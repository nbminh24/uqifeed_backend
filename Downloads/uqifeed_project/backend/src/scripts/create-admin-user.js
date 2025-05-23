// Script to create admin user in Firebase
const User = require('../models/user');
const { auth } = require('../config/firebase');
const dotenv = require('dotenv');

// Load environment variables
dotenv.config();

async function createAdminUser() {
    try {
        const adminData = {
            email: 'admin@gmail.com',
            password: 'admin',
            username: 'admin'
        };

        // Check if user already exists
        const userExists = await User.findByEmail(adminData.email);
        if (userExists) {
            console.log('Admin user already exists');
            return;
        }

        // Create user in Firestore
        const user = await User.create(adminData);

        console.log('Admin user created successfully:', user);
        process.exit(0);
    } catch (error) {
        console.error('Error creating admin user:', error);
        process.exit(1);
    }
}

// Run the function
createAdminUser();
