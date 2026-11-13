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
| 10 | MEDIUM | **Padrão legado de callbacks** (`sqlite3` usado só com callbacks) em vez de promises/`async-await`. Não é API *deprecated*: o driver ainda suporta callbacks | `src/AppManager.js:37-137` | Torna o tratamento de erros frágil e esconde falhas. |
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
- **Autoverificação obrigatória.** Antes de mostrar o relatório, a skill roda um snippet bash (em `audit-report-template.md`) que confere:
  - se todo `caminho:linha` citado existe e está dentro do tamanho do arquivo;
  - se todo `File:` tem número de linha;
  - se os totais batem.

  Na Fase 3, todo número do bloco de validação precisa vir de um comando executado, e o `.env.example` é conferido contra as variáveis que a config realmente lê.

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

No total foram **17 execuções completas das Fases 1+2** (7 no P1, 5 no P2, 5 no P3) e **9 da Fase 3**, divididas em uma fase inicial de ajuste e 4 rodadas de correção. Todas as tentativas descartadas, com relatórios e logs, estão em [docs/logs/iterations/](docs/logs/iterations/) (`iterN` = ajuste inicial, `runN` = rodada N).

Para não depender só de leitura humana, escrevi um verificador independente, [docs/logs/check-report.py](docs/logs/check-report.py). Ele confere:
- se cada `caminho:linha` citado existe e está dentro do tamanho do arquivo;
- se a ordenação e os totais estão consistentes;
- se a contagem de arquivos bate com o `find` real.

Cada rodada só avançou quando o verificador não acusou nada.

| # | Problema observado | Causa | Correção na skill |
|---|---|---|---|
| 1 | No P1, iteração 1, a tabela-resumo trazia locais vagos (`controllers.py`, "múltiplas funções") e um finding sem linhas | O template permitia isso | `audit-report-template.md`: proíbe nome de arquivo sem linha e define o formato `path:linhas (+N)` |
| 2 | A arquitetura proposta na Fase 2 ignorava o layout das guidelines | As guidelines só eram lidas na Fase 3 | A Fase 2 passou a consultar `mvc-guidelines.md` §2/§5 |
| 3 | No P1, iteração 2, o projeto foi classificado como "Camadas parciais" | Existem arquivos chamados `controllers.py` e `models.py` | `project-analysis.md`: "nome de arquivo não é camada". Arquivos únicos por camada contendo todos os domínios = Monolítica |
| 4 | O modelo imprimiu só a tabela e **afirmou** ter impresso o relatório completo no chat | Exigência difícil de cumprir em saídas longas | O relatório completo vai para o arquivo. O chat mostra uma versão condensada de cada finding, e a skill proíbe declarar como impresso o que não foi |
| 5 | No P2, iteração 1, a skill também protegeu `DELETE /api/users/:id` com token | A política de contrato era ambígua | `mvc-guidelines.md` §4: token **apenas** em SQL/código arbitrário, reset do banco e rotas `/admin`. O resto mantém o acesso original e recebe uma recomendação |
| 6 | O template de smoke test gerava `curl -X ""` | Em `local m="$1" args=(… "$m")`, o bash expande `$m` antes da atribuição | `validation-guide.md`: `local` separado. O agente detectou o bug com `bash -x` e contornou sozinho |
| 7 | Senhas com hash tornam incompatível um `loja.db` antigo | O banco de dados guarda o formato antigo | A validação parte sempre de banco limpo (remove `*.db` antes de cada boot), e a mudança aparece em "Contract Changes" |
| 8 | Rodada 1: o P2 citou `utils.js:1-7` sem o `src/`, o P3 contou 14 arquivos quando eram 15 e ficou sem `.env.example` | As regras não exigiam caminho completo, contagem por comando nem `.env.example` em projeto parcial | Caminho completo a partir da raiz. Contagem = saída literal de `find … \| wc -l`, incluindo `__init__` vazios. `.env.example` obrigatório em qualquer maturidade, com checagem de cobertura |
| 9 | Rodada 2: comentários das evidências sem o caminho completo (`# user_routes.py:61`), intervalo `1-49` num arquivo de 48 linhas e um `File: ver tabela` | Regras em texto não bastavam | **Autoverificação obrigatória** no template: um snippet bash que valida todo `caminho:linha`, todo `File:` e os totais antes de imprimir o relatório |
| 10 | Rodada 3: relatórios 100% precisos, mas o chat mostrava só a tabela-resumo (P1, P2 e P3) | O modelo tratava a lista como redundante com o arquivo | O passo 9 explica que o humano aprova lendo o chat e adota um formato curto de 2 linhas por finding. Na rodada 4: 20/20, 17/17 e 18/18 no chat |
| 11 | Rodada 4: as execuções do P2 e do P3 pararam no meio por limite de uso da conta | Limite da sessão Claude | Execuções incompletas descartadas e refeitas depois que o limite renovou |
| 12 | Rodada 4: os resumos da Fase 3 do P1 e do P3 escreveram "6" e "9" variáveis, quando eram 7 e 10 (o código estava correto) | Número escrito de memória | A linha passa a listar os **nomes** das variáveis, todo número do bloco de validação deve vir de um comando executado e nenhum artefato de runtime pode sobrar. P1 e P3 foram refeitos com essa versão |
| 13 | O `sqlite3` com callbacks às vezes aparecia como API deprecated e às vezes não | O catálogo listava o padrão em AP-12 e em AP-18 ao mesmo tempo | AP-18 passa a valer só para APIs oficialmente deprecated. Callbacks ainda suportados ficam em AP-12 |
| 14 | Na rodada final, minha varredura de código morto ([deadcode.py](docs/logs/deadcode.py)) achou `format_date` em `task-manager-api/utils/helpers.py` sem nenhum uso. O resumo da Fase 3 afirmava ter removido as funções mortas | A autoverificação da Fase 3 confere config, segredos e APIs deprecated, mas não varre código morto | **Ajuste manual** depois da skill: função removida e smoke do P3 repetido (37/37 iguais à validação). É o único trecho do código refatorado que não saiu da skill. Fica como melhoria futura incluir a varredura de código morto no `validation-guide.md` |

Também registrei o que a skill **decidiu não fazer**:
- implementar autenticação real (JWT/sessão), que exige decisões de produto;
- conectar o `NotificationService` no P3, o que criaria uma chamada de rede síncrona nova.

Os dois casos aparecem como recomendação no resumo da Fase 3.

---

## C) Resultados

### Versão da skill usada na rodada final

| Projeto | Commit da skill | Observação |
|---|---|---|
| P1 code-smells | `a7f868b` (final) | Fases 1-3 com a versão final |
| P2 ecommerce | `59b1c4f` | Rodou antes do último ajuste, que mudou só 3 pontos: o texto da linha do `.env.example` no bloco de validação, a regra de limpar artefatos e o esclarecimento de AP-18 no catálogo. O resultado do P2 já cumpria os três: `.env.example` com 4/4 variáveis, nenhum artefato e a seção de deprecated coerente com o catálogo final |
| P3 task-manager | `a7f868b` (final) | Fases 1-3 com a versão final |

As 3 cópias versionadas da skill são idênticas (`diff -r`) e correspondem ao commit `a7f868b`.

### Resumo das auditorias (Fase 2)

| Projeto | Stack detectada | Maturidade | CRITICAL | HIGH | MEDIUM | LOW | Total | Relatório |
|---|---|---|---|---|---|---|---|---|
| code-smells-project | Python + Flask 3.1.1 | Monolítica | 6 | 5 | 5 | 4 | **20** | [audit-project-1.md](reports/audit-project-1.md) |
| ecommerce-api-legacy | Node.js 20 + Express 4.x | Monolítica | 4 | 4 | 4 | 5 | **17** | [audit-project-2.md](reports/audit-project-2.md) |
| task-manager-api | Python + Flask 3.0.0 + Flask-SQLAlchemy | Camadas parciais | 3 | 4 | 7 | 4 | **18** | [audit-project-3.md](reports/audit-project-3.md) |

Verificação automática dos 3 relatórios com [check-report.py](docs/logs/check-report.py) e com a autoverificação da própria skill:
- **zero** caminhos inexistentes ou linhas fora do arquivo (111, 37 e 97 referências conferidas);
- contagem de arquivos igual à real (4, 3 e 15);
- ordenação e totais consistentes;
- todos os findings listados também no chat (20/20, 17/17 e 18/18).

Cobertura da análise manual: os achados da seção A foram todos encontrados pela skill. O mínimo exigido era 5 por projeto.

APIs deprecated:
- **P1:** nenhuma. A seção existe e registra o que foi verificado.
- **P2:** nenhuma API oficialmente deprecated. O padrão legado de callbacks do `sqlite3` aparece como callback hell (AP-12) e foi migrado para async/await.
- **P3:** `datetime.utcnow()` (deprecated no Python 3.12+) e `Model.query.get()` (legado no SQLAlchemy 2.0), com tabela de todas as ocorrências.

### Validação independente (além da validação feita pela própria skill)

Para cada projeto, escrevi um smoke test próprio ([smoke-p1.sh](docs/logs/smoke-p1.sh), [smoke-p2.sh](docs/logs/smoke-p2.sh), [smoke-p3.sh](docs/logs/smoke-p3.sh)) cobrindo todas as rotas, com casos de sucesso, 404 e 400. Rodei o mesmo script contra o **original** (commit `6d1ce62`) e contra o **refatorado**, partindo de banco limpo.

| Projeto | Requisições | Status idênticos | Diferenças (todas intencionais) |
|---|---|---|---|
| P1 | 34 | 31 | Login com SQL Injection `' OR '1'='1`: **200 → 401** (antes entrava sem senha). `/admin/query` e `/admin/reset-db` sem token: 200 → 403 (com token: 200) |
| P2 | 13 | 10 | `GET /api/admin/financial-report` sem token: 200 → 403 (com token: 200, mesmo formato) |
| P3 | 37 | 36 | `POST /tasks` com `priority: "3"`: **500 (TypeError) → 400** |

Saídas completas: [project-1-smoke.txt](docs/logs/project-1-smoke.txt), [project-2-smoke.txt](docs/logs/project-2-smoke.txt), [project-3-smoke.txt](docs/logs/project-3-smoke.txt).

Também conferi:
- `senha`/`password` sumiram das respostas;
- `/health` do P1 não expõe mais `secret_key`, `db_path` nem `debug`;
- P1: body vazio em `/login` e `/pedidos/:id/status` agora dá 400, e produto referenciado em pedido é desativado (`ativo=0`) em vez de apagado;
- P2: `DELETE /api/users/:id` remove matrículas e pagamentos em cascata;
- P3: cadastro com `role: "admin"` cria um `user`, e `seed.py` e `app.py` rodam com `-W error::DeprecationWarning` sem falhar;
- `.env.example` lista exatamente as variáveis lidas pela config: P1 7/7, P2 4/4, P3 6/6;
- os envelopes `dados/sucesso/erro`, `error` e texto puro foram preservados.

### Antes / depois

**code-smells-project** (de 4 arquivos para 35 em `src/`)
```
ANTES                         DEPOIS
app.py         (rotas+admin)  app.py                      # entry point fino (python app.py)
controllers.py (validação…)   .env.example
models.py      (SQL 4 dom.)   src/app.py                  # create_app() — composition root
database.py    (global conn)  src/config/settings.py      # env vars + constantes
                              src/database.py             # conexão por request (flask.g), schema, seed com hash
                              src/models/{produto,usuario,pedido}_model.py
                              src/controllers/{home,health,produto,usuario,pedido,relatorio,admin}_controller.py
                              src/views/{home,health,produto,usuario,pedido,relatorio,admin}_routes.py   # blueprints
                              src/services/{relatorio,notification}_service.py
                              src/validators/{produto,usuario,pedido}_validator.py
                              src/middlewares/{error_handler,auth}.py
```

**ecommerce-api-legacy** (de God Class para 26 arquivos em camadas)
```
ANTES                          DEPOIS
src/app.js                     src/app.js                       # composition root (npm start inalterado)
src/AppManager.js (God Class)  src/config/{index,constants,logger}.js
src/utils.js (segredos+cache)  src/database/connection.js       # sqlite3 promisificado + transaction()
                               src/models/{user,course,enrollment,payment,auditLog,report}Model.js
                               src/services/{checkout,report,user}Service.js
                               src/controllers/{checkout,report,user}Controller.js
                               src/routes/index.js + {checkout,admin,user}Routes.js
                               src/middlewares/{errorHandler,asyncHandler,adminAuth}.js
                               src/errors/index.js              # AppError e subclasses
                               src/utils/password.js            # scrypt + salt
                               .env.example
```

**task-manager-api** (camadas completadas no lugar, sem renomear `routes/`)
```
ANTES                                  DEPOIS
app.py  (config hardcoded)             app.py              # create_app() + `app` para o seed.py
models/ (MD5, to_dict com password)    models/             # werkzeug hash, to_dict seguro, is_overdue() único
routes/ (regras + validação + N+1)     routes/             # finas: task, user, report + category_routes (separada)
services/ (SMTP hardcoded, sem uso)    (removido)          # código morto: nenhuma rota usava o NotificationService
utils/helpers.py (maioria sem uso)     utils/helpers.py    # só as funções usadas
                                       utils/time.py       # utcnow timezone-aware
                                       config/settings.py  # NOVO
                                       controllers/        # NOVO: task, user, category, report
                                       middlewares/error_handler.py  # NOVO
                                       .env.example        # NOVO
```

### Checklist de validação

| Item | P1 code-smells | P2 ecommerce | P3 task-manager |
|---|---|---|---|
| **Fase 1** — Linguagem detectada corretamente | ✅ Python | ✅ JavaScript/Node 20 | ✅ Python |
| Framework detectado corretamente | ✅ Flask 3.1.1 | ✅ Express 4.x | ✅ Flask 3.0.0 + Flask-SQLAlchemy |
| Domínio descrito corretamente | ✅ E-commerce | ✅ LMS com checkout | ✅ Task Manager |
| Nº de arquivos condiz com a realidade | ✅ 4 | ✅ 3 | ✅ 15 |
| **Fase 2** — Relatório segue o template | ✅ | ✅ | ✅ |
| Cada finding com arquivo e linhas exatos | ✅ 111 refs | ✅ 37 refs | ✅ 97 refs |
| Ordenado CRITICAL → LOW | ✅ | ✅ | ✅ |
| Mínimo de 5 findings | ✅ 20 | ✅ 17 | ✅ 18 |
| APIs deprecated (se aplicável) | ✅ seção com "nenhuma" | ✅ seção com "nenhuma" (callbacks em AP-12) | ✅ `utcnow`, `query.get` |
| Pausa e pede confirmação antes da Fase 3 | ✅ | ✅ | ✅ |
| **Fase 3** — Estrutura segue MVC | ✅ | ✅ | ✅ |
| Config extraída (sem hardcoded) | ✅ `src/config/settings.py` + `.env.example` (7/7) | ✅ `src/config/index.js` + `.env.example` (4/4) | ✅ `config/settings.py` + `.env.example` (6/6) |
| Models abstraem os dados | ✅ | ✅ | ✅ |
| Views/Routes separadas | ✅ `src/views/` | ✅ `src/routes/` | ✅ `routes/` |
| Controllers concentram o fluxo | ✅ | ✅ | ✅ |
| Error handling centralizado | ✅ | ✅ | ✅ |
| Entry point claro | ✅ `app.py` → `create_app()` | ✅ `src/app.js` | ✅ `app.py` → `create_app()` |
| Aplicação inicia sem erros | ✅ | ✅ | ✅ |
| Endpoints originais respondem | ✅ 31/34 iguais + 3 de segurança | ✅ 10/13 iguais + 3 do `/admin` | ✅ 36/37 iguais + 1 bug corrigido |

### Logs das execuções

| Projeto | Fases 1+2 | Fase 3 | Smoke independente |
|---|---|---|---|
| P1 | [project-1-phase1-2.log](docs/logs/project-1-phase1-2.log) | [project-1-phase3.log](docs/logs/project-1-phase3.log) | [project-1-smoke.txt](docs/logs/project-1-smoke.txt) |
| P2 | [project-2-phase1-2.log](docs/logs/project-2-phase1-2.log) | [project-2-phase3.log](docs/logs/project-2-phase3.log) | [project-2-smoke.txt](docs/logs/project-2-smoke.txt) |
| P3 | [project-3-phase1-2.log](docs/logs/project-3-phase1-2.log) | [project-3-phase3.log](docs/logs/project-3-phase3.log) | [project-3-smoke.txt](docs/logs/project-3-smoke.txt) |

Os logs foram extraídos do `--output-format stream-json` do Claude Code e mostram as mensagens do agente e um resumo de cada ferramenta usada. A seção "Boot do refatorado", no fim de cada arquivo de smoke, traz as primeiras linhas do servidor no ar.

### Observações sobre o comportamento em stacks diferentes

- **Mesma skill, sem nenhum ajuste por stack.** Todos os ajustes das rodadas foram genéricos: formato, precisão e verificação, nunca regras específicas de um projeto.
- **Monólito Python (P1).** Gerou o layout completo em `src/` e manteve `python app.py` através de um entry point fino.
- **God Class Node (P2).**
  - Criou uma camada `services/` para checkout, relatório e exclusão em cascata, que são regras com transação.
  - Promisificou o `sqlite3` e manteve os nomes públicos do payload (`usr`, `eml`, `c_id`), renomeando só internamente.
  - Preservou o formato de erro em **texto puro** do original.
- **Projeto parcial (P3).**
  - Seguiu a estratégia "completar em vigor": manteve `routes/`, adicionou `controllers/` e `config/`, e respeitou o import `from app import app, db` do `seed.py`.
  - Preservou o envelope `{"error": …}`, diferente do `{"erro": …}` do P1.
  - Removeu código morto: o `NotificationService` nunca era chamado. Uma função morta que sobrou (`format_date`) foi removida à mão; ver o item 14 de "Desafios encontrados".
- **Variação entre execuções.** O mesmo projeto gera números de findings ligeiramente diferentes a cada execução (o P1 teve 19 a 22). Os problemas centrais (segurança, God Class, N+1) aparecem sempre. O que varia é como problemas parecidos são agrupados.
- **Formato JSON.** No P1 e no P3 o JSON deixou de sair indentado. Era efeito colateral de `debug=True`, e as chaves e valores são os mesmos.
- **Modelo e custo.** As execuções headless usaram o modelo padrão do Claude Code no ambiente (`claude-sonnet-5`, registrado na primeira linha de cada log). Custo da rodada final: P1 US$ 1,46 + 5,44; P2 US$ 1,10 + 3,16; P3 US$ 1,43 + 4,99 (Fases 1+2 e Fase 3).

---

## D) Como Executar

### Pré-requisitos
- **Claude Code** instalado e autenticado (`claude --version`).
- **Python 3.10+** com `venv` e `pip` (no Debian/Ubuntu: `sudo apt install python3-venv python3-pip`).
- **Node.js 18+** e npm.
- `git` e `curl`, para validar.

### Preparar os ambientes
```bash
git clone https://github.com/pizolatoguilherme/mba-ia-refactor-projects-skill.git
cd mba-ia-refactor-projects-skill

(cd code-smells-project && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)
(cd task-manager-api   && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)
(cd ecommerce-api-legacy && npm install)
```

### Executar a skill (ordem sugerida: P1 → P2 → P3)
A skill está em `.claude/skills/refactor-arch/` dentro de cada projeto. Os projetos deste repositório **já estão refatorados**. Para reproduzir a refatoração do zero, clone o [repositório base](https://github.com/devfullcycle/mba-ia-refactor-projects-skill) e copie a pasta `.claude/` de qualquer projeto deste repositório para dentro de cada projeto de lá.

**Interativo** (pausa na Fase 2 e espera `y`):
```bash
cd code-smells-project   && claude "/refactor-arch"
cd ../ecommerce-api-legacy && claude "/refactor-arch"
cd ../task-manager-api     && claude "/refactor-arch"
```

**Headless** (como foi executado aqui):
```bash
cd code-smells-project
claude -p "/refactor-arch" --permission-mode acceptEdits \
  --allowedTools "Bash Read Write Edit Glob Grep" --add-dir .. \
  --output-format stream-json --verbose > phase1-2.jsonl      # Fases 1+2, para em [y/n]
claude -p "y" --resume <session_id> --permission-mode acceptEdits \
  --allowedTools "Bash Read Write Edit Glob Grep" --add-dir .. \
  --output-format stream-json --verbose > phase3.jsonl        # Fase 3
```

O `session_id` está no evento `init` do primeiro arquivo. Use `--resume <id>` em vez de `-c`, para não retomar a sessão errada.

O relatório é salvo em `reports/audit-<pasta-do-projeto>.md`. Neste repositório ele foi renomeado para `reports/audit-project-N.md`.

### Rodar e validar os projetos refatorados
```bash
# P1 — http://localhost:5000
cd code-smells-project && ADMIN_TOKEN=troque-me .venv/bin/python app.py

# P2 — http://localhost:3000
cd ecommerce-api-legacy && ADMIN_TOKEN=troque-me npm start

# P3 — http://localhost:5000 (rode o seed antes)
cd task-manager-api && .venv/bin/python seed.py && .venv/bin/python app.py
```

Smoke tests (com o app no ar, em outro terminal):
```bash
bash docs/logs/smoke-p1.sh http://127.0.0.1:5000 /tmp/p1.txt && cat /tmp/p1.txt
bash docs/logs/smoke-p2.sh http://127.0.0.1:3000 /tmp/p2.txt && cat /tmp/p2.txt
bash docs/logs/smoke-p3.sh http://127.0.0.1:5000 /tmp/p3.txt && cat /tmp/p3.txt
```

Os scripts usam o token `smoke-token`. Para ver os 200 nas rotas `/admin`, suba os apps com `ADMIN_TOKEN=smoke-token`.

Rotas protegidas exigem o header `X-Admin-Token: <ADMIN_TOKEN>`:
- P1: `/admin/query` e `/admin/reset-db`;
- P2: `/api/admin/financial-report`.

Sem `ADMIN_TOKEN` definido, essas rotas respondem 403.

Compare a saída com as seções "ANTES" e "DEPOIS" de `docs/logs/project-N-smoke.txt`.

### Variáveis de ambiente
| Projeto | Variáveis (todas listadas no `.env.example` do projeto) |
|---|---|
| P1 | `SECRET_KEY`, `FLASK_DEBUG`, `HOST`, `PORT`, `DB_PATH`, `ADMIN_TOKEN`, `CORS_ORIGINS` |
| P2 | `PORT`, `DB_PATH`, `PAYMENT_GATEWAY_KEY`, `ADMIN_TOKEN` |
| P3 | `SECRET_KEY`, `FLASK_DEBUG`, `HOST`, `PORT`, `DATABASE_URL`, `CORS_ORIGINS` |

Sem `SECRET_KEY`, P1 e P3 geram uma chave aleatória a cada boot e mostram um aviso.
