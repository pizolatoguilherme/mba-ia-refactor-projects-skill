# Refatoração Arquitetural Automatizada com a Skill `refactor-arch`

Entrega do desafio **"Criação de Skills — Refatoração Arquitetural Automatizada"** (MBA em Engenharia de Software com IA — Full Cycle).
O enunciado original está no [repositório base](https://github.com/devfullcycle/mba-ia-refactor-projects-skill).

A skill `refactor-arch` para o **Claude Code** audita um backend legado e o refatora para **MVC** em 3 fases:

1. **Análise.** Detecta a stack e mapeia a arquitetura.
2. **Auditoria.** Gera o relatório e pausa para pedir confirmação.
3. **Refatoração.** Reestrutura o código e valida que a aplicação continua funcionando.

A skill foi executada nos 3 projetos deste repositório.

| Projeto | Stack | Domínio |
|---|---|---|
| [code-smells-project](code-smells-project/) | Python 3 + Flask 3.1 + sqlite3 | API de E-commerce |
| [ecommerce-api-legacy](ecommerce-api-legacy/) | Node.js + Express 4 + sqlite3 | LMS com checkout |
| [task-manager-api](task-manager-api/) | Python 3 + Flask 3.0 + Flask-SQLAlchemy | Task Manager |

---

## A) Análise Manual

Antes de criar a skill, li os 3 projetos linha a linha. As linhas citadas abaixo se referem ao código **original** (commit `6d1ce62`). A severidade segue a escala do enunciado:

- **CRITICAL:** segurança, ou separação de responsabilidades totalmente violada.
- **HIGH:** violação forte de MVC/SOLID.
- **MEDIUM:** duplicação, performance ou validação.
- **LOW:** legibilidade.

### Projeto 1 — code-smells-project (Python/Flask, monólito em 4 arquivos)

| # | Severidade | Problema | Local | Por que importa |
|---|---|---|---|---|
| 1 | CRITICAL | **SQL Injection**: queries montadas por concatenação de strings, inclusive no login | `models.py:28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140, 174, 280, 289-297` | `' OR '1'='1` no login entra sem senha. Qualquer campo permite ler ou apagar o banco. |
| 2 | CRITICAL | **Execução de SQL arbitrário e reset do banco sem autenticação** (`/admin/query`, `/admin/reset-db`) | `app.py:47-78` | Uma única requisição anônima despeja ou destrói o banco inteiro. |
| 3 | CRITICAL | **Credenciais hardcoded e vazadas**: `SECRET_KEY` literal, que o `/health` ainda devolve junto com `db_path` e `debug` | `app.py:7`; `controllers.py:285-289` | Quem acessa o repositório, ou só o endpoint de health, obtém o segredo usado para assinar sessões. |
| 4 | CRITICAL | **Senhas em texto puro**: gravadas e comparadas sem hash e devolvidas no `GET /usuarios` | `database.py:76-78`; `models.py:83, 99, 126-129` | Um vazamento do banco, ou uma simples chamada à API, expõe a senha de todos os usuários. |
| 5 | CRITICAL | **God Module**: `models.py` concentra SQL, regras (estoque, desconto) e formatação de 4 domínios. `controllers.py` mistura validação, notificações e health check com SQL | `models.py:1-314`; `controllers.py:1-292` | Nada pode ser testado isoladamente, e qualquer mudança afeta todos os domínios. |
| 6 | HIGH | **Regra de negócio no controller/model errado**: notificações simuladas com `print` dentro dos controllers e política de desconto dentro do acesso a dados | `controllers.py:208-210, 247-250`; `models.py:256-262` | Regras ficam presas à camada HTTP ou SQL e não podem ser reutilizadas. |
| 7 | HIGH | **Estado global mutável**: uma conexão única com `check_same_thread=False`, compartilhada entre threads | `database.py:4-11` | Condições de corrida no servidor multi-thread do Flask. |
| 8 | HIGH | **Debug ligado em produção** (`DEBUG=True`, `debug=True` em `0.0.0.0`) | `app.py:8, 88` | O debugger do Werkzeug permite executar código remotamente. |
| 9 | MEDIUM | **N+1 queries** em pedidos (1 + N + N×M consultas), com a função duplicada para "todos" e "por usuário" | `models.py:171-201, 203-233` | A latência cresce com o volume de dados, e as duas cópias divergem com o tempo. |
| 10 | MEDIUM | **Validação duplicada ou ausente**: o mesmo bloco em criar e atualizar produto. `login` e `atualizar_status` quebram com body vazio (500) | `controllers.py:24-62, 64-96, 169-170, 239-240` | Regras divergem, e erros de cliente viram 500. |
| 11 | MEDIUM | **Exceções engolidas e vazadas**: `except Exception` em todos os handlers devolvendo `str(e)` ao cliente | `controllers.py:10-12, 21-22, …` | Vaza detalhes internos e não há tratamento central. |
| 12 | LOW | **Magic numbers e strings**: faixas e taxas de desconto, listas de categorias e status inline | `models.py:256-262`; `controllers.py:52, 242` | Regras de negócio ficam escondidas no meio do código. |
| 13 | LOW | **`print` como log e imports sem uso** (`sqlite3` em models, `os` em database) | `controllers.py:8, 57, 106…`; `models.py:2`; `database.py:2` | Sem níveis nem destino configurável, e com ruído no código. |

### Projeto 2 — ecommerce-api-legacy (Node.js/Express, God Class)

| # | Severidade | Problema | Local | Por que importa |
|---|---|---|---|---|
| 1 | CRITICAL | **Credenciais hardcoded**: senha do banco, chave de gateway `pk_live_…` e usuário SMTP | `src/utils.js:1-7` | Segredos de produção versionados no repositório. |
| 2 | CRITICAL | **Hash de senha inseguro** (`badCrypto`: base64 repetido e truncado em 10 caracteres) e senha padrão `"123456"` quando o cliente não envia uma | `src/utils.js:17-23`; `src/AppManager.js:68`; seed com senha em texto puro em `:18` | O hash é reversível ou colidível e a conta nasce com senha previsível. |
| 3 | CRITICAL | **Vazamento de dados de cartão**: o número do cartão e a chave do gateway vão para o log | `src/AppManager.js:45` | Viola PCI-DSS: os dados sensíveis acabam no agregador de logs. |
| 4 | CRITICAL | **God Class `AppManager`**: cria o schema, faz o seed, registra rotas, processa pagamento, matrícula, auditoria e relatório | `src/AppManager.js:4-139` | Não há camadas, e não dá para testar nem trocar o banco. |
| 5 | HIGH | **Callback hell sem transação**: matrícula, pagamento e auditoria aninhados em 5 níveis, com `self = this` | `src/AppManager.js:37-77` | Uma falha no meio deixa matrícula sem pagamento, e o fluxo fica ilegível. |
| 6 | HIGH | **Estado global mutável** (`globalCache`, `totalRevenue`; este é exportado por valor e nunca é atualizado) | `src/utils.js:9-15, 25` | Estado compartilhado e enganoso, já que a receita acumulada nunca muda. |
| 7 | HIGH | **Endpoints administrativos sem autenticação**: relatório financeiro e exclusão de usuário | `src/AppManager.js:80, 131` | Qualquer pessoa vê a receita e apaga usuários. |
| 8 | MEDIUM | **N+1 no relatório financeiro**: 1 query por curso, mais 2 por matrícula | `src/AppManager.js:83-128` | O número de queries cresce com cursos × alunos. |
| 9 | MEDIUM | **Erros ignorados e falta de integridade referencial**: `err` ignorado (com `enrollments` undefined, o processo cai) e DELETE de usuário sem cascade (a própria mensagem admite "dados sujos") | `src/AppManager.js:92-93, 104-106, 131-137` | Um erro de banco derruba o servidor, e sobram registros órfãos. |
| 10 | MEDIUM | **API legada de callbacks** (`sqlite3` callback-style) em vez de promises/`async-await` | `src/AppManager.js:37-137` | Padrão obsoleto que torna o tratamento de erros frágil. |
| 11 | LOW | **Nomes crípticos** (`u, e, p, cid, cc`) e `let` para valores que nunca mudam | `src/AppManager.js:29-33` | Legibilidade ruim. |
| 12 | LOW | **Magic values**: cartão aprovado se começar com `"4"`, 10000 iterações, porta 3000 | `src/AppManager.js:46`; `src/utils.js:6, 19` | Regras implícitas espalhadas pelo código. |

### Projeto 3 — task-manager-api (Python/Flask, camadas parciais)

| # | Severidade | Problema | Local | Por que importa |
|---|---|---|---|---|
| 1 | CRITICAL | **Segredos hardcoded**: `SECRET_KEY` e usuário/senha do SMTP | `app.py:13`; `services/notification_service.py:7-10` | Credenciais versionadas no repositório. |
| 2 | CRITICAL | **MD5 para senha e hash exposto na API**: o `to_dict()` inclui `password`, que é devolvido no login e em GET/POST/PUT de usuário | `models/user.py:21, 27-32`; `routes/user_routes.py:33, 85, 129, 209` | Um hash MD5 sem salt se quebra em segundos, e a API ainda o entrega. |
| 3 | HIGH | **Autenticação quebrada**: token fake `'fake-jwt-token-' + id` e `role` escolhido pelo próprio cliente no cadastro | `routes/user_routes.py:52, 71-72, 210` | Qualquer pessoa cria uma conta `admin` e o token é previsível. |
| 4 | HIGH | **Rotas "gordas"**: validação e regra de negócio dentro dos handlers. `utils/helpers.py` (`process_task_data`, constantes) existe mas nunca é usado. CRUD de categorias mora em `report_routes.py` | `routes/task_routes.py:85-223`; `utils/helpers.py:57-116`; `routes/report_routes.py:157-223` | A organização é só física: não há controllers e as camadas existentes são ignoradas. |
| 5 | HIGH | **Debug ligado em produção** | `app.py:34` | Execução remota de código pelo debugger. |
| 6 | MEDIUM | **N+1**: usuário e categoria buscados por task, `len(u.tasks)` por usuário, count por categoria, tasks por usuário no relatório | `routes/task_routes.py:41-57`; `routes/user_routes.py:22`; `routes/report_routes.py:53-68, 159-164` | Muitas queries por request. |
| 7 | MEDIUM | **Lógica duplicada**: o cálculo de "overdue" aparece 5 vezes, apesar de existir `Task.is_overdue()`, e a serialização de task está duplicada | `routes/task_routes.py:17-39, 71-80, 283-287`; `routes/user_routes.py:171-180`; `routes/report_routes.py:33-43` | As regras divergem em silêncio. |
| 8 | MEDIUM | **APIs deprecated**: `Model.query.get()` (legado no SQLAlchemy 2.0) e `datetime.utcnow()` (deprecated no Python 3.12+) | `routes/task_routes.py:42, 51, 67, 117, 122, 158, 188, 195`; `routes/user_routes.py:29, 94, 136, 155`; `models/*.py` | Geram warnings hoje e serão removidas em versões futuras. |
| 9 | MEDIUM | **`except:` sem tipo e validação de tipo ausente**: `priority` enviada como string resulta em `TypeError` e 500, e `update_category` quebra com body vazio | `routes/task_routes.py:62, 113, 137, 204, 236`; `routes/report_routes.py:186, 196`; `utils/helpers.py:46, 49, 88` | Esconde bugs, e erros de cliente viram 500. |
| 10 | MEDIUM | **Contagens repetidas**: 9 `COUNT` separados no relatório em vez de `GROUP BY` | `routes/report_routes.py:15-28` | Idas desnecessárias ao banco. |
| 11 | LOW | **Imports sem uso** (`os, sys, json`, `time`, `hashlib`, `math`…) | `app.py:7`; `routes/task_routes.py:7`; `routes/user_routes.py:6`; `utils/helpers.py:2-7` | Ruído no código. |
| 12 | LOW | **Construções não idiomáticas** (`type(x) == list`, `if …: return True else: return False`) e `print` como log | `routes/task_routes.py:141, 149, 210`; `models/user.py:34-38`; `models/task.py:38-48` | Legibilidade. |

### Padrões recorrentes (insumo para a skill)
- **Nos 3 projetos:** segredos hardcoded, senhas mal protegidas ou expostas, `debug`/print, N+1, regra de negócio na camada HTTP e ausência de tratamento de erro centralizado.
- **Varia entre os projetos:**
  - o *grau de organização*: monólito, God Class ou camadas parciais;
  - o *dialeto de acesso a dados*: sqlite3 cru, sqlite3 com callbacks ou ORM;
  - o *formato de erro*: `{"erro"}`, texto puro ou `{"error"}`.

  A skill precisa se adaptar a essas três dimensões em vez de aplicar um template fixo.

---

## B) Construção da Skill

### Estrutura

```
.claude/skills/refactor-arch/
├── SKILL.md                         # o "prompt": princípios + 3 fases + blocos de saída fixos
└── references/
    ├── project-analysis.md          # heurísticas de linguagem, framework, banco, maturidade e domínio
    ├── anti-patterns-catalog.md     # 24 anti-patterns (6 CRITICAL, 6 HIGH, 7 MEDIUM, 5 LOW) + tabela de APIs deprecated
    ├── audit-report-template.md     # formato exato do relatório da Fase 2
    ├── mvc-guidelines.md            # camadas, layout alvo por stack, política de contrato
    ├── refactoring-playbook.md      # 16 transformações com código antes/depois (Python e JS)
    └── validation-guide.md          # baseline + smoke test + comparação + limpeza
```

| Área exigida | Arquivo |
|---|---|
| Análise de projeto | `project-analysis.md` |
| Catálogo de anti-patterns (≥8, com deprecated APIs) | `anti-patterns-catalog.md` (24 itens; AP-18 = APIs deprecated) |
| Template de relatório | `audit-report-template.md` |
| Guidelines de arquitetura MVC | `mvc-guidelines.md` |
| Playbook de refatoração (≥8 com antes/depois) | `refactoring-playbook.md` (16 padrões) |

### Decisões de design

- **O SKILL.md é curto e procedural.** Ele diz *o que fazer e quando*. O conhecimento de domínio (*como detectar, como corrigir*) fica nas referências, e cada fase manda ler só os arquivos de que precisa (*progressive disclosure*).
- **Blocos de saída fixos.** `PHASE 1`, o relatório e `PHASE 3` funcionam como contrato de saída, o que torna execuções diferentes comparáveis e fáceis de validar com o checklist.
- **Portão explícito na Fase 2.** A regra "nada é escrito no projeto antes do `y`" aparece nos princípios e no fim da fase. O único arquivo permitido antes da confirmação é o relatório em `reports/`, fora do código-fonte.
- **Sem perguntas antes da Fase 2.** Isso permite rodar a skill de forma headless (`claude -p`) e retomar com `claude -c -p "y"`.
- **`disable-model-invocation: true`.** Como a skill altera código, ela só roda quando alguém digita `/refactor-arch`, nunca por iniciativa do modelo.
- **Validação por baseline.** Antes de mexer no código, a Fase 3 sobe a aplicação **original** e grava status e corpo de todas as rotas. Depois da refatoração, roda o mesmo script sobre um banco limpo e compara linha a linha. "Funciona" passa a ser uma diferença verificável, não uma impressão.
- **Política de contrato explícita.** Rotas, métodos, status e envelopes (`dados/sucesso/erro`, `error`, texto puro) são preservados. As únicas mudanças permitidas são as de segurança, e todas são listadas em "Contract Changes":
  - remover senhas e segredos das respostas;
  - proteger `/admin/query` e `/admin/reset-db` com `X-Admin-Token` **sem apagar as rotas**;
  - bloquear escalada de privilégio.
- **Sem dependências novas.** O hash de senha usa `werkzeug.security` (já vem com o Flask) e `crypto.scrypt` (nativo do Node).

### Anti-patterns do catálogo e por quê

| Severidade | Anti-patterns | Motivação |
|---|---|---|
| CRITICAL | Credenciais hardcoded, SQL Injection, endpoint de SQL arbitrário/reset sem auth, hash de senha fraco ou ausente, exposição de dados sensíveis (resposta e log), God Class/Module | Aparecem nos 3 projetos e têm impacto imediato de segurança ou bloqueiam qualquer separação de camadas |
| HIGH | Regra de negócio em controller/rota, estado global mutável, acoplamento sem DI com efeitos colaterais no import, defaults inseguros (debug), autenticação/autorização quebrada, callback hell sem transação | Violações de MVC/SOLID que impedem testes e geram inconsistência |
| MEDIUM | N+1 e contagens repetidas, lógica duplicada, validação ausente, exceções engolidas ou vazadas, falta de integridade referencial, **APIs deprecated**, responsabilidade no módulo errado ou camada não usada | Performance e manutenção. O último item cobre projetos "falsamente organizados" |
| LOW | Magic numbers, nomes ruins, imports e código morto, print/console.log como log, construções não idiomáticas | Legibilidade |

Cada item traz **sinais de detecção concretos** (por exemplo, `cursor.execute("..." + var)`, `` db.run(`...${id}`) ``, `Model.query.get(`, 3 ou mais callbacks aninhados, query dentro de `for`/`forEach`) e aponta para a transformação do playbook que o corrige.

### Como a skill é agnóstica de tecnologia

1. **Detecção pelo manifesto.** `requirements.txt`, `package.json`, `go.mod`, `Gemfile`, `pom.xml` e outros, com tabelas de framework, banco e padrões de rota para cada stack.
2. **Sinais por linguagem, ideia universal.** O catálogo descreve o conceito (por exemplo, "SQL construído com dados do request") e dá exemplos de Python e JS. Para outras stacks, o agente procura o construto equivalente.
3. **Estratégia por maturidade.** A Fase 1 classifica o projeto como *Monolítica*, *Camadas parciais* ou *Em camadas*:
   - um monólito é reestruturado em `src/`;
   - um projeto parcial mantém suas convenções (`routes/` continua `routes/`) e ganha `controllers/`, `config/` e `middlewares/`.
4. **Layouts alvo por stack** (Flask monólito, Flask parcial, Express, outros), sempre preservando o comando de execução original.
5. **Validação por HTTP (curl).** Funciona para qualquer servidor web, sem depender de um framework de testes específico.

### Desafios encontrados

_Preenchido após as execuções (ver seção C)._

---

## C) Resultados

_Em andamento: será preenchido após a execução da skill nos 3 projetos._

---

## D) Como Executar

_Em andamento._
