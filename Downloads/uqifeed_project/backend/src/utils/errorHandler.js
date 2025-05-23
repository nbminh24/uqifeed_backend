/**
 * Error response utility
 * Provides consistent error responses across the API
 */

/**
 * Create a custom error object
 * @param {String} message - Error message
 * @param {Number} statusCode - HTTP status code
 * @returns {Error} Custom error object
 */
exports.createError = (message, statusCode = 500) => {
    const error = new Error(message);
    error.statusCode = statusCode;
    return error;
};

/**
 * Handle 404 not found errors
 * @param {String} resource - Name of the resource not found
 * @returns {Error} Not found error
 */
exports.notFoundError = (resource = 'Resource') => {
    return this.createError(`${resource} not found`, 404);
};

/**
 * Handle unauthorized errors
 * @param {String} message - Custom message (optional)
 * @returns {Error} Unauthorized error
 */
exports.unauthorizedError = (message = 'Not authorized to access this resource') => {
    return this.createError(message, 401);
};

/**
 * Handle forbidden errors
 * @param {String} message - Custom message (optional)
 * @returns {Error} Forbidden error
 */
exports.forbiddenError = (message = 'Forbidden access to this resource') => {
    return this.createError(message, 403);
};

/**
 * Handle validation errors
 * @param {Array} errors - Validation errors
 * @returns {Error} Validation error
 */
exports.validationError = (errors) => {
    const error = this.createError('Validation failed', 400);
    error.errors = errors;
    return error;
};

/**
 * Send error response
 * @param {Error} err - Error object
 * @param {Object} res - Express response object
 */
exports.sendErrorResponse = (err, res) => {
    const statusCode = err.statusCode || 500;

    res.status(statusCode).json({
        success: false,
        message: err.message || 'Something went wrong',
        errors: err.errors || null,
        stack: process.env.NODE_ENV === 'production' ? null : err.stack
    });
};
