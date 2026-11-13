================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python (ambiente local 3.14.4) + Flask 3.1.1
Files:   4 analyzed | ~780 lines of code
Architecture: Monolítica
Date:    2026-11-13

## Summary
CRITICAL: 6 | HIGH: 5 | MEDIUM: 5 | LOW: 4

| ID | Severity | Anti-pattern | Location |
|----|----------|--------------|----------|
| F01 | CRITICAL | Credenciais hardcoded | app.py:7 (+1) |
| F02 | CRITICAL | SQL Injection | models.py:28 (+22) |
| F03 | CRITICAL | Endpoint admin sem autenticação executando SQL arbitrário/destrutivo | app.py:47-57 (+1) |
| F04 | CRITICAL | Senhas em texto puro | database.py:75-79 (+2) |
| F05 | CRITICAL | Exposição de dados sensíveis | models.py:83 (+2) |
| F06 | CRITICAL | God Module | models.py:1-314 |
| F07 | HIGH | Lógica de negócio no controller (fat controller) | controllers.py:24-62 (+3) |
| F08 | HIGH | Conexão de banco global mutável | database.py:4 (+2) |
| F09 | HIGH | Acoplamento forte / sem factory / efeitos no boot | app.py:1-9 (+1) |
| F10 | HIGH | Defaults de runtime inseguros | app.py:8 (+3) |
| F11 | HIGH | Escrita multi-etapas sem transação | models.py:133-169 |
| F12 | MEDIUM | Consultas N+1 | models.py:171-201 (+3) |
| F13 | MEDIUM | Lógica duplicada | controllers.py:28-50 (+2) |
| F14 | MEDIUM | Validação inconsistente / ausente | controllers.py:64-96 (+1) |
| F15 | MEDIUM | Exceções genéricas vazando detalhes internos | controllers.py:10 (+16) |
| F16 | MEDIUM | Integridade referencial ausente no delete | controllers.py:98-109 (+2) |
| F17 | LOW | Números/strings mágicos | controllers.py:47 (+4) |
| F18 | LOW | Import não utilizado | models.py:2 |
| F19 | LOW | `print` usado como logging | app.py:56 (+16) |
| F20 | LOW | Parâmetro `id` sombreando builtin | controllers.py:14 (+7) |

## Findings

### F01 [CRITICAL] Credenciais hardcoded
File: app.py:7, controllers.py:289
Catalog: AP-01 | Fix: PB-01
Evidence:
```python
# app.py:7
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
```
Description: A `SECRET_KEY` do Flask está escrita como literal no código-fonte e o mesmo literal é repetido em `controllers.py:289` (no `/health`).
Impact: Qualquer pessoa com acesso ao repositório (ou a uma imagem publicada) pode assinar/forjar sessões e cookies da aplicação; rotacionar a chave exige alterar e reimplantar código.
Recommendation: Ler `SECRET_KEY` de variável de ambiente (`config/settings.py`), com geração de valor efêmero via `secrets.token_hex(32)` quando ausente em desenvolvimento, e nunca devolvê-la em respostas HTTP.

### F02 [CRITICAL] SQL Injection
File: models.py:28, models.py:47-50, models.py:57-61, models.py:68, models.py:92, models.py:109-111, models.py:126-129, models.py:140, models.py:148-151, models.py:155, models.py:157-161, models.py:163-166, models.py:174, models.py:188, models.py:192, models.py:220, models.py:224, models.py:279-281, models.py:291, models.py:293, models.py:295, models.py:297, models.py:299
Catalog: AP-02 | Fix: PB-02
Evidence:
```python
# models.py:109-111
cursor.execute(
    "SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"
)
```
Description: Praticamente todas as consultas de `models.py` são montadas por concatenação de string com dados vindos direta ou indiretamente do request (nome, descrição, categoria, email, senha, termo de busca, preço mínimo/máximo, status).
Impact: Qualquer cliente pode ler, alterar ou apagar dados fora do previsto; o caso de `login_usuario` permite bypass de autenticação com payload como `' OR '1'='1`. `buscar_produtos` (termo de busca) é igualmente explorável via `LIKE`.
Recommendation: Reescrever todas as queries com parâmetros `?` dentro dos models de cada domínio (`produto_model.py`, `usuario_model.py`, `pedido_model.py`).

### F03 [CRITICAL] Endpoint admin sem autenticação executando SQL arbitrário/destrutivo
File: app.py:47-57, app.py:59-78
Catalog: AP-03 | Fix: PB-04
Evidence:
```python
# app.py:59-69
@app.route("/admin/query", methods=["POST"])
def executar_query():
    dados = request.get_json()
    query = dados.get("sql", "")
    ...
    cursor.execute(query)
```
Description: `/admin/reset-db` apaga todas as tabelas e `/admin/query` executa qualquer SQL enviado no corpo da requisição — nenhum dos dois exige autenticação.
Impact: Um atacante remoto consegue destruir ou extrair todo o banco de dados com uma única requisição HTTP sem credenciais.
Recommendation: Manter as rotas, mas exigir um guard de autenticação admin (`X-Admin-Token` validado contra `ADMIN_TOKEN` do ambiente); sem o header correto, responder 403.

### F04 [CRITICAL] Senhas em texto puro
File: database.py:75-79, models.py:109-111, models.py:126-129
Catalog: AP-04 | Fix: PB-03
Evidence:
```python
# database.py:75-79
usuarios = [
    ("Admin", "admin@loja.com", "admin123", "admin"),
    ("João Silva", "joao@email.com", "123456", "cliente"),
    ("Maria Santos", "maria@email.com", "senha123", "cliente"),
]
```
Description: As senhas de seed são literais em texto puro, o cadastro (`criar_usuario`) grava a senha recebida sem hash e o login (`login_usuario`) compara a senha em texto puro armazenada no banco.
Impact: Um leak do banco (ou do próprio `/admin/query`, ver F03) expõe a senha real de todos os usuários, reaproveitável em outros serviços (credential stuffing).
Recommendation: Usar `werkzeug.security.generate_password_hash`/`check_password_hash` (já incluso no Flask) no cadastro, no seed e no login.

### F05 [CRITICAL] Exposição de dados sensíveis
File: models.py:83, models.py:99, controllers.py:286-289
Catalog: AP-05 | Fix: PB-03, PB-15
Evidence:
```python
# controllers.py:286-289
"ambiente": "producao",
"db_path": "loja.db",
"debug": True,
"secret_key": "minha-chave-super-secreta-123"
```
Description: `get_todos_usuarios`/`get_usuario_por_id` incluem o campo `senha` na serialização devolvida por `GET /usuarios` e `GET /usuarios/:id`; `GET /health` devolve `secret_key`, `db_path` e `debug`.
Impact: Qualquer cliente da API consegue ler a senha (mesmo após hashing, o hash não deveria ser exposto) de qualquer usuário, além de segredos de configuração via `/health`.
Recommendation: Remover `senha` da serialização dos models de usuário; remover `secret_key`/`db_path`/`debug` do `/health`.

### F06 [CRITICAL] God Module
File: models.py:1-314
Catalog: AP-06 | Fix: PB-05, PB-06
Evidence:
```python
# models.py — produtos (4-70), usuarios (72-131), pedidos (133-233) e
# relatórios (235-273) no mesmo módulo, com SQL e regras de negócio juntos
```
Description: Um único arquivo concentra acesso a dados de 4 domínios não relacionados (produtos, usuários, pedidos, relatórios) junto com regras de negócio (checagem de estoque em `criar_pedido:144-145`, cálculo de desconto em `relatorio_vendas:256-262`).
Impact: Qualquer alteração em um domínio arrisca quebrar os outros; impossível testar uma regra isoladamente; mescla camada de dados com regras.
Recommendation: Dividir em `models/produto_model.py`, `models/usuario_model.py`, `models/pedido_model.py`; mover regras de negócio (desconto, estoque) para `services/relatorio_service.py` e para o próprio model/controller do pedido.

### F07 [HIGH] Lógica de negócio no controller (fat controller)
File: controllers.py:24-62, controllers.py:64-96, controllers.py:188-220, controllers.py:237-255
Catalog: AP-07 | Fix: PB-08
Evidence:
```python
# controllers.py:208-210
print("ENVIANDO EMAIL: Pedido " + str(resultado["pedido_id"]) + " criado para usuario " + str(usuario_id))
print("ENVIANDO SMS: Seu pedido foi recebido!")
print("ENVIANDO PUSH: Novo pedido recebido pelo sistema")
```
Description: `criar_produto`/`atualizar_produto` validam regras de domínio (faixas de preço/estoque, tamanho de nome, categorias válidas) diretamente no handler HTTP; `criar_pedido`/`atualizar_status_pedido` disparam "notificações" (simuladas via `print`) como efeito colateral dentro do controller.
Impact: Regras não podem ser reusadas nem testadas sem subir o Flask; a mesma validação é reescrita em cada handler.
Recommendation: Mover validação para `validators/produto_validator.py` e notificações para `services/notification_service.py`, chamados pelo controller.

### F08 [HIGH] Conexão de banco global mutável
File: database.py:4, database.py:8, database.py:10
Catalog: AP-08 | Fix: PB-12
Evidence:
```python
# database.py:4-10
db_connection = None
db_path = "loja.db"

def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect(db_path, check_same_thread=False)
```
Description: Uma única conexão SQLite é criada uma vez e compartilhada globalmente entre todas as requisições/threads via `global` e `check_same_thread=False`.
Impact: Race conditions entre requisições concorrentes, estado de transação vazando entre requests (ver F11), impossível isolar conexões em testes.
Recommendation: Abrir uma conexão por requisição usando `flask.g`, fechada em `teardown_appcontext`.

### F09 [HIGH] Acoplamento forte / sem factory / efeitos no boot
File: app.py:1-9, app.py:82
Catalog: AP-09 | Fix: PB-07
Evidence:
```python
# app.py:1-9
import controllers
from database import get_db

app = Flask(__name__)
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.config["DEBUG"] = True
CORS(app)
```
Description: O objeto `app` é criado e configurado no nível do módulo (sem `create_app()`), importando diretamente os módulos concretos `controllers`/`database`; `get_db()` é chamado em `app.py:82` antes do `app.run`, inicializando schema e seed de forma síncrona e sem possibilidade de injeção de dependência.
Impact: Impossível trocar banco/serviços em testes; qualquer import do módulo `app` já configura a aplicação inteira.
Recommendation: Introduzir `create_app()` como composition root; mover registro de rotas, config e inicialização de schema para dentro da factory.

### F10 [HIGH] Defaults de runtime inseguros
File: app.py:8, app.py:9, app.py:88, controllers.py:286
Catalog: AP-10 | Fix: PB-01
Evidence:
```python
# app.py:8-9, 88
app.config["DEBUG"] = True
CORS(app)
...
app.run(host="0.0.0.0", port=5000, debug=True)
```
Description: `DEBUG=True` fixo habilita o debugger interativo do Werkzeug (execução remota de código) exposto em `0.0.0.0`; `CORS(app)` libera todas as origens sem restrição; `controllers.py:286` ainda afirma `"ambiente": "producao"` contradizendo o `debug=True` real.
Impact: Em produção, qualquer erro não tratado abre o console interativo do Werkzeug para quem acessar a porta 5000; CORS irrestrito amplia a superfície de ataque.
Recommendation: `DEBUG` deve vir do ambiente com default `False`; `CORS_ORIGINS` configurável; `/health` deve refletir o valor real de `DEBUG`.

### F11 [HIGH] Escrita multi-etapas sem transação
File: models.py:133-169
Catalog: AP-12 | Fix: PB-10
Evidence:
```python
# models.py:148-166
cursor.execute("INSERT INTO pedidos ...")
pedido_id = cursor.lastrowid
for item in itens:
    cursor.execute("INSERT INTO itens_pedido ...")
    cursor.execute("UPDATE produtos SET estoque = estoque - ...")
db.commit()
```
Description: `criar_pedido` executa inserção do pedido, inserção de cada item e atualização de estoque em instruções separadas sem `BEGIN/COMMIT/ROLLBACK` explícito nem tratamento de falha parcial; como a conexão é global (F08), uma exceção no meio do loop deixa instruções pendentes na mesma conexão até o próximo `commit()` de **qualquer** requisição futura.
Impact: Falha em um item deixa pedido/estoque inconsistentes; escritas de uma requisição podem ser commitadas junto com as de outra.
Recommendation: Envolver toda a operação em `with db:` (transação) e garantir rollback explícito em caso de erro.

### F12 [MEDIUM] Consultas N+1
File: models.py:171-201, models.py:203-233, models.py:140, models.py:155
Catalog: AP-13 | Fix: PB-09
Evidence:
```python
# models.py:187-192
cursor2 = db.cursor()
cursor2.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"]))
itens = cursor2.fetchall()
for item in itens:
    cursor3 = db.cursor()
    cursor3.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))
```
Description: `get_pedidos_usuario` e `get_todos_pedidos` disparam uma query de itens por pedido e, dentro dela, uma query de produto por item; `criar_pedido` também busca o mesmo produto duas vezes (linhas 140 e 155) no mesmo loop.
Impact: O número de queries cresce linearmente com pedidos × itens, piorando latência conforme o volume de dados aumenta.
Recommendation: Substituir por um único `JOIN` entre `pedidos`, `itens_pedido` e `produtos`; em `criar_pedido`, reaproveitar o produto já buscado na checagem de estoque.

### F13 [MEDIUM] Lógica duplicada
File: controllers.py:28-50, controllers.py:74-90, models.py:12-21, models.py:31-40, models.py:304-313
Catalog: AP-14 | Fix: PB-13, PB-08
Evidence:
```python
# controllers.py:28-50 (criar_produto) repetido em controllers.py:74-90 (atualizar_produto)
if "nome" not in dados: ...
if "preco" not in dados: ...
if preco < 0: ...
```
Description: O bloco de validação de produto é reescrito quase idêntico em `criar_produto` e `atualizar_produto`; o mapeamento `row → dict` de produto aparece igual em `get_todos_produtos`, `get_produto_por_id` e `buscar_produtos`.
Impact: Uma correção de regra ou campo precisa ser replicada manualmente em 2-3 lugares, divergindo com o tempo.
Recommendation: Extrair a validação para `validators/produto_validator.py` e a serialização para um único método `_to_dict` no model de produto.

### F14 [MEDIUM] Validação inconsistente / ausente
File: controllers.py:64-96, controllers.py:195-203, models.py:139-146
Catalog: AP-15 | Fix: PB-13
Evidence:
```python
# controllers.py:81-90 — atualizar_produto não repete as checagens de
# criar_produto:47-54 (tamanho do nome, categoria válida)
```
Description: `atualizar_produto` não valida tamanho de nome (2-200) nem categoria válida, ao contrário de `criar_produto`; `criar_pedido` (controller e model) acessa `item["produto_id"]`/`item["quantidade"]` sem validar a presença/tipo dessas chaves antes de usá-las.
Impact: Dados inválidos podem ser persistidos via `PUT /produtos/:id`; um item malformado em `POST /pedidos` gera `KeyError`/`TypeError` capturado genericamente como 500 em vez de um 400 claro.
Recommendation: Reusar o mesmo validator de produto em create/update; validar a forma de cada item do pedido antes de chamar o model.

### F15 [MEDIUM] Exceções genéricas vazando detalhes internos
File: controllers.py:10, controllers.py:21, controllers.py:60, controllers.py:95, controllers.py:108, controllers.py:125, controllers.py:133, controllers.py:143, controllers.py:164, controllers.py:185, controllers.py:218, controllers.py:226, controllers.py:234, controllers.py:254, controllers.py:261, controllers.py:291, app.py:77
Catalog: AP-16 | Fix: PB-11
Evidence:
```python
# controllers.py:60-62
except Exception as e:
    print("ERRO ao criar produto: " + str(e))
    return jsonify({"erro": str(e)}), 500
```
Description: Todo handler repete o mesmo padrão `try/except Exception as e: return {"erro": str(e)}, 500`, devolvendo a mensagem interna da exceção (incluindo erros de SQL) diretamente ao cliente; não há tratamento centralizado.
Impact: Detalhes de implementação (nomes de coluna, erros de SQLite) vazam ao cliente; formato de erro inconsistente entre rotas; bugs reais ficam mascarados por um 500 genérico.
Recommendation: Centralizar em `middlewares/error_handler.py` com uma hierarquia de erros tipados e mensagem genérica para exceções não mapeadas.

### F16 [MEDIUM] Integridade referencial ausente no delete
File: controllers.py:98-109, models.py:65-70, database.py:14-53
Catalog: AP-17 | Fix: PB-16
Evidence:
```python
# models.py:65-70
def deletar_produto(id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM produtos WHERE id = " + str(id))
```
Description: `DELETE /produtos/:id` remove a linha de `produtos` sem verificar se existem `itens_pedido` referenciando aquele produto; o schema (`database.py:14-53`) nunca declara chaves estrangeiras nem `PRAGMA foreign_keys`.
Impact: Pedidos antigos passam a referenciar um `produto_id` inexistente; `get_pedidos_usuario`/`get_todos_pedidos` já tratam isso com um fallback (`"Desconhecido"`), evidenciando que o dado órfão é esperado em vez de prevenido.
Recommendation: Em vez de apagar fisicamente um produto referenciado em pedidos, marcar `ativo = 0` (exclusão lógica) e filtrar por `ativo = 1` nas listagens.

### F17 [LOW] Números/strings mágicos
File: controllers.py:47, controllers.py:49, controllers.py:52, controllers.py:242, models.py:257-262
Catalog: AP-20 | Fix: PB-15
Evidence:
```python
# models.py:257-262
if faturamento > 10000:
    desconto = faturamento * 0.1
elif faturamento > 5000:
    desconto = faturamento * 0.05
```
Description: Faixas de desconto, limites de tamanho de nome, lista de categorias válidas e lista de status de pedido estão todos embutidos como literais dentro das funções.
Impact: Mudar uma regra de negócio exige caçar o literal certo em vários arquivos; fácil divergir (ex.: categorias válidas só existe em `controllers.py:52`, nada impede um status diferente ser inserido via SQL direto).
Recommendation: Mover para constantes em `config/settings.py` (`CATEGORIAS_VALIDAS`, `FAIXAS_DESCONTO`, `STATUS_PEDIDO`).

### F18 [LOW] Import não utilizado
File: models.py:2
Catalog: AP-22 | Fix: PB-15
Evidence:
```python
# models.py:1-2
from database import get_db
import sqlite3
```
Description: `sqlite3` é importado em `models.py` mas nenhum símbolo do módulo é referenciado no arquivo.
Impact: Nenhum em runtime; ruído que sugere incorretamente uma dependência direta do driver no model.
Recommendation: Remover o import.

### F19 [LOW] `print` usado como logging
File: app.py:56, app.py:83-86, controllers.py:8, controllers.py:11, controllers.py:57, controllers.py:61, controllers.py:106, controllers.py:161, controllers.py:179, controllers.py:182, controllers.py:208-210, controllers.py:219, controllers.py:248, controllers.py:250
Catalog: AP-23 | Fix: PB-15
Evidence:
```python
# controllers.py:11
print("ERRO: " + str(e))
```
Description: Toda a aplicação usa `print()` para registrar eventos de negócio e erros, inclusive mensagens de erro que deveriam ir para um log estruturado.
Impact: Sem níveis de severidade, sem estrutura, sem possibilidade de silenciar ou rotear esses eventos em produção.
Recommendation: Substituir por `logging.getLogger(__name__)` configurado no composition root.

### F20 [LOW] Parâmetro `id` sombreando builtin
File: controllers.py:14, controllers.py:64, controllers.py:98, controllers.py:136, models.py:24, models.py:54, models.py:65, models.py:89
Catalog: AP-24 | Fix: PB-15
Evidence:
```python
# controllers.py:14
def buscar_produto(id):
```
Description: Oito funções usam `id` como nome de parâmetro, sombreando o builtin `id()` do Python dentro do próprio escopo da função.
Impact: Puramente estilístico aqui (nenhuma função chama `id()` internamente), mas reduz legibilidade e é um padrão a evitar.
Recommendation: Renomear para um nome de domínio (`produto_id`, `usuario_id`) ao mover as funções para os novos models/controllers.

## Deprecated APIs
Nenhuma API deprecated encontrada (grep por `utcnow`, `.query.get(`, `before_first_request`, `distutils`, `pkg_resources` sem ocorrências; projeto não usa ORM nem datetime).

## Proposed Target Architecture
Maturidade: Monolítica → estratégia "criar o layout completo, dividir por domínio, mover cada função para sua camada e apagar os arquivos antigos" (mvc-guidelines.md §5).

```
code-smells-project/
├── app.py                      # entry point fino: from src.app import create_app
├── requirements.txt
├── .env.example                # SECRET_KEY, FLASK_DEBUG, HOST, PORT, DB_PATH, ADMIN_TOKEN, CORS_ORIGINS
└── src/
    ├── app.py                  # create_app(): composition root
    ├── config/settings.py      # env vars + constantes (categorias, faixas de desconto, status)
    ├── database.py             # get_db() por requisição (flask.g), init_schema(), seed_if_empty()
    ├── models/                 # produto_model.py, usuario_model.py, pedido_model.py
    ├── controllers/            # produto_, usuario_, pedido_, relatorio_, health_, admin_controller.py
    ├── views/                  # Blueprints: produto_, usuario_, pedido_, relatorio_, health_, admin_routes.py
    ├── services/                # notification_service.py, relatorio_service.py
    ├── validators/              # produto_validator.py, usuario_validator.py, pedido_validator.py
    └── middlewares/
        ├── error_handler.py    # AppError + handlers centralizados
        └── auth.py             # require_admin (ADMIN_TOKEN) para /admin/*
```

================================
Total: 20 findings
================================
