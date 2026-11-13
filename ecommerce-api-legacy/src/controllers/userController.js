const userService = require('../services/userService');

async function remove(req, res) {
    await userService.remove(req.params.id);
    res.send('Usuário deletado e matrículas/pagamentos relacionados removidos.');
}

module.exports = { remove };
