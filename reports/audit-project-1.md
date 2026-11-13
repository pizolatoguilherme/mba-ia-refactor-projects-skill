================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python (3.14 local) + Flask 3.1.1
Files:   4 analisados | ~780 linhas de código
Architecture: Monolítica — models.py concentra SQL concatenada e regras de negócio (estoque, desconto) de todos os domínios; controllers.py replica o mesmo tratamento de erro em cada função; app.py define rotas administrativas com SQL bruto direto na camada de entrada, sem passar por controller/model
Date:    2026-11-13

## Summary
CRITICAL: 6 | HIGH: 5 | MEDIUM: 7 | LOW: 4

| ID | Severity | Anti-pattern | Location |
|----|----------|--------------|----------|
| F01 | CRITICAL | Credencial/segredo hardcoded | app.py:7 |
| F02 | CRITICAL | SQL Injection | models.py:28 (+17) |
| F03 | CRITICAL | Endpoint admin destrutivo/SQL arbitrário sem autenticação | app.py:47-78 |
| F04 | CRITICAL | Senha em texto puro (armazenamento e comparação) | database.py:75-79 (+2) |
| F05 | CRITICAL | Exposição de dados sensíveis em respostas | models.py:79-86 (+3) |
| F06 | CRITICAL | God Module | models.py:1-314 (+1) |
| F07 | HIGH | Lógica de negócio e efeitos colaterais no controller | controllers.py:24-96 (+2) |
| F08 | HIGH | Estado global mutável / conexão singleton compartilhada | database.py:4 (+3) |
| F09 | HIGH | Acoplamento forte / sem app factory / efeitos no import | app.py:1-30 |
| F10 | HIGH | Defaults de runtime inseguros | app.py:8 (+3) |
| F11 | HIGH | Autenticação/autorização inexistente | controllers.py:167-220 |
| F12 | MEDIUM | Escrita multi-etapas sem transação segura | models.py:133-169 |
| F13 | MEDIUM | Consultas N+1 | models.py:187-199 (+1) |
| F14 | MEDIUM | Lógica duplicada | controllers.py:28-50 (+2) |
| F15 | MEDIUM | Validação de entrada ausente/inconsistente | controllers.py:64-96 (+1) |
| F16 | MEDIUM | Exceções engolidas / detalhes internos expostos | controllers.py:10-12 (+15) |
| F17 | MEDIUM | Falta de integridade referencial no delete | models.py:65-70 |
| F18 | MEDIUM | Responsabilidade mal posicionada | app.py:47-78 |
| F19 | LOW | Números/strings mágicas | controllers.py:52 (+2) |
| F20 | LOW | Import não utilizado | models.py:2 |
| F21 | LOW | `print` como logging | app.py:56 (+4) |
| F22 | LOW | Construções não idiomáticas (parâmetro `id` sombreia builtin) | controllers.py:14 (+7) |

## Findings

### F01 [CRITICAL] Credencial/segredo hardcoded
File: app.py:7
Catalog: AP-01 | Fix: PB-01
Evidence:
```python
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
```
Description: A `SECRET_KEY` do Flask está escrita como literal no código-fonte.
Impact: Qualquer pessoa com acesso ao repositório pode forjar sessões/cookies assinados; rotacionar o segredo exige alterar e reimplantar código.
Recommendation: Ler de variável de ambiente (`os.environ.get("SECRET_KEY")`) com fallback aleatório (`secrets.token_hex(32)`) e aviso de log em dev, movido para `config/settings.py`.

### F02 [CRITICAL] SQL Injection
File: models.py:28, models.py:48-50, models.py:58-61, models.py:68, models.py:92, models.py:109-111, models.py:126-129, models.py:140, models.py:148-151, models.py:155-166, models.py:174, models.py:188, models.py:192, models.py:220, models.py:224, models.py:279-280, models.py:289-297
Catalog: AP-02 | Fix: PB-02
Evidence:
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
```
Description: Praticamente toda consulta em `models.py` é montada por concatenação de strings com dados vindos diretamente do request (IDs de path, corpo JSON, query string), incluindo a consulta de login.
Impact: Qualquer cliente pode ler, alterar ou destruir dados do banco; a consulta de login permite bypass de autenticação com payload como `' OR '1'='1`.
Recommendation: Reescrever todas as queries com parâmetros (`?`) e `cursor.execute(sql, (params,))`, dentro dos models de cada domínio (`produto_model.py`, `usuario_model.py`, `pedido_model.py`).

### F03 [CRITICAL] Endpoint admin destrutivo/SQL arbitrário sem autenticação
File: app.py:47-78
Catalog: AP-03 | Fix: PB-04
Evidence:
```python
@app.route("/admin/query", methods=["POST"])
def executar_query():
    dados = request.get_json()
    query = dados.get("sql", "")
    cursor.execute(query)
```
Description: `/admin/reset-db` apaga todas as tabelas e `/admin/query` executa SQL arbitrário vindo do corpo da requisição — nenhuma das duas rotas exige autenticação.
Impact: Um atacante não autenticado pode apagar ou exfiltrar o banco inteiro com uma única requisição HTTP.
Recommendation: Manter as rotas, mas exigir header `X-Admin-Token` validado contra `ADMIN_TOKEN` (config), respondendo 403 se o token não for configurado/não bater; mover a lógica para um `admin_controller.py` dedicado.

### F04 [CRITICAL] Senha em texto puro (armazenamento e comparação)
File: database.py:75-79, models.py:109-111, models.py:122-131
Catalog: AP-04 | Fix: PB-03
Evidence:
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
```
Description: Senhas são inseridas e comparadas em texto puro — tanto no seed inicial quanto no cadastro (`criar_usuario`) e no login (`login_usuario`).
Impact: Um leak do banco expõe a senha real de todos os usuários, reutilizável em outros serviços (credential stuffing).
Recommendation: Hashear com `werkzeug.security.generate_password_hash` no cadastro e validar com `check_password_hash` no login (já incluso no Flask, sem nova dependência).

### F05 [CRITICAL] Exposição de dados sensíveis em respostas
File: models.py:79-86, models.py:94-102, controllers.py:128-144, controllers.py:276-290
Catalog: AP-05 | Fix: PB-03, PB-15
Evidence:
```python
return jsonify({"dados": usuarios, "sucesso": True}), 200
# usuarios inclui row["senha"] para cada usuário
...
"debug": True,
"secret_key": "minha-chave-super-secreta-123"
```
Description: `get_todos_usuarios`/`get_usuario_por_id` incluem o campo `senha` e são expostos sem filtro em `/usuarios` e `/usuarios/<id>`; `/health` devolve `secret_key`, `db_path` e `debug` no corpo da resposta.
Impact: Qualquer cliente da API consegue ler a senha (em texto puro) de qualquer usuário e o segredo da aplicação a partir de endpoints públicos.
Recommendation: Remover `senha`/`secret_key`/`db_path`/`debug` da serialização dos models e do `health_check`; serialização de entidade nunca inclui campos sensíveis (regra MVC §3.4).

### F06 [CRITICAL] God Module
File: models.py:1-314, controllers.py:1-292
Catalog: AP-06 | Fix: PB-05, PB-06
Evidence:
```python
# um único arquivo com acesso a dados + regras de negócio para produtos, usuários e pedidos
def criar_pedido(usuario_id, itens):
    ...
    total = total + (produto["preco"] * item["quantidade"])
```
Description: `models.py` concentra acesso a dados, SQL e regras de negócio (cálculo de total/estoque, elegibilidade de desconto) para três domínios não relacionados (produtos, usuários, pedidos) em um único arquivo; `controllers.py` replica a mesma estrutura para todos os domínios com tratamento de erro idêntico copiado 19 vezes.
Impact: Qualquer alteração em um domínio arrisca quebrar os outros; impossível testar uma regra isoladamente; arquivo de 300+ linhas misturando camadas.
Recommendation: Dividir em `models/produto_model.py`, `models/usuario_model.py`, `models/pedido_model.py` e `controllers/<dominio>_controller.py`, cada um só com seu domínio.

### F07 [HIGH] Lógica de negócio e efeitos colaterais no controller
File: controllers.py:24-62, controllers.py:64-96, controllers.py:208-210, controllers.py:247-250
Catalog: AP-07 | Fix: PB-08
Evidence:
```python
print("ENVIANDO EMAIL: Pedido " + str(resultado["pedido_id"]) + " criado para usuario " + str(usuario_id))
print("ENVIANDO SMS: Seu pedido foi recebido!")
print("ENVIANDO PUSH: Novo pedido recebido pelo sistema")
```
Description: `criar_produto`/`atualizar_produto` repetem o mesmo bloco de validação de campos; `criar_pedido` e `atualizar_status_pedido` disparam "notificações" (simuladas via `print`) diretamente no controller.
Impact: Regras não podem ser reutilizadas nem testadas sem HTTP; a cada novo canal de notificação o controller cresce mais.
Recommendation: Extrair validação para um validator reutilizável e as notificações para `services/notification_service.py`, chamado pelo controller.

### F08 [HIGH] Estado global mutável / conexão singleton compartilhada
File: database.py:4, database.py:7-10
Catalog: AP-08 | Fix: PB-12
Evidence:
```python
db_connection = None
def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect(db_path, check_same_thread=False)
```
Description: Uma única conexão SQLite é criada no módulo e reutilizada por todas as requisições/threads via `global`, com `check_same_thread=False`.
Impact: Condições de corrida entre requisições concorrentes; transações de uma requisição podem ser commitadas/misturadas com as de outra (ver F12).
Recommendation: Conexão por requisição usando `flask.g`, aberta no início e fechada em `teardown_appcontext` (padrão Flask + sqlite3).

### F09 [HIGH] Acoplamento forte / sem app factory / efeitos no import
File: app.py:1-30
Catalog: AP-09 | Fix: PB-07
Evidence:
```python
app = Flask(__name__)
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
...
app.add_url_rule("/produtos", "listar_produtos", controllers.listar_produtos, methods=["GET"])
```
Description: O app Flask é criado, configurado e todas as rotas são registradas no nível de módulo, no momento do import — não existe `create_app()`; `controllers.py` importa `models` e `database.get_db` diretamente, sem injeção.
Impact: Impossível criar múltiplas instâncias do app (ex.: testes) sem efeitos colaterais de import; troca de implementação de banco exige editar cada model.
Recommendation: Introduzir `create_app()` como composition root (mantendo `app.py` fino para preservar `python app.py`), registrar rotas via Blueprints dentro da factory.

### F10 [HIGH] Defaults de runtime inseguros
File: app.py:8, app.py:9, app.py:88, controllers.py:286, controllers.py:288
Catalog: AP-10 | Fix: PB-01
Evidence:
```python
app.config["DEBUG"] = True
...
app.run(host="0.0.0.0", port=5000, debug=True)
```
Description: Debug do Werkzeug habilitado com bind em `0.0.0.0`, CORS liberado para qualquer origem, e `/health` informa `"ambiente": "producao"` enquanto debug está ativo.
Impact: O debugger interativo do Werkzeug permite execução remota de código se exposto; CORS aberto facilita exfiltração via browser de qualquer origem.
Recommendation: `DEBUG`/`CORS` controlados por variável de ambiente, com `False`/origens restritas como default seguro.

### F11 [HIGH] Autenticação/autorização inexistente
File: controllers.py:167-220
Catalog: AP-11 | Fix: PB-04
Evidence:
```python
def criar_pedido():
    dados = request.get_json()
    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])
```
Description: O login (`/login`) não emite nenhum token/sessão; `/pedidos` aceita `usuario_id` diretamente do corpo da requisição, sem vínculo com um usuário autenticado.
Impact: Qualquer cliente pode criar pedidos em nome de qualquer `usuario_id` apenas adivinhando o número.
Recommendation: Fora do escopo implementar um sistema de auth completo (recomendação registrada); no mínimo, documentar a limitação e, junto com F03, proteger as rotas administrativas com `X-Admin-Token`.

### F12 [MEDIUM] Escrita multi-etapas sem transação segura
File: models.py:133-169
Catalog: AP-12 | Fix: PB-10
Evidence:
```python
cursor.execute("INSERT INTO pedidos (usuario_id, status, total) VALUES (...)")
pedido_id = cursor.lastrowid
for item in itens:
    cursor.execute("INSERT INTO itens_pedido ...")
    cursor.execute("UPDATE produtos SET estoque = estoque - ...")
db.commit()
```
Description: `criar_pedido` insere o pedido, os itens e atualiza o estoque em várias instruções sem `BEGIN`/`ROLLBACK` explícitos; combinado com a conexão global compartilhada (F08), uma falha no meio do laço deixa a transação pendente, que pode ser commitada por outra requisição não relacionada.
Impact: Pedidos parcialmente gravados (itens sem estoque debitado, ou vice-versa) em caso de erro.
Recommendation: Envolver as escritas em uma transação explícita (`with db:` ou `BEGIN`/`COMMIT`/`ROLLBACK`) dentro de um helper de transação no `database.py`, usado por um `pedido_service.py`.

### F13 [MEDIUM] Consultas N+1
File: models.py:187-199, models.py:219-231
Catalog: AP-13 | Fix: PB-09
Evidence:
```python
for item in itens:
    cursor3 = db.cursor()
    cursor3.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))
```
Description: `get_pedidos_usuario` e `get_todos_pedidos` fazem uma query de itens por pedido e, dentro dela, uma query de produto por item — duas camadas de N+1.
Impact: Tempo de resposta cresce linearmente com o número de pedidos/itens; piora sensivelmente em produção.
Recommendation: Substituir por um único `JOIN` entre `pedidos`, `itens_pedido` e `produtos`, agrupando em Python.

### F14 [MEDIUM] Lógica duplicada
File: controllers.py:28-50, controllers.py:72-90, models.py:9-21, models.py:31-40, models.py:304-313, models.py:171-201, models.py:203-233
Catalog: AP-14 | Fix: PB-13, PB-08
Evidence:
```python
if "nome" not in dados: ...
if "preco" not in dados: ...
if "estoque" not in dados: ...
```
Description: A validação de produto é copiada entre `criar_produto` e `atualizar_produto`; o mapeamento `row → dict` de produto é repetido em três funções de `models.py`; `get_pedidos_usuario` e `get_todos_pedidos` são praticamente idênticas, diferindo só pelo `WHERE usuario_id`.
Impact: Regras divergem silenciosamente (já ocorre: `atualizar_produto` não valida categoria, ver F15).
Recommendation: Extrair um validador de produto reutilizável, um serializador único `_produto_to_dict(row)` e reaproveitar `get_todos_pedidos` filtrando opcionalmente por `usuario_id`.

### F15 [MEDIUM] Validação de entrada ausente/inconsistente
File: controllers.py:64-96, controllers.py:188-206
Catalog: AP-15 | Fix: PB-13
Evidence:
```python
def atualizar_produto(id):
    ...
    # sem validação de `categoria` (presente em criar_produto, linha 52-54)
```
Description: `atualizar_produto` não valida `categoria` contra a lista de categorias válidas, ao contrário de `criar_produto`; `criar_pedido` não valida a presença de `produto_id`/`quantidade` em cada item antes de usá-los (`item["produto_id"]` pode lançar `KeyError`).
Impact: Dados inconsistentes podem ser persistidos via update; payloads malformados em pedidos geram 500 em vez de 400.
Recommendation: Reaproveitar o mesmo validador de produto (F14) em create e update; validar cada item do pedido antes de processar.

### F16 [MEDIUM] Exceções engolidas / detalhes internos expostos
File: controllers.py:10-12, controllers.py:21-22, controllers.py:60-62, controllers.py:95-96, controllers.py:108-109, controllers.py:125-126, controllers.py:133-134, controllers.py:143-144, controllers.py:164-165, controllers.py:185-186, controllers.py:218-220, controllers.py:226-227, controllers.py:234-235, controllers.py:254-255, controllers.py:261-262, controllers.py:291-292
Catalog: AP-16 | Fix: PB-11
Evidence:
```python
except Exception as e:
    return jsonify({"erro": str(e)}), 500
```
Description: As 16 funções de `controllers.py` repetem o mesmo `try/except Exception` que devolve `str(e)` diretamente ao cliente; não existe handler de erro centralizado.
Impact: Mensagens internas (nomes de tabelas/colunas, tracebacks parciais) podem ser expostas; formato de erro é mantido só por convenção manual em cada função.
Recommendation: Registrar um error handler centralizado (`middlewares/error_handler.py`) com erros tipados (`NotFoundError`, `ValidationError`), removendo o `try/except` repetido dos controllers.

### F17 [MEDIUM] Falta de integridade referencial no delete
File: models.py:65-70
Catalog: AP-17 | Fix: PB-16
Evidence:
```python
def deletar_produto(id):
    cursor.execute("DELETE FROM produtos WHERE id = " + str(id))
```
Description: Produtos podem ser excluídos mesmo com `itens_pedido` referenciando o `produto_id`; `database.py` não habilita `PRAGMA foreign_keys = ON` nem define `FOREIGN KEY` nas tabelas.
Impact: Relatórios e consultas de pedidos passam a exibir "Desconhecido" (já tratado defensivamente em `models.py:196`) em vez de impedir a exclusão ou alertar o chamador.
Recommendation: Adicionar `FOREIGN KEY` + `PRAGMA foreign_keys = ON` no schema e bloquear a exclusão de produtos referenciados (ou soft-delete via `ativo`, campo que já existe na tabela mas não é usado).

### F18 [MEDIUM] Responsabilidade mal posicionada
File: app.py:47-78
Catalog: AP-19 | Fix: PB-05
Evidence:
```python
@app.route("/admin/reset-db", methods=["POST"])
def reset_database():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM itens_pedido")
```
Description: Diferente de todas as outras rotas (registradas via `controllers.*`), `/admin/reset-db` e `/admin/query` têm a lógica escrita diretamente no entry point, acessando o banco sem passar por nenhuma camada.
Impact: Estrutura inconsistente — quem lê `app.py` esperando só registro de rotas encontra acesso a dados e regras ali.
Recommendation: Mover para `controllers/admin_controller.py`, seguindo o mesmo padrão das demais rotas.

### F19 [LOW] Números/strings mágicas
File: controllers.py:52, controllers.py:242, models.py:256-262
Catalog: AP-20 | Fix: PB-15
Evidence:
```python
if faturamento > 10000:
    desconto = faturamento * 0.1
```
Description: Lista de categorias válidas, lista de status de pedido e faixas/taxas de desconto estão embutidas diretamente no código.
Impact: Mudar uma regra de negócio exige editar código-fonte em vez de uma constante central.
Recommendation: Mover para `config/settings.py` como constantes (`CATEGORIAS_VALIDAS`, `STATUS_PEDIDO`, `FAIXAS_DESCONTO`).

### F20 [LOW] Import não utilizado
File: models.py:2
Catalog: AP-22 | Fix: PB-15
Evidence:
```python
import sqlite3
```
Description: `sqlite3` é importado em `models.py` mas nunca referenciado — todo acesso passa por `database.get_db()`.
Impact: Nenhum funcional; ruído de leitura.
Recommendation: Remover o import ao mover o conteúdo para os novos módulos de model.

### F21 [LOW] `print` como logging
File: app.py:56, app.py:83-86, controllers.py:8, controllers.py:11, controllers.py:57, controllers.py:61, controllers.py:106, controllers.py:161, controllers.py:179, controllers.py:182, controllers.py:208-210, controllers.py:219, controllers.py:248, controllers.py:250
Catalog: AP-23 | Fix: PB-15
Evidence:
```python
print("ERRO: " + str(e))
```
Description: Toda a aplicação usa `print` para eventos e erros, sem níveis nem estrutura.
Impact: Impossível filtrar/rotear logs em produção; erros e "notificações" simuladas se misturam no stdout.
Recommendation: Usar `logging.getLogger(__name__)` configurado no `create_app()`.

### F22 [LOW] Construções não idiomáticas (parâmetro `id` sombreia builtin)
File: controllers.py:14, controllers.py:64, controllers.py:98, controllers.py:136, models.py:24, models.py:54, models.py:65, models.py:89
Catalog: AP-24 | Fix: PB-15
Evidence:
```python
def buscar_produto(id):
```
Description: Vários parâmetros de função se chamam `id`, sombreando o builtin `id()` do Python.
Impact: Puramente estilístico; risco baixo de confusão em manutenção futura.
Recommendation: Renomear para `produto_id`/`usuario_id`/`pedido_id` conforme o domínio.

## Deprecated APIs
Nenhuma API deprecated encontrada (verificado `utcnow`, `.query.get(`, `before_first_request`, `distutils`/`imp`, adaptadores de datetime do sqlite3 — nenhum uso presente).

## Proposed Target Architecture
Estratégia (maturidade Monolítica, guidelines §5): reestruturar o monólito completo em `src/`, dividindo por domínio e deletando os arquivos antigos.

```
code-smells-project/
├── app.py                      # entry point fino: from src.app import create_app
├── requirements.txt
├── .env.example                 # SECRET_KEY, ADMIN_TOKEN, DB_PATH, DEBUG, CORS_ORIGINS
└── src/
    ├── __init__.py
    ├── app.py                   # create_app(): composition root, registra blueprints e middlewares
    ├── config/
    │   └── settings.py          # env vars + constantes (categorias, status, faixas de desconto)
    ├── database.py              # get_db() por request via flask.g, teardown, init_db(), seed, transaction()
    ├── models/
    │   ├── produto_model.py
    │   ├── usuario_model.py
    │   └── pedido_model.py
    ├── controllers/
    │   ├── produto_controller.py
    │   ├── usuario_controller.py
    │   ├── pedido_controller.py
    │   ├── relatorio_controller.py
    │   └── admin_controller.py  # reset-db / query, protegidos por X-Admin-Token
    ├── views/
    │   ├── produto_routes.py
    │   ├── usuario_routes.py
    │   ├── pedido_routes.py
    │   ├── relatorio_routes.py
    │   └── admin_routes.py
    ├── services/
    │   └── notification_service.py  # substitui os prints de "envio" em criar_pedido/atualizar_status_pedido
    └── middlewares/
        ├── error_handler.py     # erros tipados -> respostas padronizadas
        └── admin_auth.py        # guard X-Admin-Token
```

================================
Total: 22 findings
================================
