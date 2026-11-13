================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript (Node.js) + Express 4.x (^4.18.2)
Files:   3 analyzed | ~180 lines of code
Architecture: Monolítica
Date:    2026-11-13

## Summary
CRITICAL: 4 | HIGH: 4 | MEDIUM: 4 | LOW: 5

| ID | Severity | Anti-pattern | Location |
|----|----------|--------------|----------|
| F01 | CRITICAL | Credenciais/segredos hardcoded | src/utils.js:1-7 |
| F02 | CRITICAL | God Class / God Module | src/AppManager.js:1-141 |
| F03 | CRITICAL | Hash de senha fraco + senha padrão insegura | src/utils.js:17-23 (+1) |
| F04 | CRITICAL | Exposição de dados sensíveis em log | src/AppManager.js:45 |
| F05 | HIGH | Rotas administrativas/sensíveis sem autenticação | src/AppManager.js:80 (+1) |
| F06 | HIGH | Estado global mutável | src/utils.js:9-10 (+2) |
| F07 | HIGH | Acoplamento forte / sem injeção de dependência | src/AppManager.js:4-9 (+1) |
| F08 | HIGH | Callback hell / escrita multi-etapas sem transação | src/AppManager.js:37-77 (+1) |
| F09 | MEDIUM | Consultas N+1 no relatório financeiro | src/AppManager.js:83-127 |
| F10 | MEDIUM | Erros engolidos / callbacks ignorando `err` | src/AppManager.js:92 (+3) |
| F11 | MEDIUM | Ausência de integridade referencial no delete | src/AppManager.js:131-137 |
| F12 | MEDIUM | Validação de entrada ausente/inconsistente | src/AppManager.js:29-35 |
| F13 | LOW | `console.log` como logging | src/app.js:13 (+1) |
| F14 | LOW | Números/strings mágicos | src/AppManager.js:46 (+1) |
| F15 | LOW | Nomenclatura pobre | src/AppManager.js:29-33 (+2) |
| F16 | LOW | Import/variável morta (`totalRevenue`) | src/utils.js:10 (+2) |
| F17 | LOW | Uso não idiomático de `let` em vez de `const` | src/AppManager.js:29-33 (+6) |

## Findings

### F01 [CRITICAL] Credenciais/segredos hardcoded
File: src/utils.js:1-7
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
Description: O objeto `config` guarda usuário/senha de banco, chave de gateway de pagamento (prefixo `pk_live_`, indicando ambiente de produção) e usuário SMTP como literais de string direto no código-fonte.
Impact: Qualquer pessoa com acesso ao repositório (ou a uma imagem buildada) obtém credenciais de produção; rotacionar uma credencial exige alterar e reimplantar código.
Recommendation: Mover todos os valores para variáveis de ambiente (`process.env.DB_PASS`, `process.env.PAYMENT_GATEWAY_KEY`, etc.) lidas em `src/config/index.js`, com defaults seguros apenas para valores não sensíveis (porta); documentar em `.env.example`.

### F02 [CRITICAL] God Class / God Module
File: src/AppManager.js:1-141
Catalog: AP-06 | Fix: PB-05, PB-06
Evidence:
```js
class AppManager {
    constructor() { this.db = new sqlite3.Database(':memory:'); }
    initDb() { /* schema + seed de 5 tabelas */ }
    setupRoutes(app) { /* checkout, relatório financeiro e delete de usuário */ }
}
```
Description: Uma única classe concentra conexão/schema do banco, seed de dados, registro de rotas HTTP, validação de entrada, regra de negócio de checkout, cálculo de pagamento, geração de relatório financeiro e serialização de resposta — para 5 tabelas de domínios distintos (usuários, cursos, matrículas, pagamentos, auditoria).
Impact: Impossível testar qualquer regra isoladamente; qualquer alteração em uma rota arrisca quebrar as outras duas; não há reuso de lógica fora do contexto HTTP.
Recommendation: Dividir em `models/` (acesso a dados por domínio), `controllers/` (orquestração por caso de uso), `services/` (checkout, relatório), `routes/` (mapeamento HTTP) e `database/` (conexão, schema, seed), conforme `mvc-guidelines.md` §2.3.

### F03 [CRITICAL] Hash de senha fraco + senha padrão insegura
File: src/utils.js:17-23, src/AppManager.js:68
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
// src/AppManager.js:68
let hash = badCrypto(p || "123456");
```
Description: Senhas não são hasheadas com um algoritmo criptográfico — `badCrypto` apenas repete uma codificação Base64 (reversível, sem salt) e trunca o resultado para 10 caracteres, colidindo facilmente. Além disso, quando o cliente não envia senha, o sistema atribui a senha fixa `"123456"` a um novo usuário.
Impact: Um leak do banco expõe a senha de todos os usuários (base64 é reversível); a senha padrão previsível permite login indevido em contas criadas sem senha explícita.
Recommendation: Usar `crypto.scrypt`/`crypto.pbkdf2` (módulo nativo do Node, sem nova dependência) com salt por usuário dentro de `models/userModel.js`; exigir senha no payload (400 se ausente) em vez de aplicar um default.

### F04 [CRITICAL] Exposição de dados sensíveis em log
File: src/AppManager.js:45
Catalog: AP-05 | Fix: PB-03, PB-15
Evidence:
```js
console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
```
Description: O número completo do cartão de crédito enviado pelo cliente e a chave do gateway de pagamento são impressos em texto puro no log da aplicação a cada checkout.
Impact: Qualquer pessoa com acesso aos logs (arquivo, console, agregador) obtém dados de cartão (violação PCI) e a chave de pagamento de produção.
Recommendation: Remover o log do número do cartão e da chave; se necessário auditar o evento, logar apenas um identificador não sensível (ex.: últimos 4 dígitos) através de um logger estruturado em `services/checkoutService.js`.

### F05 [HIGH] Rotas administrativas/sensíveis sem autenticação
File: src/AppManager.js:80, src/AppManager.js:131
Catalog: AP-11 | Fix: PB-04
Evidence:
```js
app.get('/api/admin/financial-report', (req, res) => { ... });
// src/AppManager.js:131
app.delete('/api/users/:id', (req, res) => { ... });
```
Description: `GET /api/admin/financial-report` está sob o namespace `/admin` e expõe nomes, e-mails e valores pagos de todos os alunos sem nenhuma verificação de autenticação/autorização. `DELETE /api/users/:id` remove qualquer usuário sem checagem de identidade.
Impact: Qualquer cliente não autenticado pode extrair dados financeiros e pessoais de todos os usuários, ou apagar contas de terceiros.
Recommendation: Conforme a política de contrato (`mvc-guidelines.md` §4), proteger apenas a rota `/api/admin/financial-report` com um middleware `adminAuth` exigindo header `X-Admin-Token` igual a `ADMIN_TOKEN` (env); se `ADMIN_TOKEN` não estiver definido, responder 403. `DELETE /api/users/:id` é um CRUD de recurso comum — mantém o nível de acesso original; recomendar autenticação de usuário no resumo final, fora do escopo desta refatoração.

### F06 [HIGH] Estado global mutável
File: src/utils.js:9-10, src/utils.js:14, src/utils.js:25
Catalog: AP-08 | Fix: PB-12
Evidence:
```js
let globalCache = {};
let totalRevenue = 0;
// ...
module.exports = { config, logAndCache, badCrypto, globalCache, totalRevenue };
```
Description: `globalCache` e `totalRevenue` são variáveis mutáveis no escopo do módulo, exportadas por valor/referência e alteradas por função livre (`logAndCache`) chamada a partir de qualquer lugar da aplicação.
Impact: Estado compartilhado sem controle de concorrência; em múltiplos workers/processos o cache fica inconsistente; não há forma de isolar esse estado em testes.
Recommendation: Eliminar o cache global; se necessário, encapsular em um serviço com interface explícita (`services/cacheService.js`) instanciado pela composition root, sem exportar a variável mutável diretamente.

### F07 [HIGH] Acoplamento forte / sem injeção de dependência
File: src/AppManager.js:4-9, src/app.js:8-10
Catalog: AP-09 | Fix: PB-07
Evidence:
```js
class AppManager {
    constructor() {
        this.db = new sqlite3.Database(':memory:');
    }
}
// src/app.js:8-10
const manager = new AppManager();
manager.initDb();
manager.setupRoutes(app);
```
Description: A conexão com o banco é criada dentro do construtor da própria classe que também define as rotas, e o boot (`initDb`/`setupRoutes`) é disparado diretamente no módulo de entrada, sem uma factory que permita injetar um banco de teste ou adiar a inicialização.
Impact: Impossível substituir o banco por um dublê em testes unitários; qualquer erro de seed quebra o processo de import/boot inteiro.
Recommendation: Criar `database/connection.js` responsável por abrir a conexão e expor helpers promisificados; `createApp(db)` em `src/app.js` como composition root que recebe a conexão por parâmetro.

### F08 [HIGH] Callback hell / escrita multi-etapas sem transação
File: src/AppManager.js:37-77, src/AppManager.js:83-129
Catalog: AP-12 | Fix: PB-10
Evidence:
```js
this.db.get("SELECT * FROM courses WHERE id = ? AND active = 1", [cid], (err, course) => {
    this.db.get("SELECT id FROM users WHERE email = ?", [e], (err, user) => {
        // ... mais 4 níveis de callback aninhado, contador manual (coursesPending--, enrPending--)
    });
});
```
Description: O checkout aninha 5+ níveis de callbacks (`db.get` → `db.get` → `db.run` → `db.run` → `db.run`) e usa o workaround `const self = this` (linha 26) para manter o contexto; a matrícula, o pagamento e o log de auditoria são três `INSERT`s separados sem `BEGIN/COMMIT/ROLLBACK`. O relatório financeiro (linhas 83-129) usa contadores manuais (`coursesPending--`, `enrPending--`) para saber quando todas as consultas assíncronas terminaram.
Impact: Se o `INSERT` de pagamento falhar após a matrícula ter sido criada, o usuário fica matriculado sem pagamento registrado (dado inconsistente); o fluxo é difícil de ler, testar e dar manutenção.
Recommendation: Promisificar o driver (`util.promisify` ou wrapper em `database/connection.js`) e reescrever o checkout com `async/await` dentro de uma transação (`BEGIN`/`COMMIT`/`ROLLBACK`) em `services/checkoutService.js`; substituir os contadores manuais do relatório por `Promise.all` sobre consultas agregadas.

### F09 [MEDIUM] Consultas N+1 no relatório financeiro
File: src/AppManager.js:83-127
Catalog: AP-13 | Fix: PB-09
Evidence:
```js
courses.forEach(c => {
    this.db.all("SELECT * FROM enrollments WHERE course_id = ?", [c.id], (err, enrollments) => {
        enrollments.forEach(enr => {
            this.db.get("SELECT name, email FROM users WHERE id = ?", [enr.user_id], ...);
            this.db.get("SELECT amount, status FROM payments WHERE enrollment_id = ?", [enr.id], ...);
        });
    });
});
```
Description: Para montar o relatório, o código executa 1 query de matrículas por curso e, para cada matrícula, mais 2 queries (usuário e pagamento) — o número de consultas cresce linearmente com o volume de dados.
Impact: Com muitos cursos/matrículas, o endpoint `/api/admin/financial-report` faz centenas de round-trips ao banco, degradando a latência.
Recommendation: Substituir por um único `JOIN` (ou poucas queries agregadas com `GROUP BY`) em `models/reportModel.js`, retornando os dados já agregados ao `reportService.js`.

### F10 [MEDIUM] Erros engolidos / callbacks ignorando `err`
File: src/AppManager.js:92, src/AppManager.js:104, src/AppManager.js:106, src/AppManager.js:133
Catalog: AP-16 | Fix: PB-11
Evidence:
```js
this.db.all("SELECT * FROM enrollments WHERE course_id = ?", [c.id], (err, enrollments) => {
    let enrPending = enrollments.length; // err nunca é checado
// src/AppManager.js:133
this.db.run("DELETE FROM users WHERE id = ?", [id], (err) => {
    res.send("Usuário deletado..."); // err nunca é checado
});
```
Description: Vários callbacks do `sqlite3` recebem `err` como primeiro parâmetro mas nunca o verificam antes de usar o resultado ou responder sucesso; não existe handler de erro centralizado.
Impact: Uma falha de banco no meio do relatório lança exceção não tratada (`enrollments.length` de `undefined`) ou faz o DELETE "ter sucesso" para o cliente mesmo quando a query falhou.
Recommendation: Centralizar tratamento de erro em um middleware (`middlewares/errorHandler.js`) e, em cada acesso a dados, propagar o `err` para `next(err)`/rejeitar a Promise em vez de ignorá-lo.

### F11 [MEDIUM] Ausência de integridade referencial no delete
File: src/AppManager.js:131-137
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
Description: O próprio texto da resposta admite que matrículas e pagamentos do usuário excluído ficam órfãos no banco — não há `ON DELETE CASCADE`, nem exclusão/realocação explícita dos registros dependentes.
Impact: Relatórios futuros (ex.: `financial-report`) exibirão "Unknown" para alunos cujo usuário foi deletado, e linhas de `payments`/`enrollments` ficam sem dono, corrompendo agregações.
Recommendation: Ao excluir o usuário, dentro de uma transação, excluir (ou arquivar) matrículas e pagamentos relacionados em `models/userModel.js`/`services/userService.js`; habilitar `PRAGMA foreign_keys = ON` no `database/connection.js`.

### F12 [MEDIUM] Validação de entrada ausente/inconsistente
File: src/AppManager.js:29-35
Catalog: AP-15 | Fix: PB-13
Evidence:
```js
let u = req.body.usr;
let e = req.body.eml;
let p = req.body.pwd;
let cid = req.body.c_id;
let cc = req.body.card;
if (!u || !e || !cid || !cc) return res.status(400).send("Bad Request");
```
Description: Apenas presença é validada (`!u`, `!e`, `!cid`, `!cc`); não há checagem de tipo/formato para `c_id` (deveria ser numérico), nem validação do formato do cartão além do prefixo numérico usado depois para decidir aprovação; `pwd` não é obrigatório mesmo criando conta nova.
Impact: Um `c_id` não numérico ou um corpo malformado só é pego tardiamente pela query (erro genérico), em vez de um 400 claro e imediato.
Recommendation: Criar um validador reutilizável em `controllers/checkoutController.js` (ou `validators/`) que valide tipos e formatos antes de chamar o serviço.

### F13 [LOW] `console.log` como logging
File: src/app.js:13, src/utils.js:13
Catalog: AP-23 | Fix: PB-15
Evidence:
```js
console.log(`Frankenstein LMS rodando na porta ${config.port}...`);
console.log(`[LOG] Salvando no cache: ${key}`);
```
Description: Eventos de inicialização e cache são logados via `console.log`, sem níveis, estrutura ou possibilidade de desligar/rotear (o uso do checkout já foi tratado separadamente em F04 por expor dados sensíveis).
Impact: Não há como filtrar/rotear logs em produção; mistura de logs de debug e operação.
Recommendation: Usar um logger simples (ex.: módulo nativo `console` encapsulado em `config/logger.js` com níveis, ou `pino`/`winston` apenas se já fosse dependência — aqui manter sem nova dependência, só padronizar o encapsulamento).

### F14 [LOW] Números/strings mágicos
File: src/AppManager.js:46, src/utils.js:19
Catalog: AP-20 | Fix: PB-15
Evidence:
```js
let status = cc.startsWith("4") ? "PAID" : "DENIED";
// src/utils.js:19
for(let i = 0; i < 10000; i++) {
```
Description: O prefixo `"4"` (bandeira de cartão) e o literal `10000` (iterações do hash) estão embutidos no código sem nome ou constante explicando seu significado; os literais `"PAID"`/`"DENIED"` são repetidos em várias partes do arquivo.
Impact: Mudar a regra exige caça ao literal espalhado pelo código; risco de divergência entre os pontos que comparam o status.
Recommendation: Extrair para constantes nomeadas em `config/constants.js` (`PAYMENT_STATUS.PAID`, `PAYMENT_STATUS.DENIED`).

### F15 [LOW] Nomenclatura pobre
File: src/AppManager.js:29-33, src/utils.js:12, src/utils.js:17
Catalog: AP-21 | Fix: PB-15
Evidence:
```js
let u = req.body.usr;
let e = req.body.eml;
let p = req.body.pwd;
let cid = req.body.c_id;
let cc = req.body.card;
```
Description: Identificadores de domínio reduzidos a uma ou duas letras (`u, e, p, cid, cc`); `badCrypto` (nome que admite ser ruim em vez de ser removido) e `logAndCache` (um nome para duas responsabilidades: logar e cachear).
Impact: Dificulta leitura e revisão; nomes que "confessam" o problema (`badCrypto`) sinalizam dívida técnica conhecida e não corrigida.
Recommendation: Renomear para `username, email, password, courseId, cardNumber` ao mover a lógica para `controllers/checkoutController.js`; remover `badCrypto`/`logAndCache` ao extrair hashing (F03) e cache (F06).

### F16 [LOW] Import/variável morta (`totalRevenue`)
File: src/utils.js:10, src/utils.js:25, src/AppManager.js:2
Catalog: AP-22 | Fix: PB-15
Evidence:
```js
let totalRevenue = 0;
// src/utils.js:25
module.exports = { config, logAndCache, badCrypto, globalCache, totalRevenue };
// src/AppManager.js:2
const { config, logAndCache, badCrypto, totalRevenue } = require('./utils');
```
Description: `totalRevenue` é declarada, exportada e importada em `AppManager.js`, mas nunca é lida nem incrementada em nenhum lugar do código — é uma variável morta.
Impact: Código morto confunde quem lê, sugerindo uma funcionalidade (acumular receita total) que não existe de fato.
Recommendation: Remover `totalRevenue` de `utils.js` e do import em `AppManager.js` (o cálculo real de receita já é feito por curso no relatório, F09).

### F17 [LOW] Uso não idiomático de `let` em vez de `const`
File: src/AppManager.js:29-33, src/AppManager.js:43, src/AppManager.js:46, src/AppManager.js:52, src/AppManager.js:68, src/AppManager.js:81, src/AppManager.js:86, src/AppManager.js:90, src/AppManager.js:93, src/AppManager.js:132
Catalog: AP-24 | Fix: PB-15
Evidence:
```js
let u = req.body.usr;
let hash = badCrypto(p || "123456");
let report = [];
```
Description: Variáveis que nunca são reatribuídas (`u, e, p, cid, cc, hash, report, courseData, id`, entre outras) são declaradas com `let` em vez de `const`.
Impact: Puramente estilístico — não comunica a intenção de imutabilidade e pode mascarar reatribuições acidentais futuras.
Recommendation: Trocar por `const` ao reescrever os arquivos durante a migração para a estrutura MVC.

## Deprecated APIs
Nenhuma API deprecated encontrada (sem uso de `new Buffer`, `url.parse`, `req.param()`, `app.del()`, `var`, `createCipher()` nas versões de Node v20 / Express ^4.18.2 em uso). O uso de callbacks do driver `sqlite3` (em vez de Promises/async-await) não é uma API deprecated, mas é tratado como anti-padrão de legibilidade em F08.

## Proposed Target Architecture
```
ecommerce-api-legacy/
├── package.json                 # "start": "node src/app.js" (inalterado)
├── .env.example                 # NOVO: documenta DB_PASS, PAYMENT_GATEWAY_KEY, SMTP_USER, ADMIN_TOKEN, PORT
└── src/
    ├── app.js                   # createApp(): composition root
    ├── config/
    │   ├── index.js              # process.env + PAYMENT_STATUS/constantes (substitui utils.js:config)
    │   └── logger.js              # encapsula console.* com níveis
    ├── database/
    │   └── connection.js          # abre sqlite3 ':memory:', helpers promisificados, transaction(), initSchema()+seed()
    ├── models/
    │   ├── userModel.js            # CRUD users (sem senha em texto, sem campos sensíveis)
    │   ├── courseModel.js
    │   ├── enrollmentModel.js
    │   └── paymentModel.js
    ├── services/
    │   ├── checkoutService.js      # regra de negócio do checkout (hash de senha, aprovação, transação)
    │   └── reportService.js        # relatório financeiro via query agregada (resolve N+1)
    ├── controllers/
    │   ├── checkoutController.js
    │   ├── reportController.js
    │   └── userController.js
    ├── routes/
    │   ├── checkoutRoutes.js
    │   ├── adminRoutes.js
    │   ├── userRoutes.js
    │   └── index.js               # monta todos os routers
    └── middlewares/
        ├── errorHandler.js        # formato de erro único
        └── adminAuth.js           # guarda X-Admin-Token para /api/admin/*
```
Estratégia (maturidade Monolítica, `mvc-guidelines.md` §5): reestruturar o monólito por completo — criar o layout acima, mover cada responsabilidade de `AppManager.js`/`utils.js` para sua camada, e então **remover** `src/AppManager.js` e `src/utils.js` (substituídos integralmente), mantendo `npm start` e a porta 3000 inalterados.

================================
Total: 17 findings
================================
