const crypto = require('crypto');

const PAYMENT_STATUS = Object.freeze({
    PAID: 'PAID',
    DENIED: 'DENIED',
});

const APPROVED_CARD_PREFIX = '4';

if (!process.env.PAYMENT_GATEWAY_KEY) {
    console.warn('[config] PAYMENT_GATEWAY_KEY não definida; usando valor efêmero.');
}

module.exports = Object.freeze({
    port: Number(process.env.PORT) || 3000,
    dbPath: process.env.DB_PATH || ':memory:',
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || crypto.randomBytes(16).toString('hex'),
    smtpUser: process.env.SMTP_USER || '',
    adminToken: process.env.ADMIN_TOKEN || null,
    PAYMENT_STATUS,
    APPROVED_CARD_PREFIX,
});
