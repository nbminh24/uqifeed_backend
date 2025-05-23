/**
 * Index Controller
 * Handles basic routes and health checks
 */

// Home route
exports.home = (req, res) => {
    res.status(200).json({
        success: true,
        message: 'Welcome to UQI Feed API',
        version: '1.0.0'
    });
};

// Health check route
exports.healthCheck = (req, res) => {
    res.status(200).json({
        success: true,
        message: 'API is up and running',
        timestamp: new Date().toISOString()
    });
};
