const { AppError } = require('../errors');
const logger = require('../config/logger');

module.exports = (err, req, res, next) => {
    if (err instanceof AppError) {
        return res.status(err.status).send(err.message);
    }
    logger.error(err);
    res.status(500).send('Erro interno do servidor');
};
