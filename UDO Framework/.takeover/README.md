# .takeover/

## What It Is

This folder contains the Takeover Module: a set of auditor agent templates for systematically reviewing an existing codebase or project before doing further work on it.

## What It Does

When you point AI at an existing codebase or project, the templates in `agent-templates/` describe five specialized auditor roles AI can adopt (or spawn as subagents, where delegation is available) to investigate it:

- Structure
- Documentation
- Code quality
- Security
- Test coverage

Instead of AI making assumptions about unfamiliar code, these templates push toward systematic investigation with concrete scope, methods, and evidence expectations per role.

## Why It's Included

**Problem:** AI dropped into an existing project makes assumptions. It misses critical context. It breaks things because it doesn't understand dependencies. It gives confident but wrong answers about code it hasn't actually analyzed.

**Solution:** Use these auditor templates to structure the review, one per area of concern, before taking action on unfamiliar code.

## Structure

```
.takeover/
├── agent-templates/            # Auditor agent definitions
│   ├── structure-auditor.md
│   ├── documentation-auditor.md
│   ├── code-quality-auditor.md
│   ├── security-auditor.md
│   └── test-auditor.md
└── README.md                   # This file
```

There is no separate orchestrator file, discovery config, or scope config for this module; the templates below are the entire module. There is no `audits/` or `evidence/` folder either; write any output the templates produce to the usual project locations (`.outputs/`, `.memory/canonical/`, or `.project-catalog/decisions/`, as appropriate).

## Auditor Roles

| Auditor | Focus |
|---------|-------|
| Structure | Architecture, organization, patterns |
| Documentation | README, comments, docs quality |
| Code Quality | Standards, complexity, maintainability |
| Security | Vulnerabilities, auth, data handling |
| Test | Coverage, test quality, CI/CD |

## Using a Template

Each auditor template in `agent-templates/` defines:
- **Scope** - what to examine
- **Methods** - how to investigate
- **Outputs** - what to produce
- **Evidence** - what to collect

Open the relevant template, adopt (or delegate to) that role, and follow its scope and methods. Save findings using the project's normal memory and decision-log locations rather than a dedicated takeover output folder, since none exists.

## When to Use Takeover

- Inheriting an existing codebase
- Joining a project mid-stream
- Auditing unfamiliar code
- Due diligence on acquisitions
- Security/quality assessments

## Integration with UDO

After a takeover review:
- Findings become canonical facts in `.memory/canonical/`
- Issues become todos in `PROJECT_STATE.json`
- Lessons go to `LESSONS_LEARNED.md`
