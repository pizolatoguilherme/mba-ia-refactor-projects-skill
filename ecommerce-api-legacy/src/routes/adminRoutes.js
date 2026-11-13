const express = require('express');
const asyncHandler = require('../middlewares/asyncHandler');
const adminAuth = require('../middlewares/adminAuth');
const reportController = require('../controllers/reportController');

const router = express.Router();

router.get('/admin/financial-report', adminAuth, asyncHandler(reportController.financial));

module.exports = router;
