const router = require('express').Router();

router.use(require('./checkoutRoutes'));
router.use(require('./adminRoutes'));
router.use(require('./userRoutes'));

module.exports = router;
