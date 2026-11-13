const express = require('express');
const asyncHandler = require('../middlewares/asyncHandler');
const checkoutController = require('../controllers/checkoutController');

const router = express.Router();

router.post('/checkout', asyncHandler(checkoutController.create));

module.exports = router;
