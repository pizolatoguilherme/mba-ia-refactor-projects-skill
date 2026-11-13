const reportService = require('../services/reportService');

async function financial(req, res) {
    const report = await reportService.financialReport();
    res.json(report);
}

module.exports = { financial };
