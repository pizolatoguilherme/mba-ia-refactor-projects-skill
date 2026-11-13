const express = require('express');
const config = require('./config');
const db = require('./database/connection');
const routes = require('./routes');
const errorHandler = require('./middlewares/errorHandler');
const logger = require('./config/logger');

function createApp() {
    const app = express();
    app.use(express.json());
    app.use('/api', routes);
    app.use(errorHandler);
    return app;
}

async function start() {
    await db.initSchema();
    await db.seed();
    const app = createApp();
    app.listen(config.port, () => {
        logger.info(`Frankenstein LMS rodando na porta ${config.port}...`);
    });
}

if (require.main === module) {
    start();
}

module.exports = { createApp };
