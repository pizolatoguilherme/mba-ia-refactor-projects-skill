const db = require('../database/connection');
const config = require('../config');

async function financialReport() {
    const rows = await db.all(`
        SELECT c.id AS course_id, c.title AS course_title,
               e.id AS enrollment_id,
               u.name AS student_name,
               p.amount AS payment_amount, p.status AS payment_status
        FROM courses c
        LEFT JOIN enrollments e ON e.course_id = c.id
        LEFT JOIN users u ON u.id = e.user_id
        LEFT JOIN payments p ON p.enrollment_id = e.id
        ORDER BY c.id, e.id
    `);

    const coursesById = new Map();
    for (const row of rows) {
        if (!coursesById.has(row.course_id)) {
            coursesById.set(row.course_id, { course: row.course_title, revenue: 0, students: [] });
        }
        const courseData = coursesById.get(row.course_id);

        if (row.enrollment_id === null) continue; // curso sem matrículas

        if (row.payment_status === config.PAYMENT_STATUS.PAID) {
            courseData.revenue += row.payment_amount;
        }

        courseData.students.push({
            student: row.student_name || 'Unknown',
            paid: row.payment_amount || 0,
        });
    }

    return Array.from(coursesById.values());
}

module.exports = { financialReport };
