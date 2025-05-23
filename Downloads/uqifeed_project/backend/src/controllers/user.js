const User = require('../models/user');
const { admin, auth } = require('../config/firebase');
const jwt = require('jsonwebtoken');
const { OAuth2Client } = require('google-auth-library');

// Google OAuth client
const googleClient = new OAuth2Client(process.env.GOOGLE_CLIENT_ID);

/**
 * User Controller
 * Handles all user-related operations
 */
const UserController = {
    /**
     * Register a new user
     * @route POST /api/auth/register
     */
    register: async (req, res) => {
        try {
            const { email, password, name } = req.body;

            // Check if user already exists
            const userExists = await User.findByEmail(email);
            if (userExists) {
                return res.status(400).json({
                    success: false,
                    message: 'Email already in use'
                });
            }

            // Create user in Firebase Auth
            const userRecord = await auth.createUser({
                email,
                password,
                displayName: name
            });

            // Create user in Firestore
            const userData = {
                name,
                email,
                role: 'user',
                uid: userRecord.uid,
                photoURL: userRecord.photoURL || '',
                emailVerified: userRecord.emailVerified
            };

            const user = await User.create(userData);

            // Generate JWT token
            const token = jwt.sign(
                { id: userRecord.uid, role: 'user' },
                process.env.JWT_SECRET,
                { expiresIn: process.env.JWT_EXPIRES_IN }
            );

            res.status(201).json({
                success: true,
                message: 'User registered successfully',
                token,
                user: {
                    id: user.id,
                    name: user.name,
                    email: user.email,
                    role: user.role,
                    photoURL: user.photoURL
                }
            });
        } catch (error) {
            console.error('Registration error:', error);
            res.status(500).json({
                success: false,
                message: 'Error registering user',
                error: process.env.NODE_ENV === 'production' ? null : error.message
            });
        }
    },

    /**
     * Login a user
     * @route POST /api/auth/login
     */
    login: async (req, res) => {
        try {
            const { email, password } = req.body;

            // Sign in with Firebase Auth
            const userCredential = await auth.signInWithEmailAndPassword(email, password);
            const firebaseUser = userCredential.user;

            // Get user from Firestore
            const user = await User.findByEmail(email);
            if (!user) {
                return res.status(404).json({
                    success: false,
                    message: 'User not found'
                });
            }

            // Generate JWT token
            const token = jwt.sign(
                { id: user.uid, role: user.role },
                process.env.JWT_SECRET,
                { expiresIn: process.env.JWT_EXPIRES_IN }
            );

            // Set cookie for token
            res.cookie('token', token, {
                expires: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days
                httpOnly: true,
                secure: process.env.NODE_ENV === 'production',
                sameSite: 'strict'
            });

            res.status(200).json({
                success: true,
                message: 'Login successful',
                token,
                user: {
                    id: user.id,
                    name: user.name,
                    email: user.email,
                    role: user.role,
                    photoURL: user.photoURL
                }
            });
        } catch (error) {
            console.error('Login error:', error);
            res.status(401).json({
                success: false,
                message: 'Invalid credentials',
                error: process.env.NODE_ENV === 'production' ? null : error.message
            });
        }
    },

    /**
     * Logout a user
     * @route GET /api/auth/logout
     */
    logout: (req, res) => {
        res.cookie('token', 'none', {
            expires: new Date(Date.now() + 10 * 1000), // 10 seconds
            httpOnly: true
        });

        res.status(200).json({
            success: true,
            message: 'Logged out successfully'
        });
    },

    /**
     * Get current user profile
     * @route GET /api/auth/me
     */
    getProfile: async (req, res) => {
        try {
            const user = await User.findById(req.user.id);

            if (!user) {
                return res.status(404).json({
                    success: false,
                    message: 'User not found'
                });
            }

            res.status(200).json({
                success: true,
                user: {
                    id: user.id,
                    name: user.name,
                    email: user.email,
                    role: user.role,
                    photoURL: user.photoURL
                }
            });
        } catch (error) {
            console.error('Get profile error:', error);
            res.status(500).json({
                success: false,
                message: 'Error retrieving user profile',
                error: process.env.NODE_ENV === 'production' ? null : error.message
            });
        }
    },

    /**
     * Update user profile
     * @route PUT /api/auth/profile
     */
    updateProfile: async (req, res) => {
        try {
            const { name, photoURL } = req.body;
            const updates = {};

            if (name) updates.name = name;
            if (photoURL) updates.photoURL = photoURL;

            // Update user in Firestore
            const updatedUser = await User.update(req.user.id, updates);

            // Update user in Firebase Auth
            await auth.updateUser(req.user.uid, {
                displayName: name,
                photoURL
            });

            res.status(200).json({
                success: true,
                message: 'Profile updated successfully',
                user: {
                    id: updatedUser.id,
                    name: updatedUser.name,
                    email: updatedUser.email,
                    role: updatedUser.role,
                    photoURL: updatedUser.photoURL
                }
            });
        } catch (error) {
            console.error('Update profile error:', error);
            res.status(500).json({
                success: false,
                message: 'Error updating profile',
                error: process.env.NODE_ENV === 'production' ? null : error.message
            });
        }
    },

    /**
     * Google OAuth login
     * @route POST /api/auth/google
     */
    googleLogin: async (req, res) => {
        try {
            const { idToken } = req.body;

            // Verify Google token
            const ticket = await googleClient.verifyIdToken({
                idToken,
                audience: process.env.GOOGLE_CLIENT_ID
            });

            const payload = ticket.getPayload();
            const { email, name, picture, sub } = payload;

            // Check if user exists
            let user = await User.findByEmail(email);

            if (!user) {
                // Create user in Firebase Auth
                try {
                    const userRecord = await auth.createUser({
                        email,
                        displayName: name,
                        photoURL: picture,
                        uid: sub
                    });

                    // Create user in Firestore
                    const userData = {
                        name,
                        email,
                        role: 'user',
                        uid: userRecord.uid,
                        photoURL: picture,
                        provider: 'google',
                        emailVerified: true
                    };

                    user = await User.create(userData);
                } catch (error) {
                    // User might exist in Auth but not in Firestore
                    if (error.code === 'auth/uid-already-exists' || error.code === 'auth/email-already-exists') {
                        const userRecord = await auth.getUserByEmail(email);

                        const userData = {
                            name,
                            email,
                            role: 'user',
                            uid: userRecord.uid,
                            photoURL: picture,
                            provider: 'google',
                            emailVerified: true
                        };

                        user = await User.create(userData);
                    } else {
                        throw error;
                    }
                }
            }

            // Generate JWT token
            const token = jwt.sign(
                { id: user.uid, role: user.role },
                process.env.JWT_SECRET,
                { expiresIn: process.env.JWT_EXPIRES_IN }
            );

            // Set cookie for token
            res.cookie('token', token, {
                expires: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days
                httpOnly: true,
                secure: process.env.NODE_ENV === 'production',
                sameSite: 'strict'
            });

            res.status(200).json({
                success: true,
                message: 'Google login successful',
                token,
                user: {
                    id: user.id,
                    name: user.name,
                    email: user.email,
                    role: user.role,
                    photoURL: user.photoURL
                }
            });
        } catch (error) {
            console.error('Google login error:', error);
            res.status(500).json({
                success: false,
                message: 'Error with Google login',
                error: process.env.NODE_ENV === 'production' ? null : error.message
            });
        }
    }
};

module.exports = UserController;
