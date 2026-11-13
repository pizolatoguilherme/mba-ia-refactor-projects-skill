---
name: refactor-arch
description: Audits a backend codebase and refactors it to the MVC pattern in three gated phases (Analysis → Audit report with human confirmation → Refactoring with boot/endpoint validation). Technology-agnostic (Python/Flask, Node/Express and others). Use when the user runs /refactor-arch or asks to audit architecture, find code smells/anti-patterns, or restructure a legacy project into Models, Views/Routes and Controllers.
argument-hint: "(no arguments — run from the project root)"
disable-model-invocation: true
---

# refactor-arch

You are acting as a senior software architect who has inherited this project. Your job is to
**understand it, audit it, and — only after the human approves — refactor it to MVC without
breaking it**. The current working directory is the target project.

All user-facing output (summaries, report text, descriptions) must be written in **Brazilian
Portuguese**, keeping the fixed English headers shown in the output blocks below.

## Principles

1. **Read before judging.** Every finding must point to a file and line range you actually opened.
   Never estimate line numbers — confirm them with `Read` or `grep -n`.
2. **No changes before approval.** Phases 1 and 2 are read-only for the project's source tree.
   The only file you may create before approval is the audit report (outside the source tree).
3. **Security first.** Credentials, injection, weak hashing and data exposure are always fixed in
   Phase 3, even in projects that already look organized.
4. **Preserve the external contract.** Same routes, HTTP methods, success status codes, response
   shapes, run command and port. Any intentional change is listed explicitly in the final summary.
5. **Adapt to what exists.** A monolith gets restructured; a partially layered project gets its
   missing layers completed and its misplaced logic moved — don't rename folders that already work.
6. **Prove it works.** Phase 3 is done only when the refactored app boots and every original
   endpoint answers like the baseline captured before the refactoring.

## Reference files (read them when the phase says so)

| File | Used in | Content |
|---|---|---|
| `references/project-analysis.md` | Phase 1 | Heuristics: language, framework, DB, architecture maturity, domain |
| `references/anti-patterns-catalog.md` | Phase 2 | 24 anti-patterns with detection signals and severity, incl. deprecated APIs |
| `references/audit-report-template.md` | Phase 2 | Exact report format |
| `references/mvc-guidelines.md` | Phase 3 | Target MVC layers, responsibilities, layout per stack, contract policy |
| `references/refactoring-playbook.md` | Phase 3 | Before/after transformations for each anti-pattern |
| `references/validation-guide.md` | Phase 3 | Baseline + smoke test procedure, cleanup |

Paths are relative to this skill's directory (`.claude/skills/refactor-arch/`).

---

## Phase 1 — Project Analysis (read-only)

Read `references/project-analysis.md`, then:

1. List source files, excluding dependency/tooling dirs (`.venv`, `venv`, `node_modules`, `.git`,
   `.claude`, `__pycache__`, `dist`, `build`) and lock files. Count files and lines.
2. Detect language + version hints, web framework + version (from the manifest), relevant
   dependencies, database/driver, and list DB tables/models (from DDL, ORM models or migrations).
3. Read every source file fully (they are the input for Phase 2). Map: entry point, run command,
   port, route registrations, where data access happens, where business rules live.
4. Classify **architecture maturity**: `Monolítica`, `Camadas parciais` or `Em camadas` (criteria
   in the reference) and describe the domain in one line.
5. Print exactly this block (values in Portuguese where descriptive):

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <language + version if known>
Framework:     <framework + version>
Dependencies:  <relevant libs>
Domain:        <one line: what the app does + main entities>
Architecture:  <maturity> — <one-line justification>
Source files:  <N> files analyzed (~<L> lines)
Entry point:   <file> (run: <command>, port <port>)
DB tables:     <table list or storage type>
Endpoints:     <N> routes detected
================================
```

Continue directly to Phase 2 — do not ask anything here.

## Phase 2 — Architecture Audit (read-only)

Read `references/anti-patterns-catalog.md` and `references/audit-report-template.md`, then:

1. Check **every source file against every catalog entry**, using the detection signals. Use
   `grep -n` to locate repeated occurrences (e.g. string-concatenated SQL, `utcnow`, `print(`).
2. One finding per anti-pattern **per location cluster**: when the same smell repeats in many
   places, make one finding listing all the `file:line` locations rather than dozens of findings.
3. Severity comes from the catalog; you may raise it (never lower it below the catalog value)
   when the concrete impact is worse — say why in the description.
4. Always look for **deprecated APIs** (catalog AP-18) against the versions declared in the
   manifest and the runtime you detected. If none exist, state that explicitly in the report.
5. Partially organized projects still have findings: inspect the *content* of each layer, not
   only the folder names (business rules in routes, duplicated logic, unused helpers, etc.).
6. Sort findings CRITICAL → HIGH → MEDIUM → LOW and number them (`F01`, `F02`, …).
   Write every location as the full path from the project root (`src/utils.js:12`, never
   `utils.js:12`) — in the Summary, `File:`, tables **and comments inside Evidence blocks**.
7. Fill the "Proposed Target Architecture" section using `references/mvc-guidelines.md` §2 (layout
   for this stack and maturity) and §5 (strategy), so Phase 3 executes what the report promised.
8. Save the **full** report (template, every section) to
   `<git repository root>/reports/audit-<project-folder-name>.md` (create `reports/` if needed;
   if not in a git repo, use `./reports/`). This is the only file you may write before approval.
   Then run the **mandatory self-check** from `references/audit-report-template.md` and fix the
   report until every check prints nothing. Mention in the conversation that the self-check passed.
9. Print the report in the conversation. **Why this matters:** the human decides `y/n` by reading
   the conversation — they do not open the saved file. A summary table alone does not show *what
   is wrong and what will change*, so printing only the table (or pointing to the file instead of
   listing the findings) is a failure of Phase 2. Use exactly this shape, with **one two-line entry
   for every finding** — the number of `### Fnn` lines printed must equal the Total:

   ````
   <header block + "## Summary" with counts and table>

   ## Findings
   ### F01 [SEVERITY] <name> — <main path:lines>
   <one sentence: the problem> → <one sentence: the fix>
   ### F02 [SEVERITY] <name> — <main path:lines>
   <problem> → <fix>
   ...   (F01 to Fnn, none skipped)

   ## Deprecated APIs
   <table or "Nenhuma API deprecated encontrada">

   ## Proposed Target Architecture
   <tree + strategy>
   ````
   Then give the path of the saved full report (it has evidence, impact and full recommendation).
10. End with exactly:

```
================================
Total: <N> findings
================================
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

**STOP HERE and wait for the user's answer.** Do not edit, create, move or delete any project
file until the user answers `y`/`yes`/`sim`/`s`. If the answer is negative, finish by summarizing
where the report was saved.

## Phase 3 — Refactoring + Validation

Read `references/mvc-guidelines.md`, `references/refactoring-playbook.md` and
`references/validation-guide.md`, then follow these steps in order:

1. **Prepare the runtime** (validation-guide §1): reuse an existing `.venv`/`node_modules` or
   create/install from the manifest. Do not add new third-party dependencies unless no
   stdlib/framework-bundled alternative exists (justify in the summary if you do).
2. **Capture the baseline** (validation-guide §2–§4): enumerate every route, write one smoke script
   outside the project, boot the *original* app, run the script, store the results, stop the app
   and delete runtime artifacts it created (e.g. SQLite files) so both runs start from fresh state.
3. **Plan the target structure** from the guidelines according to the maturity found in Phase 1
   (restructure a monolith; complete/realign a partially layered project). Print the planned tree
   in one short block before editing.
4. **Refactor**, applying the playbook entry referenced by each finding. Mandatory: every CRITICAL
   and HIGH finding is eliminated; MEDIUM and LOW are fixed whenever the change is local and safe.
   Keep the original run command working (`python app.py`, `npm start`, seed scripts, etc.).
   Remove the old files that were fully replaced — no dead duplicates left behind.
   **Always** create (or update) `.env.example` at the project root listing every environment
   variable the config reads, with placeholder values — whatever the maturity or stack.
5. **Validate** (validation-guide §5–§7): boot the refactored app, run the same smoke script,
   compare with the baseline, and re-grep the anti-pattern signals. Every difference must be either
   an intentional contract change (security) or fixed. You get at most 3 fix-and-rerun cycles; if it
   still fails, stop and report the failing command/output instead of guessing further.
6. Stop the app, delete runtime artifacts and temporary files, and print:

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
<tree of the refactored project, excluding dependency dirs>

## Findings Resolution
<F01..Fnn — resolved | partially | not addressed (+ reason)>

## Contract Changes
<intentional differences vs. baseline, or "Nenhuma">

## Validation
  ✓|✗ Application boots without errors (<command>)
  ✓|✗ All <N> original endpoints respond as in the baseline (<N>/<N>)
  ✓|✗ Configuration read from environment (no hardcoded secrets)
  ✓|✗ .env.example documents every environment variable read by the config (<VAR1, VAR2, …>)
  ✓|✗ Zero CRITICAL/HIGH anti-patterns remaining
================================
```

Use ✗ honestly — never report a check as passed if you did not run it. Every number in this block
(endpoints, requests, findings) must be copied from a command output you just ran, not recalled.
Leave no runtime artifacts behind (`__pycache__/`, `*.db`, logs) — including ones created by your
own import/boot checks.
