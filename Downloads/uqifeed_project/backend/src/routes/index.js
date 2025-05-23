const express = require('express');
const router = express.Router();

// Controllers
const indexController = require('../controllers/index');

// Import other routes
const authRoutes = require('./auth');

// Base routes
router.get('/', indexController.home);
router.get('/api/health', indexController.healthCheck);

// Use route modules
router.use('/api/auth', authRoutes);

module.exports = router;
