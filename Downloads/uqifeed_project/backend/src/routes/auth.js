const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/auth');
const userController = require('../controllers/user');
const { body } = require('express-validator');
const validationMiddleware = require('../middleware/validation');

// Validation rules
const registerValidation = [
    body('name').notEmpty().withMessage('Name is required'),
    body('email').isEmail().withMessage('Please provide a valid email'),
    body('password')
        .isLength({ min: 6 })
        .withMessage('Password must be at least 6 characters long')
];

const loginValidation = [
    body('email').isEmail().withMessage('Please provide a valid email'),
    body('password').notEmpty().withMessage('Password is required')
];

// Routes
router.post(
    '/register',
    registerValidation,
    validationMiddleware,
    userController.register
);

router.post(
    '/login',
    loginValidation,
    validationMiddleware,
    userController.login
);

router.post('/google', userController.googleLogin);

router.get('/logout', userController.logout);

router.get('/me', authenticate, userController.getProfile);

router.put('/profile', authenticate, userController.updateProfile);

module.exports = router;
