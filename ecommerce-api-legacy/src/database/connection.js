const sqlite3 = require('sqlite3').verbose();
const config = require('../config');
const { hashPassword } = require('../utils/password');

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

let chain = Promise.resolve();

function transaction(fn) {
    const result = chain.then(async () => {
        await run('BEGIN');
        try {
            const out = await fn();
            await run('COMMIT');
            return out;
        } catch (err) {
            await run('ROLLBACK');
            throw err;
        }
    });
    chain = result.catch(() => {});
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
    const existing = await get('SELECT id FROM users LIMIT 1');
    if (existing) return;

    const passwordHash = hashPassword('123');
    const { lastID: userId } = await run(
        'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
        ['Leonan', 'leonan@fullcycle.com.br', passwordHash],
    );
    const { lastID: courseId1 } = await run(
        'INSERT INTO courses (title, price, active) VALUES (?, ?, 1)',
        ['Clean Architecture', 997.00],
    );
    await run('INSERT INTO courses (title, price, active) VALUES (?, ?, 1)', ['Docker', 497.00]);
    const { lastID: enrollmentId } = await run(
        'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
        [userId, courseId1],
    );
    await run(
        'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
        [enrollmentId, 997.00, 'PAID'],
    );
}

module.exports = { run, get, all, transaction, initSchema, seed };
