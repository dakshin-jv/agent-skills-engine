# Building & Using Claude Skills — A Developer's Reference

> **Version:** 1.0
> **Audience:** Developers building, deploying, testing, and maintaining Agent Skills
> **Basis:** Anthropic's official documentation (platform.claude.com), from the October 2025 launch onward.
> **Scope:** This is a practical, developer-facing guide — how to author skills, wire in scripts, deploy across surfaces (claude.ai, Claude Code, API), test them, and reason about the tradeoffs.

---

## Table of Contents

1. [What a Skill Is (Developer Framing)](#1-what-a-skill-is-developer-framing)
2. [Anatomy of a Skill](#2-anatomy-of-a-skill)
3. [How Skills Load — The Three-Level Model](#3-how-skills-load--the-three-level-model)
4. [Writing an Effective SKILL.md](#4-writing-an-effective-skillmd)
5. [Scripts: Execute vs. Read](#5-scripts-execute-vs-read)
6. [Runtime Environment & Dependencies](#6-runtime-environment--dependencies)
7. [Progressive Disclosure & File Organization](#7-progressive-disclosure--file-organization)
8. [Workflows, Feedback Loops & Validation](#8-workflows-feedback-loops--validation)
9. [Evaluation-Driven Development](#9-evaluation-driven-development)
10. [Distribution & Deployment](#10-distribution--deployment)
11. [Using Skills via the API & Managed Agents](#11-using-skills-via-the-api--managed-agents)
12. [Tradeoffs — When to Use a Skill vs. Plain Code](#12-tradeoffs--when-to-use-a-skill-vs-plain-code)
13. [Error Handling Realities](#13-error-handling-realities)
14. [Security Considerations](#14-security-considerations)
15. [Anti-Patterns to Avoid](#15-anti-patterns-to-avoid)
16. [Pre-Ship Checklist](#16-pre-ship-checklist)
17. [Appendix A — Minimal SKILL.md Template](#appendix-a--minimal-skillmd-template)
18. [Appendix B — Reference Links](#appendix-b--reference-links)
19. [Appendix C — Glossary](#appendix-c--glossary)

---

## 1. What a Skill Is (Developer Framing)

A Skill is a **filesystem-based folder** containing a `SKILL.md` file plus optional supporting files (scripts, reference docs, assets, templates). It packages domain expertise — workflows, conventions, procedures — that turns a general-purpose model into a specialist for a given task.

The defining property: a skill **loads on demand**. It only affects the context window when it becomes relevant to the current task. This is what lets you install many skills without paying for all of them on every request.

### Skills vs. MCP — a distinction that matters

| | Skills | MCP servers |
|---|---|---|
| **What they change** | *Behavior* — how Claude performs a task | *Capability* — what external tools/data Claude can reach |
| **Form** | Instructions + scripts + resources in a folder | A server exposing tools over a protocol |
| **Relationship** | A skill can *instruct* Claude to call an MCP tool | A tool a skill might depend on |

They compose well: MCP for connectivity, Skills for encoding how to use that connectivity correctly.

### Where skills run

Skills work across three surfaces from a single `SKILL.md` format:

- **Claude apps** (claude.ai, desktop, mobile) — Pro, Max, Team, Enterprise plans, with Code Execution enabled.
- **Claude Code** — dropped into `~/.claude/skills` or a project's `.claude/skills/`.
- **Claude API / Agent SDK** — attached to Messages API requests and managed via the `/v1/skills` endpoint. Requires the Code Execution Tool beta.

---

## 2. Anatomy of a Skill

```
skill-name/
├── SKILL.md              # REQUIRED: YAML frontmatter + markdown instructions
├── reference.md          # optional: detailed docs, loaded on demand
├── examples.md           # optional: input/output pairs
├── FORMS.md              # optional: feature-specific guide
└── scripts/              # optional: executable code
    ├── analyze.py        #   → executed, source NOT loaded into context
    └── validate.py
```

### The `SKILL.md` file

Two parts: YAML frontmatter (metadata) and a markdown body (instructions).

**YAML frontmatter — required fields:**

| Field | Rules |
|---|---|
| `name` | ≤ 64 characters; lowercase letters, numbers, hyphens only; no XML tags; cannot contain reserved words `anthropic` or `claude`. |
| `description` | Non-empty; ≤ 1024 characters; no XML tags; written in third person; states **what the skill does** *and* **when to use it**. |

The `description` is the single most important field for discovery. Claude uses it — potentially against 100+ available skills — to decide whether to trigger this one. The body provides implementation detail; the description alone drives selection.

### Supporting file types (all optional)

- **Reference files** (`.md`) — deep documentation, API references, schemas. Loaded into context only when Claude follows a link to them.
- **Scripts** (`scripts/`) — executable utilities. Run via bash without loading their source; only their *output* consumes tokens.
- **Assets** — templates, fonts, images, boilerplate used in producing output.

You can add **custom folders** (e.g. `templates/`, `schemas/`, `reference/`) freely, as long as they're referenced clearly from `SKILL.md`. Anthropic's own examples organize by domain (e.g. `reference/finance.md`, `reference/sales.md`).

---

## 3. How Skills Load — The Three-Level Model

This is the core mental model for reasoning about context cost.

**Level 1 — Metadata (always loaded).**
At startup, only the `name` and `description` from every installed skill's frontmatter are injected into the system prompt. This is the pre-load cost of having a skill available. It's small, but it's *not free* — descriptions across many skills add up, which is why concision matters and why you should prune unused skills.

**Level 2 — SKILL.md body (loaded when triggered).**
When the task matches a skill's description, Claude reads the full `SKILL.md` body from the filesystem via a bash read. This is where your instructions live. Keep it under ~500 lines.

**Level 3 — Bundled resources (loaded/executed on demand).**
- Reference files are read only when Claude follows a link to them — no cost until then.
- Scripts are **executed**, not read. Claude runs `python scripts/foo.py` via bash; the source never enters context. Only stdout/stderr costs tokens.

**Key consequence for authors:** you can bundle comprehensive resources — full API docs, large datasets, extensive examples — with *zero* context penalty until they're actually accessed. This filesystem-based model is what makes progressive disclosure possible.

---

## 4. Writing an Effective SKILL.md

### Principle 1 — Concise is key

The context window is a shared resource. Once `SKILL.md` loads, every token competes with conversation history, other skills' metadata, and the user's actual request.

Default assumption: **Claude is already very smart.** Only add what it doesn't already know. Interrogate each line — "Does Claude really need this? Can I assume it knows this? Does this paragraph justify its token cost?"

**Good (concise, ~50 tokens):**
```markdown
## Extract PDF text

Use pdfplumber for text extraction:

    import pdfplumber
    with pdfplumber.open("file.pdf") as pdf:
        text = pdf.pages[0].extract_text()
```

**Bad (verbose, ~150 tokens):** a paragraph explaining what a PDF is, that libraries exist, why pdfplumber is nice, how to pip install it… all of which Claude already knows.

### Principle 2 — Set appropriate degrees of freedom

Match specificity to how fragile and variable the task is.

| Freedom | Use when | Form |
|---|---|---|
| **High** | Many valid approaches; context-dependent decisions | Prose steps ("Analyze structure, check for bugs, suggest improvements") |
| **Medium** | A preferred pattern exists; some variation OK | Parameterized script or pseudocode |
| **Low** | Fragile, order-critical, consistency essential | Exact commands, "do not modify" |

Analogy: a **narrow bridge with cliffs** (DB migrations) needs exact guardrails; an **open field** (code review) needs general direction and trust.

### Principle 3 — Write discovery-friendly descriptions

Always **third person**. The description is injected into the system prompt; inconsistent point-of-view harms discovery.

- Good: `Processes Excel files and generates reports.`
- Avoid: `I can help you process Excel files.` / `You can use this to…`

Be specific and include key trigger terms:

```yaml
description: Extract text and tables from PDF files, fill forms, merge
  documents. Use when working with PDF files or when the user mentions
  PDFs, forms, or document extraction.
```

Avoid vague descriptions: `Helps with documents.` / `Processes data.` / `Does stuff with files.`

### Principle 4 — Consistent terminology

Pick one term and stick to it. Don't mix "field / box / element / control" or "extract / pull / get / retrieve." Consistency helps Claude follow instructions reliably.

### Principle 5 — Naming conventions

Prefer **gerund form**: `processing-pdfs`, `analyzing-spreadsheets`, `managing-databases`. Noun phrases (`pdf-processing`) and action forms (`process-pdfs`) are acceptable. Avoid vague names (`helper`, `utils`, `tools`) and reserved words.

---

## 5. Scripts: Execute vs. Read

Scripts are how skills perform deterministic work reliably. The single most important authoring decision here is signaling **intent**:

- **Execute** (most common): *"Run `analyze_form.py` to extract fields."*
- **Read as reference** (for complex logic Claude should study): *"See `analyze_form.py` for the extraction algorithm."*

Execution is preferred for utility scripts — more reliable, more efficient, source stays out of context.

### Why ship scripts at all (vs. letting Claude generate code)?

- More reliable than freshly generated code.
- Saves tokens (no code in context).
- Saves time (no generation step).
- Ensures consistency across every invocation.

### Solve, don't punt

Handle error conditions *inside* the script rather than leaving Claude to figure them out.

**Good:**
```python
def process_file(path):
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        print(f"File {path} not found, creating default")
        with open(path, "w") as f:
            f.write("")
        return ""
    except PermissionError:
        print(f"Cannot access {path}, using default")
        return ""
```

**Bad:**
```python
def process_file(path):
    return open(path).read()   # just fails; Claude left to guess
```

### No voodoo constants

Document every magic number. "If you don't know the right value, how will Claude?"

```python
# HTTP requests typically complete within 30s; longer covers slow links
REQUEST_TIMEOUT = 30
# Three retries balances reliability vs speed; most transient failures
# resolve by the second retry
MAX_RETRIES = 3
```

### Paths

Always forward slashes: `scripts/helper.py`, never `scripts\helper.py`. Unix-style paths work everywhere; Windows-style paths break on Unix.

---

## 6. Runtime Environment & Dependencies

Skills run in a code-execution sandbox with filesystem access, bash, and code execution. Authoring implications:

- **File paths matter** — Claude navigates your skill like a filesystem; use descriptive names (`form_validation_rules.md`, not `doc2.md`).
- **Organize for discovery** — group by domain (`reference/finance.md`, `reference/sales.md`), not `docs/file1.md`.
- **Bundle freely** — large reference material costs nothing until read.
- **Prefer scripts for deterministic ops** — write `validate_form.py` instead of asking Claude to generate validation code each time.

### Dependency availability differs by surface — a critical deployment gotcha

| Surface | Package installation |
|---|---|
| **claude.ai** | Can install from npm and PyPI, and pull from GitHub repos |
| **Claude API** | **No network access, no runtime package installation** |

If you target the API, you cannot rely on installing packages at runtime — everything must be pre-available. Always list required packages explicitly in `SKILL.md`, and verify they exist in the code execution environment.

### MCP tool references

If your skill calls MCP tools, always use fully qualified names: `ServerName:tool_name` (e.g. `BigQuery:bigquery_schema`, `GitHub:create_issue`). Without the server prefix, Claude may fail to locate the tool when multiple servers are present.

---

## 7. Progressive Disclosure & File Organization

`SKILL.md` should act like a table of contents that points to detail as needed.

**Rules:**
- Keep the `SKILL.md` body under **500 lines**.
- Keep references **one level deep** from `SKILL.md`. Nested references (SKILL → advanced → details) cause Claude to preview partially (`head -100`) and miss content.
- Add a **table of contents** to any reference file over ~100 lines, so partial reads still reveal full scope.

**Pattern 1 — High-level guide with references:**
```markdown
# PDF Processing

## Quick start
[inline minimal example]

## Advanced features
**Form filling**: See FORMS.md
**API reference**: See REFERENCE.md
**Examples**: See EXAMPLES.md
```

**Pattern 2 — Domain-specific organization** (load only what's relevant):
```
bigquery-skill/
├── SKILL.md            # overview + navigation
└── reference/
    ├── finance.md      # revenue, billing
    ├── sales.md        # pipeline, accounts
    ├── product.md      # API usage
    └── marketing.md    # campaigns
```
When the user asks about revenue, Claude reads only `reference/finance.md`; the others stay on disk at zero cost.

**Pattern 3 — Conditional details:** show basic content inline, link advanced content (`REDLINING.md`, `OOXML.md`) that's read only when the feature is needed.

---

## 8. Workflows, Feedback Loops & Validation

### Workflows for complex tasks

Break complex operations into sequential steps. For multi-step processes, give Claude a checklist to copy and tick off:

```markdown
## PDF form filling workflow

Task Progress:
- [ ] Step 1: Analyze the form (run analyze_form.py)
- [ ] Step 2: Create field mapping (edit fields.json)
- [ ] Step 3: Validate mapping (run validate_fields.py)
- [ ] Step 4: Fill the form (run fill_form.py)
- [ ] Step 5: Verify output (run verify_output.py)
```

Explicit steps stop Claude skipping critical validation.

### Feedback loops

The pattern **run validator → fix errors → repeat** materially improves output quality. The "validator" can be a script *or* a reference document (e.g. a style guide Claude checks against).

```markdown
## Document editing process
1. Edit word/document.xml
2. Validate immediately: python ooxml/scripts/validate.py unpacked_dir/
3. If it fails: read the error, fix, re-run
4. Only proceed when validation passes
5. Rebuild and test
```

### Plan-validate-execute

For high-stakes or batch operations, have Claude produce a structured **plan file** (e.g. `changes.json`), validate it with a script, and only then execute. This catches errors before they touch originals, keeps planning reversible, and gives machine-verifiable checkpoints. Use for batch operations, destructive changes, and complex validation rules. Make validation scripts verbose with specific, actionable error messages.

---

## 9. Evaluation-Driven Development

**Build evaluations *before* writing extensive documentation.** This keeps you solving real problems, not imagined ones.

1. **Identify gaps** — run Claude on representative tasks *without* the skill; document specific failures.
2. **Create evaluations** — build at least three scenarios targeting those gaps.
3. **Establish a baseline** — measure performance without the skill.
4. **Write minimal instructions** — just enough to pass the evals.
5. **Iterate** — run evals, compare to baseline, refine.

**Evaluation shape:**
```json
{
  "skills": ["pdf-processing"],
  "query": "Extract all text from this PDF and save it to output.txt",
  "files": ["test-files/document.pdf"],
  "expected_behavior": [
    "Reads the PDF using an appropriate library or tool",
    "Extracts text from all pages without missing any",
    "Saves extracted text to output.txt in a readable format"
  ]
}
```
There is no built-in eval runner — build your own harness. Evaluations are your source of truth for skill effectiveness.

### The two-Claude iteration loop

- **Claude A** — the "author": helps you design and refine the skill.
- **Claude B** — a fresh instance with the skill loaded, running real tasks.

Work a task with Claude A, extract the reusable pattern, ask A to generate the skill, review for concision, then test with B. When B struggles, bring the specific failure back to A ("B forgot to filter test accounts on the Q4 report — is the rule prominent enough?"). Repeat. You don't need a special "skill-writing skill"; Claude understands the format natively.

### Observe how Claude navigates

Watch for: unexpected read order (structure isn't intuitive), missed reference links (make them more explicit), overuse of one file (maybe promote it into SKILL.md), and never-accessed files (unnecessary or poorly signaled). Test across **Haiku, Sonnet, and Opus** if you'll deploy on multiple models — what suffices for Opus may need more detail for Haiku.

---

## 10. Distribution & Deployment

### Individual users
1. Download / author the skill folder.
2. Zip it if needed.
3. Upload via **Settings → Capabilities → Skills** in claude.ai, **or**
4. Place it in the Claude Code skills directory (`~/.claude/skills` globally, or `.claude/skills/` per project — restart the session once after install).

### Organization-wide
Admins can deploy skills workspace-wide, with automatic updates and centralized management. Admins must enable Skills org-wide before individual users can use them.

### Open standard
Agent Skills are published as an open standard, designed for portability across platforms that adopt the spec — the same folder can, in principle, run on other tools.

### Housekeeping
Every loaded skill consumes some context whether it helps or not. Audit your skill set regularly and remove anything you haven't triggered recently. A small, opinionated, version-controlled skill folder beats a large one.

---

## 11. Using Skills via the API & Managed Agents

### Messages API
Skills can be attached to Messages API requests. They require the Code Execution Tool beta, which provides the sandbox they run in. The `/v1/skills` endpoint gives programmatic control over custom skill creation, versioning, and management. You can also create, view, and upgrade versions via the Claude Console.

### Managed Agents
- Requests require the `managed-agents-2026-04-01` beta header (SDKs set it automatically).
- A **custom skill** is a directory (SKILL.md + supporting files) uploaded to your workspace as a zip or individual files. Creating it returns a `skill_*` ID.
- **Anthropic pre-built skills** (e.g. `xlsx`, `pptx`, `docx`, `pdf`) exist in every workspace — no upload step.
- Attach skills at agent creation. Each entry specifies:

| Field | Description |
|---|---|
| `type` | `anthropic` (pre-built) or `custom` (workspace-authored) |
| `skill_id` | Short name for Anthropic skills (`xlsx`); `skill_*` ID for custom |
| `version` | Custom skills only — pin a version or use `latest` |

- **Limit:** up to **20 skills per session**, counted across every agent in the session.

Example (CLI-style):
```yaml
name: Financial Analyst
model: claude-opus-4-8
system: You are a financial analysis agent.
skills:
  - type: anthropic
    skill_id: xlsx
  - type: custom
    skill_id: skill_abc123
    version: latest
```

When calling the Skills API directly (cURL/CLI), pass the `anthropic-beta: skills-2025-10-02` header explicitly; SDKs send it for you.

---

## 12. Tradeoffs — When to Use a Skill vs. Plain Code

A skill is not automatically the right tool. The honest test: **do you need extraction, or judgment?**

| Situation | Better choice |
|---|---|
| Fully deterministic, one-off ("convert this PDF to DOCX") | Plain script |
| No judgment needed, running at massive scale | Plain script (token cost matters) |
| Performance-critical (<100ms) | Plain script |
| Data formats vary run to run | **Skill** |
| Requires understanding / interpretation | **Skill** |
| Judgment calls ("is this contract clause risky?") | **Skill** |
| Multi-step reasoning with checkpoints | **Skill** |
| Recurring task you'd otherwise re-explain each time | **Skill** |

**Rule of thumb:** if you'd currently hire a human to *read and understand* something, a skill is likely worth it. If a `cron` job could do it unattended, write the script.

**Cost framing:** a skill invocation typically costs cents; if it replaces 30 minutes of human interpretation and runs weekly, it pays for itself almost immediately. But every installed skill also levies a standing "context tax" via its metadata — so breadth isn't free.

---

## 13. Error Handling Realities

The skill runtime is a pipeline: script stdout/stderr and exit codes flow back to Claude. What Claude can and can't see follows directly from that.

**Claude will typically surface:**
- Non-zero exit codes.
- Errors and tracebacks printed to stderr.
- Clear `Error:`-prefixed messages in stdout.
- Missing expected output files (if the workflow checks for them).

**Claude may miss:**
- Silent failures (no output, exit 0).
- Logically wrong output that *looks* correct.
- Partial success where some steps completed.
- Hangs / timeouts.

**Implication:** robustness is your responsibility, not the runtime's. Build defensively — validate inputs, check intermediate outputs, print status (not just errors), exit non-zero on failure, and validate output files before declaring success. See the plan-validate-execute pattern in §8.

---

## 14. Security Considerations

Skills execute code. That is the source of their power and their risk.

- **Treat unknown skill sources like unreviewed npm packages.** Read before you install.
- Prefer official and verified skills for anything touching sensitive data.
- Org admins should govern which skills are available workspace-wide rather than letting arbitrary skills run in production contexts.
- Be mindful that a skill with network access (on claude.ai) could exfiltrate data; the API's no-network sandbox is more restrictive by design.

---

## 15. Anti-Patterns to Avoid

- Vague or first-person `description`.
- `SKILL.md` over 500 lines instead of splitting into references.
- References nested more than one level deep.
- Windows-style backslash paths.
- Offering too many options ("use pypdf, or pdfplumber, or PyMuPDF, or…") — pick a default, give one escape hatch.
- Time-sensitive info in the main body (put deprecated guidance in a collapsed "Old patterns" section instead).
- Scripts that punt errors to Claude.
- Assuming packages are installed without listing them.
- Magic constants with no justification.

---

## 16. Pre-Ship Checklist

**Core quality**
- [ ] Description is specific and includes key trigger terms
- [ ] Description states both *what* it does and *when* to use it
- [ ] SKILL.md body under 500 lines
- [ ] Extra detail lives in separate, one-level-deep files
- [ ] No time-sensitive info (or quarantined in "Old patterns")
- [ ] Consistent terminology throughout
- [ ] Concrete, not abstract, examples
- [ ] Progressive disclosure used appropriately
- [ ] Workflows have clear, ordered steps

**Code & scripts**
- [ ] Scripts solve, don't punt
- [ ] Explicit, helpful error handling
- [ ] No voodoo constants
- [ ] Required packages listed and verified available on target surface
- [ ] Scripts documented; execute-vs-read intent stated
- [ ] All forward-slash paths
- [ ] Validation/verification steps for critical operations

**Testing**
- [ ] At least three evaluations created
- [ ] Tested with Haiku, Sonnet, and Opus (if multi-model)
- [ ] Tested against real usage scenarios
- [ ] Team feedback incorporated (if applicable)

---

## Appendix A — Minimal SKILL.md Template

```markdown
---
name: processing-pdfs
description: Extract text and tables from PDF files, fill forms, and merge
  documents. Use when working with PDF files or when the user mentions PDFs,
  forms, or document extraction.
---

# PDF Processing

## Quick start

Extract text with pdfplumber:

    import pdfplumber
    with pdfplumber.open("file.pdf") as pdf:
        text = pdf.pages[0].extract_text()

## Dependencies

Requires: pdfplumber. (On claude.ai: `pip install pdfplumber`. On the API,
ensure it is available in the code execution environment.)

## Advanced features

- **Form filling** — see FORMS.md
- **API reference** — see REFERENCE.md
- **Examples** — see EXAMPLES.md

## Utility scripts

Run `scripts/analyze_form.py input.pdf > fields.json` to extract form fields.
Run `scripts/validate_fields.py fields.json` before filling.
Run `scripts/fill_form.py input.pdf fields.json output.pdf` to produce output.
```

---

## Appendix B — Reference Links

- Introducing Agent Skills (announcement): https://claude.com/blog/skills
- Skills overview: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- Skill authoring best practices: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Skills for enterprise: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/enterprise
- Skills in the API: https://platform.claude.com/docs/en/build-with-claude/skills-guide
- Managed Agents — Skills: https://platform.claude.com/docs/en/managed-agents/skills
- Skills in Claude Code: https://code.claude.com/docs/en/skills
- Example skills (GitHub): https://github.com/anthropics/skills
- Open standard: https://agentskills.io

---

## Appendix C — Glossary

- **Skill** — a folder (SKILL.md + optional resources) that teaches Claude a task.
- **SKILL.md** — the required entry file: YAML frontmatter + markdown instructions.
- **Frontmatter** — the YAML block (`name`, `description`) at the top of SKILL.md.
- **Progressive disclosure** — loading only the metadata first, then the body, then resources on demand.
- **Degrees of freedom** — how prescriptive instructions are, matched to task fragility.
- **Reference file** — a bundled doc read into context only when linked-to.
- **Utility script** — a bundled script that's executed (not read) for deterministic work.
- **Plan-validate-execute** — produce a structured plan, validate it, then act.
- **Two-Claude loop** — authoring with one instance while testing with a fresh one.
- **Context tax** — the standing metadata cost of every installed skill.
- **MCP** — Model Context Protocol; exposes external tools/data (capability), complementary to skills (behavior).

---

*End of reference. This document reflects Anthropic's published guidance; verify specifics against the official docs before building production workflows, as details evolve.*
