const router = require('express').Router();
const asyncHandler = require('../middlewares/asyncHandler');
const adminAuth = require('../middlewares/adminAuth');
const reportController = require('../controllers/reportController');

router.get('/admin/financial-report', adminAuth, asyncHandler(reportController.financial));

module.exports = router;
