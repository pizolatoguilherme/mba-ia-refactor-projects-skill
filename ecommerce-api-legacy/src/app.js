const express = require('express');
const config = require('./config');
const db = require('./database/connection');
const routes = require('./routes');
const errorHandler = require('./middlewares/errorHandler');
const logger = require('./utils/logger');

function createApp() {
    const app = express();
    app.use(express.json());
    app.use('/api', routes);
    app.use(errorHandler);
    return app;
}

if (require.main === module) {
    db.init().then(() => {
        createApp().listen(config.port, () => {
            logger.info(`Frankenstein LMS rodando na porta ${config.port}...`);
        });
    });
}

module.exports = { createApp };
