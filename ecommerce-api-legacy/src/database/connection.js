const sqlite3 = require('sqlite3').verbose();
const config = require('../config');

const db = new sqlite3.Database(config.dbPath);

function run(sql, params = []) {
    return new Promise((resolve, reject) => {
        db.run(sql, params, function (err) {
            if (err) return reject(err);
            resolve({ lastID: this.lastID, changes: this.changes });
        });
    });
}

function get(sql, params = []) {
    return new Promise((resolve, reject) => {
        db.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
    });
}

function all(sql, params = []) {
    return new Promise((resolve, reject) => {
        db.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
    });
}

// sqlite3 serializa todas as queries de uma única conexão, então basta garantir
// que não haja mais de uma transação BEGIN/COMMIT em andamento ao mesmo tempo.
let transactionQueue = Promise.resolve();

function transaction(fn) {
    const run_ = async () => {
        await run('BEGIN');
        try {
            const result = await fn();
            await run('COMMIT');
            return result;
        } catch (err) {
            await run('ROLLBACK');
            throw err;
        }
    };
    const result = transactionQueue.then(run_);
    transactionQueue = result.catch(() => {});
    return result;
}

async function initSchema() {
    await run('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, pass TEXT)');
    await run('CREATE TABLE IF NOT EXISTS courses (id INTEGER PRIMARY KEY, title TEXT, price REAL, active INTEGER)');
    await run('CREATE TABLE IF NOT EXISTS enrollments (id INTEGER PRIMARY KEY, user_id INTEGER, course_id INTEGER)');
    await run('CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY, enrollment_id INTEGER, amount REAL, status TEXT)');
    await run('CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY, action TEXT, created_at DATETIME)');
}

async function seed() {
    const { hashPassword } = require('../utils/password');
    await run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', ['Leonan', 'leonan@fullcycle.com.br', hashPassword('123')]);
    await run("INSERT INTO courses (title, price, active) VALUES ('Clean Architecture', 997.00, 1), ('Docker', 497.00, 1)");
    await run('INSERT INTO enrollments (user_id, course_id) VALUES (1, 1)');
    await run('INSERT INTO payments (enrollment_id, amount, status) VALUES (1, 997.00, ?)', [config.PAYMENT_STATUS.PAID]);
}

async function init() {
    await initSchema();
    await seed();
}

module.exports = { run, get, all, transaction, init };
