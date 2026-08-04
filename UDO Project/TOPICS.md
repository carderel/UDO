# Topic Registry
One row per parallel workstream. PROJECT_STATE holds the project; this file holds the portfolio.
Slugs are immutable kebab-case and thread through EVERYTHING: .memory/working/<slug>-*.md, .outputs/<slug>/, checkpoint names, session-log tags (#<slug>).

| Slug | Title | Status | Owner | Opened | Last touched | Next action |
|------|-------|--------|-------|--------|--------------|-------------|

Lifecycle: INTAKE -> ACTIVE -> AWAITING-DATA -> REPORTED. Terminal: PARKED / KILLED / DONE.
Rules: a topic's status changes ONLY here (single source of truth). Session logs reference slugs, never restate status. KILLED/PARKED topics keep their row (with reason) so work is never re-derived by inference.

## Authoritative Sources
Ground-truth assets this project depends on (in this project OR sibling projects). Check here before deriving data from scratch.

| Source | Location | Authoritative for | Vintage | Access mode | Last verified |
|--------|----------|-------------------|---------|-------------|---------------|

Resume rule: any pipeline touching a source whose Last verified predates this session gets re-verified before its output is trusted (HS-EVID-001).
