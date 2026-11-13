const crypto = require('crypto');
const config = require('../config');

module.exports = (req, res, next) => {
    const sent = Buffer.from(req.get('X-Admin-Token') || '');
    const expected = Buffer.from(config.adminToken || '');
    if (!config.adminToken || sent.length !== expected.length || !crypto.timingSafeEqual(sent, expected)) {
        return res.status(403).send('Forbidden');
    }
    next();
};
