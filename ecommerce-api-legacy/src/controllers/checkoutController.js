const checkoutService = require('../services/checkoutService');

async function create(req, res) {
    const { usr: username, eml: email, pwd: password, c_id: courseId, card } = req.body || {};
    const result = await checkoutService.checkout({ username, email, password, courseId, card });
    res.status(200).json({ msg: 'Sucesso', enrollment_id: result.enrollmentId });
}

module.exports = { create };
