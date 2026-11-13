const reportModel = require('../models/reportModel');
const { PAYMENT_STATUS } = require('../config/constants');

async function financialReport() {
    const rows = await reportModel.courseEnrollmentRows();

    const report = [];
    const courseIndexById = new Map();

    for (const row of rows) {
        let index = courseIndexById.get(row.course_id);
        if (index === undefined) {
            index = report.length;
            courseIndexById.set(row.course_id, index);
            report.push({ course: row.course_title, revenue: 0, students: [] });
        }

        if (row.enrollment_id === null) continue;

        if (row.payment_status === PAYMENT_STATUS.PAID) {
            report[index].revenue += row.paid_amount;
        }
        report[index].students.push({
            student: row.student_name || 'Unknown',
            paid: row.paid_amount || 0,
        });
    }

    return report;
}

module.exports = { financialReport };
