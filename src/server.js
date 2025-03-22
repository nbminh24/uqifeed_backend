const express = require("express");
const cors = require("cors");
require("dotenv").config();

const userRoutes = require("./routes/userRoutes");

const app = express();
app.use(cors());
app.use(express.json());

// API kiểm tra server
app.get("/", (req, res) => {
    res.send("Uqifeed Backend is running!");
});

// Routes
app.use("/users", userRoutes);

// Chạy server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`🚀 Server running on port ${PORT}`);
});
