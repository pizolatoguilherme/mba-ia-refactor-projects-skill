const db = require('../database/connection');
const courseModel = require('../models/courseModel');
const userModel = require('../models/userModel');
const enrollmentModel = require('../models/enrollmentModel');
const paymentModel = require('../models/paymentModel');
const auditLogModel = require('../models/auditLogModel');
const { hashPassword } = require('../utils/password');
const { NotFoundError, ValidationError } = require('../errors');
const config = require('../config');
const logger = require('../utils/logger');

function decidePaymentStatus(card) {
    return card.startsWith(config.APPROVED_CARD_PREFIX) ? config.PAYMENT_STATUS.PAID : config.PAYMENT_STATUS.DENIED;
}

async function checkout({ name, email, password, courseId, card }) {
    const course = await courseModel.findActiveById(courseId);
    if (!course) throw new NotFoundError('Curso não encontrado');

    const existingUser = await userModel.findByEmail(email);
    if (!existingUser && !password) throw new ValidationError('Senha é obrigatória');

    logger.info(`Processando pagamento para o curso ${courseId}, cartão **** ${card.slice(-4)}`);
    const status = decidePaymentStatus(card);
    if (status === config.PAYMENT_STATUS.DENIED) throw new ValidationError('Pagamento recusado');

    return db.transaction(async () => {
        let userId = existingUser ? existingUser.id : null;
        if (!userId) {
            const { lastID } = await userModel.create(name, email, hashPassword(password));
            userId = lastID;
        }

        const { lastID: enrollmentId } = await enrollmentModel.create(userId, courseId);
        await paymentModel.create(enrollmentId, course.price, status);
        await auditLogModel.record(`Checkout curso ${courseId} por ${userId}`);

        return { enrollmentId };
    });
}

module.exports = { checkout };
