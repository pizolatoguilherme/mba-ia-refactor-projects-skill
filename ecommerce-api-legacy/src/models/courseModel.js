const db = require('../database/connection');

function findActiveById(id) {
    return db.get('SELECT * FROM courses WHERE id = ? AND active = 1', [id]);
}

module.exports = { findActiveById };
