class AppError extends Error {
    constructor(message, status = 400) {
        super(message);
        this.status = status;
    }
}

class ValidationError extends AppError {
    constructor(message) {
        super(message, 400);
    }
}

class NotFoundError extends AppError {
    constructor(message) {
        super(message, 404);
    }
}

class ForbiddenError extends AppError {
    constructor(message) {
        super(message, 403);
    }
}

module.exports = { AppError, ValidationError, NotFoundError, ForbiddenError };
