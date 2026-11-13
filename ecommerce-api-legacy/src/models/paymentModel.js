const db = require('../database/connection');

function create(enrollmentId, amount, status) {
    return db.run('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)', [enrollmentId, amount, status]);
}

function deleteByEnrollmentIds(ids) {
    if (!ids.length) return Promise.resolve({ changes: 0 });
    const placeholders = ids.map(() => '?').join(',');
    return db.run(`DELETE FROM payments WHERE enrollment_id IN (${placeholders})`, ids);
}

module.exports = { create, deleteByEnrollmentIds };
