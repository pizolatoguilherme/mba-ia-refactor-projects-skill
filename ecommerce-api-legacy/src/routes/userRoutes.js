const express = require('express');
const asyncHandler = require('../middlewares/asyncHandler');
const userController = require('../controllers/userController');

const router = express.Router();

router.delete('/users/:id', asyncHandler(userController.remove));

module.exports = router;
