const { db } = require('../config/firebase');
const bcrypt = require('bcrypt');

// Collection reference
const usersCollection = db.collection('users');

/**
 * User Model
 * Handles all database operations related to users
 */
class User {
    /**
     * Create a new user
     * @param {Object} userData - User data to create
     * @returns {Object} Created user object
     */    static async create(userData) {
        try {
            // If password is provided, hash it
            if (userData.password) {
                const salt = await bcrypt.genSalt(10);
                userData.password = await bcrypt.hash(userData.password, salt);
            }

            // Add timestamp
            userData.createdAt = new Date().toISOString();
            userData.updatedAt = new Date().toISOString();

            // Check if username is unique if provided
            if (userData.username) {
                const usernameExists = await this.findByUsername(userData.username);
                if (usernameExists) {
                    throw new Error('Username already exists');
                }
            }

            // Create user in Firestore
            const userRef = await usersCollection.add(userData);

            // Get the user data with ID
            const user = await userRef.get();
            return { id: user.id, ...user.data() };
        } catch (error) {
            console.error('Error creating user:', error);
            throw error;
        }
    }

    /**
     * Find a user by ID
     * @param {String} id - User ID
     * @returns {Object|null} User object or null if not found
     */
    static async findById(id) {
        try {
            const userDoc = await usersCollection.doc(id).get();

            if (!userDoc.exists) {
                return null;
            }

            return { id: userDoc.id, ...userDoc.data() };
        } catch (error) {
            console.error('Error finding user by ID:', error);
            throw error;
        }
    }    /**
     * Find a user by email
     * @param {String} email - User email
     * @returns {Object|null} User object or null if not found
     */
    static async findByEmail(email) {
        try {
            const snapshot = await usersCollection.where('email', '==', email).limit(1).get();

            if (snapshot.empty) {
                return null;
            }

            let user = null;
            snapshot.forEach(doc => {
                user = { id: doc.id, ...doc.data() };
            });

            return user;
        } catch (error) {
            console.error('Error finding user by email:', error);
            throw error;
        }
    }

    /**
     * Find a user by username
     * @param {String} username - Username
     * @returns {Object|null} User object or null if not found
     */
    static async findByUsername(username) {
        try {
            const snapshot = await usersCollection.where('username', '==', username).limit(1).get();

            if (snapshot.empty) {
                return null;
            }

            let user = null;
            snapshot.forEach(doc => {
                user = { id: doc.id, ...doc.data() };
            });

            return user;
        } catch (error) {
            console.error('Error finding user by username:', error);
            throw error;
        }
    }

    /**
     * Update a user
     * @param {String} id - User ID
     * @param {Object} userData - User data to update
     * @returns {Object} Updated user object
     */
    static async update(id, userData) {
        try {
            // If password is provided, hash it
            if (userData.password) {
                const salt = await bcrypt.genSalt(10);
                userData.password = await bcrypt.hash(userData.password, salt);
            }

            // Add timestamp
            userData.updatedAt = new Date().toISOString();

            // Update user in Firestore
            await usersCollection.doc(id).update(userData);

            // Get the updated user
            return await this.findById(id);
        } catch (error) {
            console.error('Error updating user:', error);
            throw error;
        }
    }

    /**
     * Delete a user
     * @param {String} id - User ID
     * @returns {Boolean} Success status
     */
    static async delete(id) {
        try {
            await usersCollection.doc(id).delete();
            return true;
        } catch (error) {
            console.error('Error deleting user:', error);
            throw error;
        }
    }

    /**
     * Find all users with pagination
     * @param {Number} limit - Number of users to retrieve
     * @param {Number} page - Page number
     * @returns {Array} Array of user objects
     */
    static async findAll(limit = 10, page = 1) {
        try {
            const offset = (page - 1) * limit;
            const snapshot = await usersCollection.orderBy('createdAt', 'desc').limit(limit).offset(offset).get();

            const users = [];
            snapshot.forEach(doc => {
                users.push({ id: doc.id, ...doc.data() });
            });

            return users;
        } catch (error) {
            console.error('Error finding all users:', error);
            throw error;
        }
    }

    /**
     * Compare password with hashed password
     * @param {String} enteredPassword - Password to compare
     * @param {String} hashedPassword - Hashed password from database
     * @returns {Boolean} Match status
     */
    static async comparePassword(enteredPassword, hashedPassword) {
        return await bcrypt.compare(enteredPassword, hashedPassword);
    }
}

module.exports = User;
