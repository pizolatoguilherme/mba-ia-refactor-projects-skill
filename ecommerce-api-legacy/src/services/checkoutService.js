const db = require('../database/connection');
const courseModel = require('../models/courseModel');
const userModel = require('../models/userModel');
const enrollmentModel = require('../models/enrollmentModel');
const paymentModel = require('../models/paymentModel');
const auditLogModel = require('../models/auditLogModel');
const { hashPassword } = require('../utils/password');
const { PAYMENT_STATUS, APPROVED_CARD_PREFIX } = require('../config/constants');
const { BadRequestError, NotFoundError } = require('../errors');
const logger = require('../config/logger');

async function checkout({ username, email, password, courseId, card }) {
    const parsedCourseId = Number(courseId);
    if (!username || !email || !card || !parsedCourseId) {
        throw new BadRequestError('Bad Request');
    }

    const course = await courseModel.findActiveById(parsedCourseId);
    if (!course) {
        throw new NotFoundError('Curso não encontrado');
    }

    const existingUser = await userModel.findByEmail(email);
    let userId;
    if (existingUser) {
        userId = existingUser.id;
    } else {
        if (!password) {
            throw new BadRequestError('Senha é obrigatória');
        }
        const passwordHash = hashPassword(password);
        const created = await userModel.create(username, email, passwordHash);
        userId = created.lastID;
    }

    const status = card.startsWith(APPROVED_CARD_PREFIX) ? PAYMENT_STATUS.PAID : PAYMENT_STATUS.DENIED;
    logger.info(`Checkout curso=${parsedCourseId} usuario=${userId} card=****${card.slice(-4)}`);

    if (status === PAYMENT_STATUS.DENIED) {
        throw new BadRequestError('Pagamento recusado');
    }

    return db.transaction(async () => {
        const { lastID: enrollmentId } = await enrollmentModel.create(userId, parsedCourseId);
        await paymentModel.create(enrollmentId, course.price, status);
        await auditLogModel.record(`Checkout curso ${parsedCourseId} por ${userId}`);
        return { enrollmentId };
    });
}

module.exports = { checkout };
