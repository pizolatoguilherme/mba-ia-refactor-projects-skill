================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript (Node.js v20.20.2) + Express 4.x (^4.18.2, instalado 4.22.1)
Files:   3 analyzed | ~180 lines of code
Architecture: Monolítica — AppManager.js concentra schema, seed, rotas, regras de pagamento/matrícula e relatório
Date:    2026-11-13

## Summary
CRITICAL: 4 | HIGH: 5 | MEDIUM: 4 | LOW: 4

| ID | Severity | Anti-pattern | Location |
|----|----------|--------------|----------|
| F01 | CRITICAL | Credenciais e segredos hardcoded | utils.js:1-7 |
| F02 | CRITICAL | Hash de senha fraco / senha padrão previsível | utils.js:17-23 (+1) |
| F03 | CRITICAL | Exposição de dados sensíveis em logs | AppManager.js:45 |
| F04 | CRITICAL | God Module (AppManager) | AppManager.js:1-141 |
| F05 | HIGH | Regra de negócio dentro da rota (fat controller) | AppManager.js:28-78 |
| F06 | HIGH | Estado global mutável | utils.js:9-10 (+2) |
| F07 | HIGH | Acoplamento forte / efeitos colaterais na importação | AppManager.js:4-9 (+2) |
| F08 | HIGH | Endpoint administrativo sem autenticação | AppManager.js:80-129 |
| F09 | HIGH | Callback hell / escrita multi-etapa sem transação | AppManager.js:26-78 (+45) |
| F10 | MEDIUM | Consultas N+1 no relatório financeiro | AppManager.js:83-127 |
| F11 | MEDIUM | Validação de entrada ausente/inconsistente | AppManager.js:35 (+1) |
| F12 | MEDIUM | Exceções engolidas / sucesso falso reportado | AppManager.js:57 (+3) |
| F13 | MEDIUM | Integridade referencial ausente no delete | AppManager.js:131-137 |
| F14 | LOW | Números/strings mágicos | AppManager.js:46 (+3) |
| F15 | LOW | Nomenclatura pobre | AppManager.js:29-33 (+2) |
| F16 | LOW | Imports/estado morto não utilizados | AppManager.js:2 (+2) |
| F17 | LOW | console.log como logging | AppManager.js:45 (+2) |

## Findings

### F01 [CRITICAL] Credenciais e segredos hardcoded
File: utils.js:1-7
Catalog: AP-01 | Fix: PB-01
Evidence:
```js
const config = {
    dbUser: "admin_master",
    dbPass: "senha_super_secreta_prod_123",
    paymentGatewayKey: "pk_live_1234567890abcdef",
    smtpUser: "no-reply@fullcycle.com.br",
    port: 3000
};
```
Description: Usuário/senha de banco, chave de gateway de pagamento (prefixo `pk_live_`, indicando ambiente de produção) e usuário SMTP estão escritos como literais no código-fonte.
Impact: Qualquer pessoa com acesso ao repositório (ou a uma imagem buildada) obtém credenciais de produção; rotacionar a chave exige alterar e reimplantar código.
Recommendation: Mover todos os valores para variáveis de ambiente (`process.env.*`) lidas em `config/index.js`, com defaults seguros apenas para valores não sensíveis (ex.: porta); gerar aviso no boot se um segredo obrigatório estiver ausente.

### F02 [CRITICAL] Hash de senha fraco / senha padrão previsível
File: utils.js:17-23, AppManager.js:68
Catalog: AP-04 | Fix: PB-03
Evidence:
```js
function badCrypto(pwd) {
    let hash = "";
    for(let i = 0; i < 10000; i++) {
        hash += Buffer.from(pwd).toString('base64').substring(0, 2);
    }
    return hash.substring(0, 10);
}
```
```js
let hash = badCrypto(p || "123456");
```
Description: Senhas não são hasheadas com um algoritmo criptográfico de senha — são codificadas em base64 repetidamente e truncadas para 10 caracteres, o que é trivialmente reversível/colidível. Além disso, quando o cliente não envia senha, o sistema usa o literal `"123456"` como senha padrão.
Impact: Um leak do banco expõe efetivamente as senhas em texto claro (base64 não é criptografia); contas criadas sem senha explícita ficam protegidas por uma senha universalmente conhecida.
Recommendation: Usar `crypto.scrypt`/`crypto.pbkdf2` (módulo nativo `crypto` do Node, sem nova dependência) com salt por usuário dentro do model de usuário; exigir senha no payload ou rejeitar com 400 em vez de aplicar um default.

### F03 [CRITICAL] Exposição de dados sensíveis em logs
File: AppManager.js:45
Catalog: AP-05 | Fix: PB-03, PB-15
Evidence:
```js
console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
```
Description: O número completo do cartão de crédito recebido no checkout e a chave secreta do gateway de pagamento são impressos juntos no log da aplicação.
Impact: Dados de cartão (PCI) e o segredo do gateway ficam expostos em qualquer agregador de logs ou console do servidor, violando práticas básicas de PCI-DSS.
Recommendation: Remover o log; se for necessário auditar o processamento, logar apenas um identificador não sensível (ex.: últimos 4 dígitos) através de um logger estruturado, nunca a chave do gateway.

### F04 [CRITICAL] God Module (AppManager)
File: AppManager.js:1-141
Catalog: AP-06 | Fix: PB-05, PB-06
Evidence:
```js
class AppManager {
    constructor() { this.db = new sqlite3.Database(':memory:'); }
    initDb() { /* schema + seed */ }
    setupRoutes(app) { /* checkout + relatório + delete, com SQL e regras inline */ }
}
```
Description: Uma única classe concentra conexão/schema do banco, dados de seed, registro de rotas, regras de pagamento/matrícula, geração de relatório financeiro e exclusão de usuário — misturando acesso a dados, regra de negócio e HTTP no mesmo arquivo de 141 linhas.
Impact: Impossível testar qualquer regra isoladamente; qualquer alteração em uma funcionalidade (ex.: relatório) arrisca quebrar outra (ex.: checkout) por estarem no mesmo módulo e usarem a mesma conexão.
Recommendation: Dividir em `database/connection.js`, `models/` (user, course, enrollment, payment, auditLog), `services/checkoutService.js`, `services/reportService.js`, `controllers/` e `routes/`, conforme `mvc-guidelines.md` §2.3.

### F05 [HIGH] Regra de negócio dentro da rota (fat controller)
File: AppManager.js:28-78
Catalog: AP-07 | Fix: PB-08
Evidence:
```js
app.post('/api/checkout', (req, res) => {
    ...
    let status = cc.startsWith("4") ? "PAID" : "DENIED";
    if (status === "DENIED") return res.status(400).send("Pagamento recusado");
    ...
});
```
Description: O handler da rota de checkout lê o body, decide se o pagamento é aprovado (`cc.startsWith("4")`), cria usuário quando necessário, cria matrícula, cria pagamento e grava auditoria — tudo inline, sem nenhuma camada de serviço/controller.
Impact: A regra de aprovação de pagamento e o fluxo de matrícula não podem ser reutilizados nem testados sem simular uma requisição HTTP completa.
Recommendation: Extrair o fluxo para `services/checkoutService.js` (orquestra models) e um `controllers/checkoutController.js` fino que apenas valida entrada e chama o serviço, devolvendo a resposta.

### F06 [HIGH] Estado global mutável
File: utils.js:9-10, utils.js:12-15, utils.js:25
Catalog: AP-08 | Fix: PB-12
Evidence:
```js
let globalCache = {};
let totalRevenue = 0;
function logAndCache(key, data) {
    globalCache[key] = data;
}
module.exports = { config, logAndCache, badCrypto, globalCache, totalRevenue };
```
Description: `globalCache` e `totalRevenue` são variáveis mutáveis no escopo do módulo, exportadas junto com uma função (`logAndCache`) que muta `globalCache` por efeito colateral.
Impact: Estado compartilhado entre todas as requisições sem isolamento; em um processo com múltiplos workers o cache fica inconsistente entre eles, e qualquer módulo que importe `globalCache`/`totalRevenue` recebe uma cópia desatualizada do valor primitivo (no caso de `totalRevenue`).
Recommendation: Remover o cache global e `totalRevenue` (não é lido por nenhum consumidor); se um cache for necessário, encapsulá-lo em uma instância injetada, não em estado de módulo.

### F07 [HIGH] Acoplamento forte / efeitos colaterais na inicialização
File: AppManager.js:4-9, app.js:8-10
Catalog: AP-09 | Fix: PB-07
Evidence:
```js
constructor() {
    this.db = new sqlite3.Database(':memory:');
}
```
```js
const manager = new AppManager();
manager.initDb();
manager.setupRoutes(app);
```
Description: A classe `AppManager` cria sua própria conexão concreta com o SQLite dentro do construtor, e o schema/seed são executados de forma síncrona e acoplada à inicialização do processo, sem nenhum ponto de injeção.
Impact: Impossível substituir o banco por um dublê em testes ou reaproveitar a mesma conexão por um `database.js` compartilhado; qualquer teste de unidade acaba abrindo um banco real.
Recommendation: Mover a criação/abertura da conexão para `database/connection.js` (composition root), injetando-a nos models/serviços em vez de instanciá-la dentro da classe.

### F08 [HIGH] Endpoint administrativo sem autenticação
File: AppManager.js:80-129
Catalog: AP-11 | Fix: PB-04
Evidence:
```js
app.get('/api/admin/financial-report', (req, res) => {
    let report = [];
    this.db.all("SELECT * FROM courses", [], (err, courses) => { ... });
});
```
Description: A rota está sob o namespace `/api/admin/...` e devolve faturamento por curso e dados de alunos (nome, valor pago), mas não exige nenhuma credencial ou token para ser acessada.
Impact: Qualquer cliente não autenticado consegue ler dados financeiros e de alunos da plataforma.
Recommendation: Aplicar o guard de admin definido em `mvc-guidelines.md` §4 — middleware `adminAuth.js` exigindo header `X-Admin-Token` igual a `ADMIN_TOKEN` (env); responder 403 se `ADMIN_TOKEN` não estiver configurado. Mantém a rota, apenas passa a exigir o token.

### F09 [HIGH] Callback hell / escrita multi-etapa sem transação
File: AppManager.js:26-78, AppManager.js:83-127
Catalog: AP-12 | Fix: PB-10
Evidence:
```js
const self = this;
...
this.db.run("INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)", [userId, cid], function(err) {
    let enrId = this.lastID;
    self.db.run("INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)", [enrId, course.price, status], function(err) {
        self.db.run("INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))", [...], (err) => { ... });
    });
});
```
Description: O checkout encadeia 5+ níveis de callbacks (com o workaround `const self = this`) para criar usuário, matrícula, pagamento e log de auditoria sem nenhum `BEGIN/COMMIT/ROLLBACK`; o relatório financeiro usa a mesma técnica com contadores manuais (`coursesPending--`, `enrPending--`) para saber quando responder.
Impact: Se a escrita de pagamento ou auditoria falhar após a matrícula ter sido criada, o banco fica com dados parcialmente gravados; o fluxo é difícil de ler e de dar manutenção com segurança.
Recommendation: Introduzir um helper `transaction(fn)` em `database/connection.js` (ou promisificar o driver) e usar `async/await` no `checkoutService`, conforme PB-10.

### F10 [MEDIUM] Consultas N+1 no relatório financeiro
File: AppManager.js:83-127
Catalog: AP-13 | Fix: PB-09
Evidence:
```js
courses.forEach(c => {
    this.db.all("SELECT * FROM enrollments WHERE course_id = ?", [c.id], (err, enrollments) => {
        enrollments.forEach(enr => {
            this.db.get("SELECT name, email FROM users WHERE id = ?", [enr.user_id], (err, user) => {
                this.db.get("SELECT amount, status FROM payments WHERE enrollment_id = ?", [enr.id], (err, payment) => { ... });
            });
        });
    });
});
```
Description: Para cada curso é feita uma query de matrículas, e para cada matrícula mais duas queries (usuário e pagamento) — três níveis de consultas dentro de loops.
Impact: O número de queries cresce linearmente com cursos × matrículas; a latência do relatório degrada rapidamente com o volume de dados.
Recommendation: Substituir por um conjunto pequeno de `JOIN`s (cursos ⋈ matrículas ⋈ usuários ⋈ pagamentos) em `models/reportModel.js` e montar o agregado em memória a partir do resultado único.

### F11 [MEDIUM] Validação de entrada ausente/inconsistente
File: AppManager.js:35, AppManager.js:131-133
Catalog: AP-15 | Fix: PB-13
Evidence:
```js
if (!u || !e || !cid || !cc) return res.status(400).send("Bad Request");
```
```js
app.delete('/api/users/:id', (req, res) => {
    let id = req.params.id;
    this.db.run("DELETE FROM users WHERE id = ?", [id], (err) => { ... });
```
Description: O checkout não valida formato de e-mail, tipo/existência de `cid` como número, nem tamanho do número de cartão; o delete de usuário aceita qualquer valor de `:id` (inclusive não numérico) sem checagem.
Impact: Dados inválidos chegam até o banco ou geram respostas de sucesso para operações que não fizeram nada (delete de um id inexistente/inválido).
Recommendation: Centralizar validação básica de presença/tipo em `validators/` ou no início do controller, devolvendo 400 com mensagem consistente antes de chamar o model.

### F12 [MEDIUM] Exceções engolidas / sucesso falso reportado
File: AppManager.js:57, AppManager.js:133-136
Catalog: AP-16 | Fix: PB-11
Evidence:
```js
self.db.run("INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))", [`Checkout curso ${cid} por ${userId}`], (err) => {
    logAndCache(`last_checkout_${userId}`, course.title);
    res.status(200).json({ msg: "Sucesso", enrollment_id: enrId });
});
```
```js
this.db.run("DELETE FROM users WHERE id = ?", [id], (err) => {
    res.send("Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.");
});
```
Description: O parâmetro `err` é recebido e ignorado nos dois callbacks — o checkout responde sucesso mesmo que o log de auditoria falhe, e o delete sempre responde como se a exclusão tivesse funcionado, mesmo que `err` esteja preenchido.
Impact: Falhas reais ficam invisíveis para quem chama a API e para quem opera o sistema; não há um formato de erro consistente.
Recommendation: Propagar `err` para um middleware central de erros (`errorHandler.js`) que responde de forma uniforme; nenhum callback deve ignorar `err` silenciosamente.

### F13 [MEDIUM] Integridade referencial ausente no delete
File: AppManager.js:131-137
Catalog: AP-17 | Fix: PB-16
Evidence:
```js
app.delete('/api/users/:id', (req, res) => {
    let id = req.params.id;
    this.db.run("DELETE FROM users WHERE id = ?", [id], (err) => {
        res.send("Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.");
    });
});
```
Description: O próprio texto de resposta admite que matrículas e pagamentos do usuário ficam órfãos após o delete — não há remoção/guarda em cascata nem checagem de dependências.
Impact: Relatórios futuros (ex.: financial-report) podem referenciar `user_id` inexistente, gerando dados inconsistentes ("Unknown") ou erros.
Recommendation: No model de usuário, decidir e aplicar explicitamente uma estratégia (cascade delete das matrículas/pagamentos relacionados, ou bloquear o delete se houver matrículas ativas) dentro de uma transação.

### F14 [LOW] Números/strings mágicos
File: AppManager.js:46, AppManager.js:48, AppManager.js:68, utils.js:19
Catalog: AP-20 | Fix: PB-15
Evidence:
```js
let status = cc.startsWith("4") ? "PAID" : "DENIED";
```
Description: A regra de aprovação de cartão (`"4"`), os status `"PAID"`/`"DENIED"`, a senha padrão `"123456"` e o contador `10000` do hash estão espalhados como literais no código.
Impact: Mudar qualquer uma dessas regras exige caçar literais pelo código; fácil introduzir inconsistência (ex.: escrever `"Paid"` em outro lugar).
Recommendation: Extrair para constantes nomeadas em `config/index.js` (ex.: `PAYMENT_STATUS.PAID`, `PAYMENT_STATUS.DENIED`).

### F15 [LOW] Nomenclatura pobre
File: AppManager.js:29-33, utils.js:12, utils.js:17
Catalog: AP-21 | Fix: PB-15
Evidence:
```js
let u = req.body.usr;
let e = req.body.eml;
let p = req.body.pwd;
let cid = req.body.c_id;
let cc = req.body.card;
```
Description: Identificadores de domínio reduzidos a uma ou duas letras (`u, e, p, cid, cc`); `badCrypto` e `logAndCache` nomeiam funções que fazem algo diferente do que o nome sugere (hashing fraco, e cache + log juntos).
Impact: Dificulta a leitura e a revisão do fluxo de checkout; nomes que "mentem" confundem quem dá manutenção.
Recommendation: Renomear para nomes de domínio completos internamente (os campos do payload — `usr`, `eml` etc. — são mantidos por contrato externo); dividir `logAndCache` em responsabilidades separadas se o cache for mantido.

### F16 [LOW] Imports/estado morto não utilizados
File: AppManager.js:2, utils.js:9-10, utils.js:25
Catalog: AP-22 | Fix: PB-15
Evidence:
```js
const { config, logAndCache, badCrypto, totalRevenue } = require('./utils');
```
Description: `totalRevenue` é importado em `AppManager.js` mas nunca lido; `globalCache`/`totalRevenue` são exportados por `utils.js` mas nenhum módulo os consome de volta.
Impact: Código morto que sugere uma funcionalidade (acumulação de receita) que não existe de fato — confunde quem lê o módulo.
Recommendation: Remover `totalRevenue` e, se `globalCache` não passar a ser usado na nova arquitetura, removê-lo também (ver F06).

### F17 [LOW] console.log como logging
File: AppManager.js:45, app.js:13, utils.js:13
Catalog: AP-23 | Fix: PB-15
Evidence:
```js
console.log(`[LOG] Salvando no cache: ${key}`);
```
Description: Toda a aplicação usa `console.log` diretamente para eventos de negócio e de boot, sem níveis (`info`/`warn`/`error`) nem estrutura.
Impact: Não é possível filtrar/rotear logs por severidade em produção; o caso de AppManager.js:45 agrava o F03 ao logar dados sensíveis.
Recommendation: Usar um logger mínimo (`console` encapsulado em `config/logger.js` com níveis) no lugar de chamadas diretas a `console.log`.

## Deprecated APIs
| File:line | Deprecated usage | Modern replacement |
|-----------|------------------|--------------------|
| AppManager.js:37,40,50,54,57,69,83,92,104,106,133 | Driver `sqlite3` usado exclusivamente via callbacks aninhados (`db.run/get/all(sql, cb)`) | Envolver o driver em uma camada promisificada (`util.promisify` ou wrapper manual) e usar `async/await` nos models/serviços |

Nenhuma outra API explicitamente deprecada (ex.: `new Buffer`, `url.parse`, `createCipher`, `req.param()`, `app.del()`) foi encontrada nas versões declaradas (Express ^4.18.2 / Node v20).

## Proposed Target Architecture
Maturidade: Monolítica → reestruturar completamente seguindo `mvc-guidelines.md` §2.3 (Node.js/Express):

```
ecommerce-api-legacy/
├── package.json                 # "start": "node src/app.js" (inalterado)
├── .env.example
└── src/
    ├── app.js                   # createApp() + listen (composition root)
    ├── config/
    │   └── index.js              # process.env + constantes (status de pagamento, etc.)
    ├── database/
    │   └── connection.js         # abre o SQLite, helpers promisificados run/get/all, transaction(fn), schema+seed
    ├── models/
    │   ├── userModel.js
    │   ├── courseModel.js
    │   ├── enrollmentModel.js
    │   ├── paymentModel.js
    │   └── auditLogModel.js
    ├── services/
    │   ├── checkoutService.js    # regra de aprovação + orquestração em transação
    │   └── reportService.js      # relatório financeiro via JOIN, sem N+1
    ├── controllers/
    │   ├── checkoutController.js
    │   ├── reportController.js
    │   └── userController.js
    ├── routes/
    │   ├── checkoutRoutes.js
    │   ├── adminRoutes.js        # financial-report protegido por adminAuth
    │   ├── userRoutes.js
    │   └── index.js              # monta todas em app
    └── middlewares/
        ├── errorHandler.js
        └── adminAuth.js          # X-Admin-Token para /api/admin/*
```

Estratégia: dividir `AppManager.js` por domínio (models + services), extrair as 3 rotas para controllers finos, mover config/segredos para `.env`, promisificar o driver para eliminar callback hell, e adicionar o guard de admin apenas na rota `/api/admin/financial-report` — preservando rotas, métodos, códigos de sucesso e payloads originais.

================================
Total: 17 findings
================================
