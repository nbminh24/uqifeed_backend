const express = require("express");
const pool = require("../config/db");

const router = express.Router();

// Lấy danh sách người dùng
router.get("/", async (req, res) => {
    try {
        const result = await pool.query("SELECT * FROM users");
        res.json(result.rows);
    } catch (err) {
        console.error(err);
        res.status(500).send("Server error");
    }
});

module.exports = router;
