const { AppError } = require('../errors');
const logger = require('../utils/logger');

// eslint-disable-next-line no-unused-vars
module.exports = (err, req, res, next) => {
    if (err instanceof AppError) {
        return res.status(err.status).send(err.message);
    }
    logger.error(err);
    res.status(500).send('Erro interno do servidor');
};
