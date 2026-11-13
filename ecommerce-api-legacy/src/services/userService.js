const db = require('../database/connection');
const userModel = require('../models/userModel');
const enrollmentModel = require('../models/enrollmentModel');
const paymentModel = require('../models/paymentModel');

function remove(userId) {
    return db.transaction(async () => {
        const enrollments = await enrollmentModel.findByUser(userId);
        await paymentModel.deleteByEnrollmentIds(enrollments.map((e) => e.id));
        await enrollmentModel.deleteByUser(userId);
        await userModel.remove(userId);
    });
}

module.exports = { remove };
