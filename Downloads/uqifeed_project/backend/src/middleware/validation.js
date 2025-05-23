const { validationResult } = require('express-validator');

/**
 * Validation Middleware
 * Checks for validation errors from express-validator
 */
const validationMiddleware = (req, res, next) => {
    const errors = validationResult(req);

    if (!errors.isEmpty()) {
        return res.status(400).json({
            success: false,
            errors: errors.array().map(error => ({
                field: error.param,
                message: error.msg
            }))
        });
    }

    next();
};

module.exports = validationMiddleware;
