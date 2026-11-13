const router = require('express').Router();
const asyncHandler = require('../middlewares/asyncHandler');
const checkoutController = require('../controllers/checkoutController');

router.post('/checkout', asyncHandler(checkoutController.create));

module.exports = router;
