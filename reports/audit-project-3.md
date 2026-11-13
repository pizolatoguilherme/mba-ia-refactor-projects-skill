================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python 3.14 + Flask 3.0.0 (Flask-SQLAlchemy 3.1.1, SQLite)
Files:   15 analyzed | ~1158 lines of code
Architecture: Camadas parciais — pastas `models/`, `routes/`, `services/`, `utils/` existem, mas regras de negócio e serialização estão duplicadas dentro das rotas, `services/notification_service.py` não é usado por nenhuma rota e `utils/helpers.py` tem funções/constantes mortas.
Date:    2026-11-13

## Summary
CRITICAL: 3 | HIGH: 4 | MEDIUM: 7 | LOW: 4

| ID | Severity | Anti-pattern | Location |
|----|----------|--------------|----------|
| F01 | CRITICAL | Credenciais hardcoded | app.py:13 (+2) |
| F02 | CRITICAL | Hash de senha fraco (MD5) | models/user.py:29 (+1) |
| F03 | CRITICAL | Exposição de dados sensíveis | models/user.py:21 (+3) |
| F04 | HIGH | Lógica de negócio nas rotas (fat controller) | routes/task_routes.py:16-59 (+3) |
| F05 | HIGH | Efeitos colaterais no import / acoplamento forte | app.py:30-31 (+1) |
| F06 | HIGH | Defaults inseguros de runtime | app.py:34 (+1) |
| F07 | HIGH | Autenticação/autorização quebrada | routes/user_routes.py:52 (+3) |
| F08 | MEDIUM | Consultas N+1 e agregados repetidos | routes/task_routes.py:41-56 (+2) |
| F09 | MEDIUM | Lógica duplicada (overdue, serialização) | routes/task_routes.py:30-39 (+5) |
| F10 | MEDIUM | Validação de entrada ausente/inconsistente | routes/report_routes.py:196-202 (+1) |
| F11 | MEDIUM | Exceções engolidas (`except:` genérico) | routes/task_routes.py:62 (+8) |
| F12 | MEDIUM | Integridade referencial ausente no delete | routes/report_routes.py:211-223 (+0) |
| F13 | MEDIUM | APIs deprecated (`utcnow`, `Query.get`) | models/task.py:15 (+ ver tabela) |
| F14 | MEDIUM | Responsabilidade mal posicionada / camada morta | routes/report_routes.py:157-223 (+2) |
| F15 | LOW | Magic numbers/strings | routes/task_routes.py:110 (+4) |
| F16 | LOW | Imports não usados / código morto | routes/task_routes.py:7 (+4) |
| F17 | LOW | `print` como logging | routes/task_routes.py:149 (+8) |
| F18 | LOW | Construções não idiomáticas | routes/task_routes.py:141 (+4) |

## Findings

### F01 [CRITICAL] Credenciais hardcoded
File: app.py:13, services/notification_service.py:7-10
Catalog: AP-01 | Fix: PB-01
Evidence:
```python
app.config['SECRET_KEY'] = 'super-secret-key-123'
# services/notification_service.py:9-10
self.email_user = 'taskmanager@gmail.com'
self.email_password = 'senha123'
```
Description: A `SECRET_KEY` do Flask e as credenciais SMTP estão escritas em texto plano no código-fonte.
Impact: Qualquer pessoa com acesso ao repositório (ou a uma imagem buildada) obtém a secret key usada para assinar sessões/tokens e a senha de uma conta de e-mail real; rotacionar exige alterar código e novo deploy.
Recommendation: Ler ambos de variáveis de ambiente (`os.environ['SECRET_KEY']`, `SMTP_USER`, `SMTP_PASSWORD`) carregadas via `python-dotenv`, documentadas em `.env.example`, sem default de produção embutido.

### F02 [CRITICAL] Hash de senha fraco (MD5)
File: models/user.py:29, models/user.py:32
Catalog: AP-04 | Fix: PB-03
Evidence:
```python
self.password = hashlib.md5(pwd.encode()).hexdigest()
```
Description: Senhas são hasheadas com MD5 sem salt, um algoritmo quebrado e rápido de forçar por brute-force/rainbow table.
Impact: Um leak do banco `tasks.db` expõe todas as senhas de usuários em minutos, permitindo reuso em outros sistemas (credential stuffing).
Recommendation: Usar `werkzeug.security.generate_password_hash`/`check_password_hash` (já disponível via Flask) ou `bcrypt`, mantendo a mesma assinatura de `set_password`/`check_password`.

### F03 [CRITICAL] Exposição de dados sensíveis
File: models/user.py:21, routes/user_routes.py:86, routes/user_routes.py:129, routes/user_routes.py:209
Catalog: AP-05 | Fix: PB-03, PB-15
Evidence:
```python
# models/user.py:16-25
def to_dict(self):
    return {
        'id': self.id, 'name': self.name, 'email': self.email,
        'password': self.password, 'role': self.role, ...
    }
```
Description: `User.to_dict()` inclui o hash da senha, e as respostas de criação (`routes/user_routes.py:86`), atualização (`routes/user_routes.py:129`) e login (`routes/user_routes.py:209`) devolvem esse dicionário completo ao cliente.
Impact: O hash da senha de qualquer usuário é exposto em respostas HTTP comuns, facilitando ataques offline mesmo sem acesso direto ao banco.
Recommendation: Remover `password` de `to_dict()` (ou criar `to_dict(include_password=False)` como padrão) e nunca serializar o campo de senha nas respostas das rotas.

### F04 [HIGH] Lógica de negócio nas rotas (fat controller)
File: routes/task_routes.py:16-59, routes/task_routes.py:273-299, routes/user_routes.py:160-183, routes/report_routes.py:12-165
Catalog: AP-07 | Fix: PB-08
Evidence:
```python
# routes/task_routes.py:30-39
if t.due_date:
    if t.due_date < datetime.utcnow():
        if t.status != 'done' and t.status != 'cancelled':
            task_data['overdue'] = True
        ...
```
Description: Cálculo de atraso, serialização manual campo-a-campo e agregações de relatório (contagens por status/prioridade, produtividade por usuário) estão implementados diretamente nas rotas, em vez de delegar a `Task.to_dict()`/`Task.is_overdue()` (já existentes em `models/task.py:23-60`) ou a uma camada de serviço.
Impact: Regras de negócio não são testáveis sem subir o Flask; qualquer mudança na regra de "atrasado" precisa ser replicada em 5+ lugares, com risco de divergência.
Recommendation: Mover cálculo de overdue e serialização para os métodos do model (`to_dict`, `is_overdue`); extrair agregações de `reports/*` para uma camada de serviço (`services/report_service.py`) chamada pelos controllers.

### F05 [HIGH] Efeitos colaterais no import / acoplamento forte
File: app.py:30-31, seed.py:2
Catalog: AP-09 | Fix: PB-07
Evidence:
```python
with app.app_context():
    db.create_all()
```
Description: `db.create_all()` roda no nível de módulo de `app.py`, fora de `if __name__ == '__main__'`; como `seed.py:2` faz `from app import app, db`, o schema é criado (e o servidor fica configurado) como efeito colateral de um simples import, sem factory function.
Impact: Impossível importar `app.py` em testes sem acionar criação de schema/side effects; ordem de boot é implícita e frágil.
Recommendation: Extrair uma função `create_app()` que registra blueprints e chama `db.create_all()` apenas quando explicitamente invocada (padrão app factory do Flask).

### F06 [HIGH] Defaults inseguros de runtime
File: app.py:15, app.py:34
Catalog: AP-10 | Fix: PB-01
Evidence:
```python
CORS(app)
...
app.run(debug=True, host='0.0.0.0', port=5000)
```
Description: `debug=True` habilita o debugger interativo do Werkzeug (execução remota de código) exposto em `0.0.0.0`; `CORS(app)` sem restrição libera qualquer origem a chamar a API.
Impact: Em produção, qualquer erro não tratado pode abrir um console de depuração remoto; a API fica acessível via CORS para qualquer site.
Recommendation: Ler `DEBUG` e `CORS_ORIGINS` de variáveis de ambiente, com `debug=False` e lista explícita de origens como padrão.

### F07 [HIGH] Autenticação/autorização quebrada
File: routes/user_routes.py:52, routes/user_routes.py:71-72, routes/user_routes.py:185-211
Catalog: AP-11 | Fix: PB-04
Evidence:
```python
# routes/user_routes.py:52,71-72
role = data.get('role', 'user')
...
if role not in ['user', 'admin', 'manager']:
```
Description: O cliente escolhe a própria `role` no cadastro (`POST /users`), podendo se registrar como `admin`; `POST /login` devolve um token falso (`'fake-jwt-token-' + id`) e o dicionário completo do usuário, incluindo o hash da senha (ligado a F03).
Impact: Qualquer visitante não autenticado pode se tornar administrador chamando `/users` com `"role": "admin"`; o "token" não tem nenhuma validade/expiração, não protegendo nenhuma rota.
Recommendation: Ignorar `role` vindo do cliente no cadastro público (default fixo `user`, promoção só por rota administrativa autenticada); emitir um JWT real (`PyJWT`) e usar um decorator de autenticação nas rotas sensíveis listadas em `mvc-guidelines.md`.

### F08 [MEDIUM] Consultas N+1 e agregados repetidos
File: routes/task_routes.py:41-56, routes/user_routes.py:22, routes/report_routes.py:19-28, routes/report_routes.py:53-68
Catalog: AP-13 | Fix: PB-09
Evidence:
```python
# routes/task_routes.py:41-56 (dentro de um for sobre todas as tasks)
user = User.query.get(t.user_id)
...
cat = Category.query.get(t.category_id)
```
Description: `get_tasks` faz duas consultas extras por task retornada; `get_users` acessa `len(u.tasks)` (lazy load) por usuário; `report_routes.py` roda 5 `COUNT` separados por status + 5 por prioridade (linhas 19-28) e uma query de tasks por usuário dentro do loop de produtividade (linha 56).
Impact: O número de queries cresce linearmente com o volume de dados, degradando a latência dos endpoints de listagem e relatório.
Recommendation: Usar `join`/`selectinload` para trazer `user`/`category` junto da consulta principal, e `GROUP BY status`/`GROUP BY priority` para os contadores agregados.

### F09 [MEDIUM] Lógica duplicada (overdue, serialização)
File: routes/task_routes.py:30-39, routes/task_routes.py:71-80, routes/task_routes.py:283-287, routes/user_routes.py:171-180, routes/report_routes.py:34-37, routes/report_routes.py:132-135
Catalog: AP-14 | Fix: PB-13, PB-08
Evidence:
```python
# repetido em 6 lugares com a mesma estrutura
if t.due_date < datetime.utcnow():
    if t.status != 'done' and t.status != 'cancelled':
        ...
```
Description: A regra "task está atrasada" é recalculada manualmente em seis pontos diferentes, mesmo existindo `Task.is_overdue()` em `models/task.py:50-60` (nunca chamado); a serialização campo-a-campo de `Task` também é repetida em vez de reusar `Task.to_dict()`.
Impact: Qualquer ajuste na regra de negócio (ex.: considerar fuso horário) precisa ser replicado em 6 lugares, com alto risco de divergência silenciosa.
Recommendation: Substituir todas as ocorrências por chamadas a `task.is_overdue()` e `task.to_dict()`.

### F10 [MEDIUM] Validação de entrada ausente/inconsistente
File: routes/report_routes.py:196-202, routes/task_routes.py:113, routes/task_routes.py:182
Catalog: AP-15 | Fix: PB-13
Evidence:
```python
# routes/report_routes.py:196-202
data = request.get_json()
if 'name' in data:
```
Description: `update_category` nunca verifica se `request.get_json()` retornou `None` antes de usar `'name' in data` (corpo vazio quebra com erro não tratado); `create_task`/`update_task` comparam `priority < 1` sem checar o tipo, lançando `TypeError` se o cliente enviar uma string.
Impact: Entradas inválidas resultam em erro 500 não controlado (e, com `debug=True` de F06, expõem stack trace) em vez de uma resposta 400 clara.
Recommendation: Replicar a checagem `if not data: return 400` já usada em `create_category`, e validar `isinstance(priority, int)` antes da comparação.

### F11 [MEDIUM] Exceções engolidas (`except:` genérico)
File: routes/task_routes.py:62, routes/task_routes.py:137, routes/task_routes.py:204, routes/task_routes.py:236, routes/user_routes.py:130, routes/user_routes.py:149, routes/report_routes.py:186, routes/report_routes.py:207, routes/report_routes.py:221, utils/helpers.py:46, utils/helpers.py:49, utils/helpers.py:88
Catalog: AP-16 | Fix: PB-11
Evidence:
```python
except:
    return jsonify({'error': 'Erro interno'}), 500
```
Description: Doze blocos `except:` genéricos capturam qualquer exceção (incluindo erros de programação) sem logar a causa real, cada rota formatando a resposta de erro à sua maneira.
Impact: Bugs reais ficam escondidos (nenhum rastro no log), dificultando diagnóstico; formato de erro inconsistente entre endpoints.
Recommendation: Centralizar tratamento de erros em um `@app.errorhandler(Exception)`, capturando exceções específicas nas rotas apenas quando há uma recuperação real a fazer.

### F12 [MEDIUM] Integridade referencial ausente no delete
File: routes/report_routes.py:211-223
Catalog: AP-17 | Fix: PB-16
Evidence:
```python
@report_bp.route('/categories/<int:cat_id>', methods=['DELETE'])
def delete_category(cat_id):
    cat = Category.query.get(cat_id)
    ...
    db.session.delete(cat)
    db.session.commit()
```
Description: Ao excluir uma categoria, as tasks que a referenciam (`task.category_id`) não são atualizadas nem desvinculadas — diferente de `delete_user` (`routes/user_routes.py:140-142`), que explicitamente apaga as tasks do usuário antes de excluí-lo.
Impact: Tasks passam a apontar para um `category_id` inexistente; relatórios e buscas por categoria ficam inconsistentes (dados órfãos).
Recommendation: Antes do delete, definir `category_id = None` nas tasks associadas (ou bloquear a exclusão se houver tasks vinculadas), replicando o padrão já usado para usuários.

### F13 [MEDIUM] APIs deprecated
File: models/task.py:15-16, routes/task_routes.py:31
Catalog: AP-18 | Fix: PB-14
Evidence:
```python
created_at = db.Column(db.DateTime, default=datetime.utcnow)
```
Description: Ver tabela "Deprecated APIs" abaixo — `datetime.utcnow()` (deprecated desde Python 3.12, runtime local é 3.14) e `Model.query.get(id)` (API legada do Flask-SQLAlchemy 3.x/SQLAlchemy 2.x) aparecem em todos os models e rotas.
Impact: `datetime.utcnow()` já emite `DeprecationWarning` e pode ser removido em versões futuras do Python; `Query.get` é mantido mas pertence ao estilo legado substituído pela Session API no SQLAlchemy 2.x.
Recommendation: Trocar por `datetime.now(timezone.utc)` e `db.session.get(Model, id)` em todas as ocorrências listadas na tabela.

### F14 [MEDIUM] Responsabilidade mal posicionada / camada morta
File: routes/report_routes.py:157-223, services/notification_service.py:1-48, utils/helpers.py:19-116
Catalog: AP-19 | Fix: PB-05
Evidence:
```python
# routes/report_routes.py:157
@report_bp.route('/categories', methods=['GET'])
```
Description: O CRUD de `categories` vive dentro de `report_routes.py` (que deveria conter apenas relatórios), não em um módulo próprio; `services/notification_service.py` define uma classe completa de notificações que nenhuma rota importa; `utils/helpers.py:19-116` define `process_task_data`, `validate_email`, `sanitize_string`, `generate_id`, `log_action`, `is_valid_color` e as constantes `VALID_STATUSES`/`VALID_ROLES`/etc., todas sem nenhum import fora do próprio arquivo — as rotas reimplementam a mesma lógica inline em vez de usá-las.
Impact: A estrutura em camadas é enganosa: parece organizada, mas a camada de serviço é decorativa e a lógica real está duplicada nas rotas (reforça F04/F09).
Recommendation: Mover `categories` para `routes/category_routes.py`; remover `notification_service.py` se não houver plano de uso real, ou conectá-lo a `create_task`/`update_task`; substituir as validações manuais nas rotas pelas funções de `utils/helpers.py` (ou remover o arquivo morto).

### F15 [LOW] Magic numbers/strings
File: routes/task_routes.py:110, routes/task_routes.py:177, routes/user_routes.py:71, routes/user_routes.py:120, models/task.py:39
Catalog: AP-20 | Fix: PB-15
Evidence:
```python
if status not in ['pending', 'in_progress', 'done', 'cancelled']:
```
Description: As listas de status válidos, roles válidas e faixa de prioridade (1-5) são literais repetidos em vários arquivos, embora `utils/helpers.py:110-116` já defina `VALID_STATUSES`/`VALID_ROLES`/etc. (não usadas, ver F14).
Impact: Adicionar um novo status/role exige editar vários arquivos manualmente; fácil esquecer um local.
Recommendation: Importar as constantes de `utils/helpers.py` (ou movê-las para os models) em vez de repetir os literais.

### F16 [LOW] Imports não usados / código morto
File: routes/task_routes.py:7, routes/user_routes.py:6, routes/report_routes.py:7-8, app.py:7, utils/helpers.py:2-7
Catalog: AP-22 | Fix: PB-15
Evidence:
```python
import json, os, sys, time
```
Description: `json, os, sys, time` em `routes/task_routes.py:7` não são referenciados no arquivo; `hashlib, json` em `routes/user_routes.py:6` idem; `routes/report_routes.py:7` importa `format_date`/`calculate_percentage` que nunca são chamadas, e `json` (linha 8) também não é usado; `app.py:7` importa `os, sys, json` sem uso; `utils/helpers.py:2-7` importa `os, sys, math, json, hashlib` sem uso no arquivo.
Impact: Ruído que dificulta entender as dependências reais de cada módulo.
Recommendation: Remover os imports não utilizados.

### F17 [LOW] `print` como logging
File: routes/task_routes.py:149, routes/task_routes.py:153, routes/task_routes.py:219, routes/task_routes.py:234, routes/user_routes.py:83, routes/user_routes.py:89, routes/user_routes.py:147, services/notification_service.py:21, services/notification_service.py:24, utils/helpers.py:39, utils/helpers.py:41
Catalog: AP-23 | Fix: PB-15
Evidence:
```python
print(f"Task criada: {task.id} - {task.title}")
```
Description: Toda a aplicação usa `print()` para registrar eventos, sem níveis, formato estruturado ou destino configurável.
Impact: Impossível filtrar por severidade ou redirecionar logs em produção; saída mistura com qualquer coisa escrita em stdout.
Recommendation: Usar o módulo `logging` do Python (`app.logger.info/error`) configurado uma vez no bootstrap da aplicação.

### F18 [LOW] Construções não idiomáticas
File: routes/task_routes.py:141, routes/task_routes.py:210, utils/helpers.py:103, models/task.py:38-60, models/user.py:34-38
Catalog: AP-24 | Fix: PB-15
Evidence:
```python
if type(tags) == list:
    ...
# models/user.py:34-38
def is_admin(self):
    if self.role == 'admin':
        return True
    else:
        return False
```
Description: `type(x) == list` em vez de `isinstance(x, list)`; vários métodos (`is_admin`, `validate_status`, `validate_priority`, `is_overdue`) usam `if cond: return True else: return False` ou pirâmides de `if` aninhados em vez de retornar a expressão booleana diretamente.
Impact: Código mais verboso e propenso a bugs ao estender as condições.
Recommendation: Usar `isinstance()` e retornar a expressão booleana diretamente (`return self.role == 'admin'`).

## Deprecated APIs
| File:line | Deprecated usage | Modern replacement |
|-----------|------------------|--------------------|
| models/category.py:11 | `datetime.utcnow` | `datetime.now(timezone.utc)` |
| models/task.py:15 | `datetime.utcnow` | `datetime.now(timezone.utc)` |
| models/task.py:16 | `datetime.utcnow` (x2) | `datetime.now(timezone.utc)` |
| models/task.py:52 | `datetime.utcnow()` | `datetime.now(timezone.utc)` |
| models/user.py:14 | `datetime.utcnow` | `datetime.now(timezone.utc)` |
| routes/task_routes.py:31,72,215,285 | `datetime.utcnow()` | `datetime.now(timezone.utc)` |
| routes/user_routes.py:172 | `datetime.utcnow()` | `datetime.now(timezone.utc)` |
| routes/report_routes.py:35,42,45,71,133 | `datetime.utcnow()` | `datetime.now(timezone.utc)` |
| services/notification_service.py:35 | `datetime.utcnow()` | `datetime.now(timezone.utc)` |
| utils/helpers.py:38 | `datetime.utcnow()` | `datetime.now(timezone.utc)` |
| routes/task_routes.py:67,117,122,158,188,195,227 | `Model.query.get(id)` | `db.session.get(Model, id)` |
| routes/user_routes.py:29,94,136,155 | `Model.query.get(id)` | `db.session.get(Model, id)` |
| routes/report_routes.py:105,192,213 | `Model.query.get(id)` | `db.session.get(Model, id)` |
| routes/task_routes.py:42,51 | `Model.query.get(id)` | `db.session.get(Model, id)` |

## Proposed Target Architecture
```
task-manager-api/
├── app.py                   # cria app via create_app(), registra blueprints, sem side effects no import
├── .env.example
├── config.py                 # lê SECRET_KEY, SQLALCHEMY_DATABASE_URI, CORS_ORIGINS, DEBUG, SMTP_* do ambiente
├── database.py                # db = SQLAlchemy() (mantido)
├── models/
│   ├── task.py, user.py, category.py   # mantêm to_dict()/is_overdue(); to_dict() de User sem password
├── controllers/               # NOVO — orquestram request/response, chamam services/models, sem SQL/regra
│   ├── task_controller.py, user_controller.py, category_controller.py, report_controller.py
├── routes/
│   ├── task_routes.py, user_routes.py, category_routes.py (NOVO), report_routes.py
│   └── __init__.py            # cada blueprint só mapeia verbo+path → controller
├── services/
│   ├── task_service.py (NOVO) # overdue, stats, N+1 → GROUP BY/join
│   ├── report_service.py (NOVO)
│   ├── auth_service.py (NOVO) # hashing seguro, emissão de token real
│   └── notification_service.py # credenciais via env; conectado ao fluxo de criação de task ou removido
├── utils/
│   └── helpers.py              # mantém só o que for de fato usado pelos controllers/services
├── errors/
│   └── handlers.py (NOVO)      # @app.errorhandler central, sem `except:` genérico nas rotas
└── seed.py
```
Estratégia: **completar camadas parciais** — preservar `models/`, `routes/`, `services/`, `utils/` já existentes; introduzir `controllers/` (hoje ausente, com toda a lógica vazando para as rotas) e `errors/`; mover a lógica de overdue/serialização/relatórios dos handlers para models/services; realinhar `categories` para seu próprio módulo; conectar ou remover a camada morta (`notification_service`, funções de `utils/helpers.py`); eliminar credenciais hardcoded e hash MD5 (F01-F03) sem alterar rotas, métodos HTTP, status codes ou formato de resposta (exceto remoção do campo `password` de `User.to_dict()`, que é mudança de segurança intencional).

================================
Total: 18 findings
================================
