const router = require('express').Router();
const asyncHandler = require('../middlewares/asyncHandler');
const userController = require('../controllers/userController');

router.delete('/users/:id', asyncHandler(userController.remove));

module.exports = router;
