const logger = require('./logger');

const paymentGatewayKey = process.env.PAYMENT_GATEWAY_KEY || '';
if (!paymentGatewayKey) {
    logger.warn('PAYMENT_GATEWAY_KEY não definido — integração real de pagamento ficará indisponível.');
}

const adminToken = process.env.ADMIN_TOKEN || null;
if (!adminToken) {
    logger.warn('ADMIN_TOKEN não definido — rotas administrativas responderão 403.');
}

module.exports = Object.freeze({
    port: Number(process.env.PORT) || 3000,
    dbPath: process.env.DB_PATH || ':memory:',
    paymentGatewayKey,
    adminToken,
});
