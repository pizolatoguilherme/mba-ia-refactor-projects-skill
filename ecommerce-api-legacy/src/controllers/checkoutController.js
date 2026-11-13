const checkoutService = require('../services/checkoutService');
const { ValidationError } = require('../errors');

async function create(req, res) {
    const { usr: name, eml: email, pwd: password, c_id: courseId, card } = req.body;

    if (!name || !email || !courseId || !card) {
        throw new ValidationError('Bad Request');
    }

    const result = await checkoutService.checkout({ name, email, password, courseId, card });
    res.status(200).json({ msg: 'Sucesso', enrollment_id: result.enrollmentId });
}

module.exports = { create };
