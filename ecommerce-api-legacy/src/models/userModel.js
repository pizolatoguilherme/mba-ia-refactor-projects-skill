const db = require('../database/connection');

function findByEmail(email) {
    return db.get('SELECT id, name, email, pass FROM users WHERE email = ?', [email]);
}

function create(name, email, passwordHash) {
    return db.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [name, email, passwordHash]);
}

function remove(id) {
    return db.run('DELETE FROM users WHERE id = ?', [id]);
}

module.exports = { findByEmail, create, remove };
