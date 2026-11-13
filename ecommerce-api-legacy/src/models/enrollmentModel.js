const db = require('../database/connection');

function create(userId, courseId) {
    return db.run('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)', [userId, courseId]);
}

function findByCourse(courseId) {
    return db.all('SELECT id, user_id, course_id FROM enrollments WHERE course_id = ?', [courseId]);
}

function findByUser(userId) {
    return db.all('SELECT id, user_id, course_id FROM enrollments WHERE user_id = ?', [userId]);
}

function deleteByUser(userId) {
    return db.run('DELETE FROM enrollments WHERE user_id = ?', [userId]);
}

module.exports = { create, findByCourse, findByUser, deleteByUser };
