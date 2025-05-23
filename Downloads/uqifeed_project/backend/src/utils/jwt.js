const jwt = require('jsonwebtoken');

/**
 * Generate a JWT token
 * @param {Object} payload - Data to include in the token
 * @param {String} expiresIn - Token expiration time
 * @returns {String} JWT token
 */
exports.generateToken = (payload, expiresIn = process.env.JWT_EXPIRES_IN) => {
    return jwt.sign(payload, process.env.JWT_SECRET, { expiresIn });
};

/**
 * Verify a JWT token
 * @param {String} token - JWT token to verify
 * @returns {Object} Decoded token payload
 */
exports.verifyToken = (token) => {
    return jwt.verify(token, process.env.JWT_SECRET);
};

/**
 * Set JWT token in cookie
 * @param {Object} res - Express response object
 * @param {String} token - JWT token
 */
exports.setTokenCookie = (res, token) => {
    const cookieOptions = {
        expires: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict'
    };

    res.cookie('token', token, cookieOptions);
};
