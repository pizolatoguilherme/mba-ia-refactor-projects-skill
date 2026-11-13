================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python 3.14 + Flask 3.0.0
Files:   14 analyzed | ~1164 lines of code
Architecture: Camadas parciais
Date:    2026-11-13

## Summary
CRITICAL: 3 | HIGH: 4 | MEDIUM: 7 | LOW: 4

| ID | Severity | Anti-pattern | Location |
|----|----------|--------------|----------|
| F01 | CRITICAL | Credenciais hardcoded | app.py:13 (+1) |
| F02 | CRITICAL | Hashing de senha fraco (MD5) | models/user.py:29 (+1) |
| F03 | CRITICAL | Exposição de dados sensíveis | models/user.py:16-25 (+3) |
| F04 | HIGH | Lógica de negócio nas rotas (fat controller) | routes/task_routes.py:30-39 (+6) |
| F05 | HIGH | Falha de autenticação / escalonamento de privilégio | routes/user_routes.py:52 (+1) |
| F06 | HIGH | Defaults de runtime inseguros | app.py:9-15 (+1) |
| F07 | HIGH | Acoplamento forte / efeitos colaterais no import | app.py:30-31 |
| F08 | MEDIUM | Consultas N+1 e agregações repetidas | routes/task_routes.py:41-56 (+3) |
| F09 | MEDIUM | Lógica duplicada | models/task.py:50-60 (+4) |
| F10 | MEDIUM | Validação de entrada ausente/inconsistente | routes/task_routes.py:113 (+2) |
| F11 | MEDIUM | Exceções engolidas / erros internos vazados | routes/task_routes.py:62 (+8) |
| F12 | MEDIUM | Integridade referencial ausente no delete | routes/report_routes.py:211-223 |
| F13 | MEDIUM | Responsabilidade mal posicionada / camada não usada | services/notification_service.py:1-48 (+3) |
| F14 | MEDIUM | APIs deprecated (`datetime.utcnow`, `Query.get`) | models/task.py:15-16 (+20) |
| F15 | LOW | Imports não usados / código morto | app.py:7 (+4) |
| F16 | LOW | `print` como logging | routes/task_routes.py:149 (+8) |
| F17 | LOW | Construções não idiomáticas | models/task.py:38-43 (+3) |
| F18 | LOW | Nomenclatura pouco descritiva | routes/task_routes.py:16 (+2) |

## Findings

### F01 [CRITICAL] Credenciais hardcoded
File: app.py:13, services/notification_service.py:7-10
Catalog: AP-01 | Fix: PB-01
Evidence:
```python
app.config['SECRET_KEY'] = 'super-secret-key-123'
...
self.email_password = 'senha123'
```
Description: A chave de sessão do Flask e as credenciais SMTP estão escritas como literais no código-fonte.
Impact: Qualquer pessoa com acesso ao repositório (ou a uma imagem buildada) obtém a chave de sessão e a senha do e-mail; rotacionar exige novo deploy.
Recommendation: Ler `SECRET_KEY` e credenciais SMTP de variáveis de ambiente (`os.environ.get`), com fallback aleatório (`secrets.token_hex`) e aviso de log quando ausente, dentro de `config/settings.py`.

### F02 [CRITICAL] Hashing de senha fraco (MD5)
File: models/user.py:29, models/user.py:32
Catalog: AP-04 | Fix: PB-03
Evidence:
```python
self.password = hashlib.md5(pwd.encode()).hexdigest()
```
Description: Senhas são armazenadas com hash MD5 simples, sem salt e com algoritmo quebrado para uso criptográfico.
Impact: Um leak do banco permite quebrar todas as senhas quase instantaneamente (MD5 é trivial de forçar/rainbow-table).
Recommendation: Usar `werkzeug.security.generate_password_hash` / `check_password_hash` (já vem com o Flask) nos métodos `set_password`/`check_password` do model.

### F03 [CRITICAL] Exposição de dados sensíveis
File: models/user.py:16-25, routes/user_routes.py:33, routes/user_routes.py:85-86, routes/user_routes.py:129, routes/user_routes.py:209
Catalog: AP-05 | Fix: PB-03, PB-15
Evidence:
```python
def to_dict(self):
    return {... 'password': self.password, ...}
```
Description: `User.to_dict()` inclui o hash da senha, e as rotas de criação, consulta, atualização e login retornam esse dict diretamente ao cliente.
Impact: O hash da senha (ainda que fosse forte) fica exposto em toda resposta HTTP relacionada a usuário, facilitando ataques offline.
Recommendation: Remover `password` da serialização padrão do model; se necessário um campo interno, usar um `to_dict(include_sensitive=False)` e nunca expor o hash nas rotas.

### F04 [HIGH] Lógica de negócio nas rotas (fat controller)
File: routes/task_routes.py:30-39, routes/task_routes.py:71-80, routes/task_routes.py:92-114, routes/task_routes.py:166-213, routes/task_routes.py:283-287, routes/user_routes.py:171-180, routes/report_routes.py:34-43, routes/report_routes.py:132-135
Catalog: AP-07 | Fix: PB-08
Evidence:
```python
if t.due_date:
    if t.due_date < datetime.utcnow():
        if t.status != 'done' and t.status != 'cancelled':
            task_data['overdue'] = True
```
Description: Cálculo de "atraso", validação de título/status/prioridade e agregações de relatório estão implementados diretamente dentro dos handlers de rota, repetidos em várias funções, em vez de delegados a um controller/model/service.
Impact: Regras não são testáveis sem subir o Flask; qualquer mudança de regra precisa ser replicada em múltiplos arquivos, já divergente (ex.: `Task.is_overdue()` existe no model mas nenhuma rota o usa).
Recommendation: Criar `controllers/` que chamam `Task.is_overdue()` e um validador compartilhado; rotas passam a apenas receber request, chamar o controller e devolver a resposta.

### F05 [HIGH] Falha de autenticação / escalonamento de privilégio
File: routes/user_routes.py:52, routes/user_routes.py:71-72, routes/user_routes.py:119-122, routes/user_routes.py:210
Catalog: AP-11 | Fix: PB-04
Evidence:
```python
role = data.get('role', 'user')
...
if role not in ['user', 'admin', 'manager']:
    ...
user.role = role
...
'token': 'fake-jwt-token-' + str(user.id)
```
Description: O cliente escolhe livremente a própria `role` no cadastro/atualização (incluindo `admin`) e o login devolve um token falso, sem assinatura nem expiração.
Impact: Qualquer usuário anônimo pode se autopromover a administrador e obter um "token" previsível, permitindo escalonamento de privilégio.
Recommendation: Ignorar `role` vindo do cliente no `POST /users` (sempre `'user'`), restringir mudança de `role` a um fluxo administrativo, e documentar/recomendar um JWT real (fora do escopo desta refatoração) no resumo final.

### F06 [HIGH] Defaults de runtime inseguros
File: app.py:9-15, app.py:33-34
Catalog: AP-10 | Fix: PB-01
Evidence:
```python
CORS(app)
...
app.run(debug=True, host='0.0.0.0', port=5000)
```
Description: `debug=True` com `host='0.0.0.0'` expõe o debugger interativo do Werkzeug (execução remota de código) em qualquer interface de rede, e `CORS(app)` libera todas as origens sem restrição.
Impact: Em produção, um atacante na rede pode acionar o debugger do Werkzeug e executar código arbitrário; CORS aberto permite qualquer site fazer requisições autenticadas.
Recommendation: Ler `DEBUG`/`HOST`/`CORS_ORIGINS` de variáveis de ambiente com default seguro (`DEBUG=False`), restringindo CORS às origens esperadas.

### F07 [HIGH] Acoplamento forte / efeitos colaterais no import
File: app.py:30-31
Catalog: AP-09 | Fix: PB-07
Evidence:
```python
with app.app_context():
    db.create_all()
```
Description: O app Flask é criado e configurado em nível de módulo, e `db.create_all()` roda assim que `app.py` é importado — inclusive quando `seed.py` faz `from app import app, db`, sem factory nem proteção por `if __name__`.
Impact: Não é possível importar o app em testes sem efeitos colaterais (criação de schema); ordem de boot acoplada à ordem de import.
Recommendation: Extrair um `create_app()` (composition root) que registra blueprints e chama `db.create_all()` explicitamente; `app.py` passa a só chamar `create_app()` e `app.run(...)` dentro de `if __name__ == '__main__'`.

### F08 [MEDIUM] Consultas N+1 e agregações repetidas
File: routes/task_routes.py:41-56, routes/user_routes.py:22, routes/report_routes.py:55-68, routes/report_routes.py:19-28
Catalog: AP-13 | Fix: PB-09
Evidence:
```python
if t.user_id:
    user = User.query.get(t.user_id)
...
'task_count': len(u.tasks)
```
Description: `get_tasks` dispara um `SELECT` de usuário e outro de categoria por task retornada; `get_users` acessa `u.tasks` (lazy relationship) por usuário; `summary_report` roda uma query de tasks por usuário dentro de um loop; status e prioridade são contados com 4+5 `COUNT` separados em vez de um `GROUP BY`.
Impact: O número de queries cresce linearmente com o volume de dados, degradando a latência dos endpoints de listagem e relatório.
Recommendation: Usar `joinedload`/`selectinload` para trazer `user`/`category` junto da query principal, e substituir os `COUNT` repetidos por uma única agregação `GROUP BY status` / `GROUP BY priority`.

### F09 [MEDIUM] Lógica duplicada
File: models/task.py:50-60, routes/task_routes.py:30-39, routes/task_routes.py:71-80, routes/task_routes.py:283-287, routes/user_routes.py:171-180, routes/report_routes.py:34-43, routes/report_routes.py:132-135, utils/helpers.py:57-108
Catalog: AP-14 | Fix: PB-13, PB-08
Evidence:
```python
# models/task.py já tem:
def is_overdue(self):
    ...
# mas routes/task_routes.py recalcula do zero:
if t.due_date and t.due_date < datetime.utcnow() and t.status not in (...):
    task_data['overdue'] = True
```
Description: A regra "task atrasada" é recalculada manualmente em 6 lugares diferentes mesmo existindo `Task.is_overdue()`; a validação de campos de task (título, status, prioridade, tags) está duplicada entre `create_task`/`update_task` e novamente, de forma não usada, em `utils/helpers.py:process_task_data`.
Impact: Regras podem divergir silenciosamente (ex. alguém corrige o bug de atraso em um lugar e esquece os outros cinco).
Recommendation: Chamar `Task.is_overdue()` em todo lugar que hoje recalcula, e extrair um único validador (controller/service) usado por `create_task` e `update_task`; remover `process_task_data` se não for adotado.

### F10 [MEDIUM] Validação de entrada ausente/inconsistente
File: routes/task_routes.py:113, routes/task_routes.py:182, routes/task_routes.py:260-264
Catalog: AP-15 | Fix: PB-13
Evidence:
```python
priority = data.get('priority', 3)
...
if priority < 1 or priority > 5:
...
if priority:
    tasks = tasks.filter(Task.priority == int(priority))
```
Description: `priority` vindo do body não tem checagem de tipo antes da comparação numérica (um valor não numérico gera `TypeError` → 500), e `search_tasks` converte `priority`/`user_id` da query string com `int()` sem tratar `ValueError`.
Impact: Entradas inválidas do cliente, que deveriam gerar 400, derrubam a rota com 500 e expõem stack trace (ver F11).
Recommendation: Validar/converter os campos numéricos com tratamento de erro explícito (`try/except ValueError` → 400) antes de usar em comparações ou filtros.

### F11 [MEDIUM] Exceções engolidas / erros internos vazados
File: routes/task_routes.py:62, routes/task_routes.py:137, routes/task_routes.py:204, routes/task_routes.py:236, routes/user_routes.py:130, routes/user_routes.py:149, routes/report_routes.py:186, routes/report_routes.py:207, routes/report_routes.py:221, utils/helpers.py:46, utils/helpers.py:49, utils/helpers.py:88
Catalog: AP-16 | Fix: PB-11
Evidence:
```python
try:
    tasks = Task.query.all()
    ...
except:
    return jsonify({'error': 'Erro interno'}), 500
```
Description: Vários `except:` genéricos (sem tipo) escondem a causa real do erro — inclusive em `get_tasks`, que embrulha toda a função num único `try/except` silencioso — e não há um handler de erro centralizado.
Impact: Bugs reais (ex. erro de tipo, conexão) ficam indistinguíveis de erros esperados; não há padronização do formato de erro.
Recommendation: Substituir por excepções tipadas (`NotFoundError`, `ValidationError`) tratadas por um `error_handler` central; usar `except Exception` apenas na borda, logando o stacktrace e devolvendo mensagem genérica.

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
Description: Ao deletar uma categoria, as tasks que referenciam `category_id` não são atualizadas nem removidas — diferente de `delete_user` (routes/user_routes.py:140-142), que já apaga as tasks do usuário antes de excluí-lo.
Impact: Tasks ficam com `category_id` apontando para um registro inexistente, gerando `category_name: None` silenciosamente e relatórios inconsistentes.
Recommendation: Ao deletar a categoria, definir `category_id = NULL` nas tasks relacionadas (ou bloquear a exclusão se houver tasks vinculadas), dentro do model/controller de categoria.

### F13 [MEDIUM] Responsabilidade mal posicionada / camada não usada
File: services/notification_service.py:1-48, utils/helpers.py:19-41, utils/helpers.py:110-116, routes/report_routes.py:7, routes/report_routes.py:157-223
Catalog: AP-19 | Fix: PB-05
Evidence:
```python
from utils.helpers import format_date, calculate_percentage
# nenhuma das duas é chamada no arquivo
```
Description: `NotificationService` existe mas nunca é importado por nenhuma rota; `utils/helpers.py` tem `validate_email`, `sanitize_string`, `generate_id`, `is_valid_color`, `process_task_data`, `log_action` e as constantes `VALID_STATUSES`/`VALID_ROLES`/etc. sem nenhum caller, enquanto as rotas reimplementam a mesma regex de e-mail e as mesmas listas localmente; `report_routes.py` importa `format_date`/`calculate_percentage` mas nunca os chama; o CRUD de categorias vive dentro do blueprint de relatórios em vez de um módulo próprio.
Impact: As camadas "organizadas" são apenas aparência — a regra real está duplicada nas rotas, e o serviço de notificação (atribuição/atraso de task) nunca dispara de fato.
Recommendation: Ligar `NotificationService` aos eventos de criação/atraso de task (ou remover se fora do escopo), apontar as rotas para os helpers existentes (ou remover os que não farão sentido), e mover o CRUD de categorias para seu próprio blueprint/model.

### F14 [MEDIUM] APIs deprecated
File: models/task.py:15-16, models/task.py:52, services/notification_service.py:35, utils/helpers.py:38, seed.py:66-74 (+ routes listadas na tabela abaixo)
Catalog: AP-18 | Fix: PB-14
Evidence:
```python
created_at = db.Column(db.DateTime, default=datetime.utcnow)
```
Description: `datetime.utcnow()` é usado como default de coluna e em cálculos de data em praticamente todo o projeto; é deprecated desde Python 3.12 (ambiente local roda 3.14) por retornar datetime "naive". O código também usa `Model.query.get(id)` (API legacy do Flask-SQLAlchemy 3.x) em 15 pontos.
Impact: `datetime.utcnow()` já emite `DeprecationWarning` e pode ser removido em versão futura do Python; `Query.get` é o padrão legacy que a SQLAlchemy 2.x recomenda substituir.
Recommendation: Trocar por `datetime.now(timezone.utc)` em todos os pontos listados na tabela "Deprecated APIs"; trocar `Model.query.get(id)` por `db.session.get(Model, id)`.

### F15 [LOW] Imports não usados / código morto
File: app.py:7, routes/task_routes.py:7, routes/user_routes.py:6, routes/report_routes.py:8, utils/helpers.py:3-6
Catalog: AP-22 | Fix: PB-15
Evidence:
```python
import os, sys, json, datetime  # app.py — os, sys, json nunca usados
```
Description: `os`, `sys`, `json` (e em `utils/helpers.py` também `math`) são importados e nunca referenciados nos respectivos arquivos.
Impact: Ruído que dificulta entender as dependências reais de cada módulo.
Recommendation: Remover os imports não utilizados.

### F16 [LOW] `print` como logging
File: routes/task_routes.py:149, routes/task_routes.py:153, routes/task_routes.py:219, routes/task_routes.py:234, routes/user_routes.py:83, routes/user_routes.py:89, routes/user_routes.py:147, services/notification_service.py:21, services/notification_service.py:24, utils/helpers.py:39, utils/helpers.py:41
Catalog: AP-23 | Fix: PB-15
Evidence:
```python
print(f"Task criada: {task.id} - {task.title}")
```
Description: Eventos da aplicação (criação/atualização/exclusão, erros, envio de e-mail) são logados com `print`, sem nível, formato ou destino configurável.
Impact: Impossível filtrar por severidade ou rotear os logs em produção; erros e eventos normais se misturam na mesma saída.
Recommendation: Usar `logging.getLogger(__name__)` com níveis apropriados (`info`/`error`) no lugar de cada `print`.

### F17 [LOW] Construções não idiomáticas
File: models/task.py:38-43, models/task.py:50-60, models/user.py:34-38, routes/task_routes.py:141, routes/task_routes.py:210, utils/helpers.py:103
Catalog: AP-24 | Fix: PB-15
Evidence:
```python
def validate_status(self, new_status):
    valid = [...]
    if new_status in valid:
        return True
    else:
        return False
```
Description: Padrão `if cond: return True else: return False` em vez de `return cond` (`validate_status`, `is_overdue`, `is_admin`), e `type(x) == list` em vez de `isinstance(x, list)`.
Impact: Apenas legibilidade/estilo — sem risco funcional.
Recommendation: Simplificar para `return cond` e usar `isinstance`.

### F18 [LOW] Nomenclatura pouco descritiva
File: routes/task_routes.py:16, routes/user_routes.py:14, routes/report_routes.py:55
Catalog: AP-21 | Fix: PB-15
Evidence:
```python
for t in tasks:
    task_data = {}
```
Description: Variáveis de uma letra (`t`, `u`, `c`, `cat`) para entidades de domínio (task, user, category) em vários loops nas três rotas.
Impact: Apenas legibilidade — dificulta a leitura de trechos já densos.
Recommendation: Renomear para `task`, `user`, `category` nos loops principais.

## Deprecated APIs
| File:line | Deprecated usage | Modern replacement |
|-----------|------------------|--------------------|
| models/task.py:15 | `datetime.utcnow` (default de coluna) | `lambda: datetime.now(timezone.utc)` |
| models/task.py:16 | `datetime.utcnow` (onupdate) | `lambda: datetime.now(timezone.utc)` |
| models/task.py:52 | `datetime.utcnow()` | `datetime.now(timezone.utc)` |
| models/category.py:11 | `datetime.utcnow` (default de coluna) | `lambda: datetime.now(timezone.utc)` |
| models/user.py:14 | `datetime.utcnow` (default de coluna) | `lambda: datetime.now(timezone.utc)` |
| routes/task_routes.py:31,72,215,285 | `datetime.utcnow()` | `datetime.now(timezone.utc)` |
| routes/user_routes.py:172 | `datetime.utcnow()` | `datetime.now(timezone.utc)` |
| routes/report_routes.py:35,42,45,71,133 | `datetime.utcnow()` | `datetime.now(timezone.utc)` |
| services/notification_service.py:35 | `datetime.utcnow()` | `datetime.now(timezone.utc)` |
| utils/helpers.py:38 | `datetime.utcnow()` | `datetime.now(timezone.utc)` |
| seed.py:66,67,69,70,74 | `datetime.utcnow()` | `datetime.now(timezone.utc)` |
| routes/task_routes.py:42,51,67,117,122,158,188,195,227 | `Model.query.get(id)` | `db.session.get(Model, id)` |
| routes/user_routes.py:29,94,136,155 | `Model.query.get(id)` | `db.session.get(Model, id)` |
| routes/report_routes.py:105,192,213 | `Model.query.get(id)` | `db.session.get(Model, id)` |

## Proposed Target Architecture
Maturidade: Camadas parciais → estratégia "completar em vigor" (mvc-guidelines.md §5): manter `models/`, `routes/`, `services/`, `utils/` e seus nomes/imports (ex.: `seed.py` continua fazendo `from app import app, db`), e adicionar o que falta:

```
task-manager-api/
├── app.py                      # create_app() + `app` em nível de módulo (compat com seed.py/python app.py)
├── config/
│   └── settings.py             # SECRET_KEY, CORS_ORIGINS, DEBUG, ADMIN_TOKEN via env; VALID_STATUSES/VALID_ROLES/etc.
├── database.py                 # mantém db = SQLAlchemy()
├── models/                     # mantém; passa a ser usado (is_overdue, to_dict sem password)
│   ├── task.py / category.py / user.py
├── controllers/                # NOVO: task_controller.py, user_controller.py, category_controller.py, report_controller.py
├── routes/                     # mantém nomes; handlers passam a delegar ao controller (1–3 linhas)
│   ├── task_routes.py / user_routes.py / report_routes.py (+ category_routes.py, se separado do report)
├── services/
│   └── notification_service.py # mantém; recebe config injetada, passa a ser chamado pelo controller de task
├── middlewares/
│   └── error_handler.py        # NOVO: handler central para NotFoundError/ValidationError/Exception
└── utils/
    └── helpers.py               # mantém só o que for efetivamente chamado pelos controllers
```

Rotas, métodos HTTP, status codes de sucesso e formato das respostas são preservados; mudanças de contrato ficam restritas à remoção de `password` das respostas e ao bloqueio de `role` client-controlled, listadas no resumo final da Fase 3.

================================
Total: 18 findings
================================
