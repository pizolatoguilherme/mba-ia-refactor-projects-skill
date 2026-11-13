const db = require('../database/connection');
const userModel = require('../models/userModel');
const enrollmentModel = require('../models/enrollmentModel');
const paymentModel = require('../models/paymentModel');

function remove(userId) {
    return db.transaction(async () => {
        const enrollments = await enrollmentModel.findByUserId(userId);
        await paymentModel.deleteByEnrollmentIds(enrollments.map((e) => e.id));
        await enrollmentModel.deleteByUserId(userId);
        const { changes } = await userModel.remove(userId);
        return changes > 0;
    });
}

module.exports = { remove };
