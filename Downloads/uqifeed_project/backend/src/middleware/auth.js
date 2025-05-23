const jwt = require('jsonwebtoken');
const { admin } = require('../config/firebase');

/**
 * Authentication Middleware
 * Verifies the JWT token from the user and attaches the user data to the request object
 */
exports.authenticate = async (req, res, next) => {
    try {
        let token;

        // Check if token exists in authorization header or cookies
        if (req.headers.authorization && req.headers.authorization.startsWith('Bearer')) {
            // Get token from header
            token = req.headers.authorization.split(' ')[1];
        } else if (req.cookies && req.cookies.token) {
            // Get token from cookie
            token = req.cookies.token;
        }

        if (!token) {
            return res.status(401).json({
                success: false,
                message: 'Not authorized to access this route'
            });
        }

        // Verify the token
        const decoded = jwt.verify(token, process.env.JWT_SECRET);

        // Check if user exists in Firebase
        try {
            const userRecord = await admin.auth().getUser(decoded.id);
            req.user = {
                id: userRecord.uid,
                email: userRecord.email,
                role: decoded.role || 'user'
            };
            next();
        } catch (error) {
            return res.status(401).json({
                success: false,
                message: 'User no longer exists'
            });
        }
    } catch (error) {
        return res.status(401).json({
            success: false,
            message: 'Not authorized to access this route',
            error: process.env.NODE_ENV === 'production' ? null : error.message
        });
    }
};

/**
 * Role Authorization Middleware
 * Checks if the user has the required role(s) to access a route
 * @param {String|Array} roles - Required role(s) to access the route
 */
exports.authorize = (roles) => {
    return (req, res, next) => {
        if (!req.user) {
            return res.status(401).json({
                success: false,
                message: 'Not authorized to access this route'
            });
        }

        // Convert single role to array
        if (!Array.isArray(roles)) {
            roles = [roles];
        }

        // Check if user role is in the roles array
        if (!roles.includes(req.user.role)) {
            return res.status(403).json({
                success: false,
                message: `User role ${req.user.role} is not authorized to access this route`
            });
        }

        next();
    };
};
