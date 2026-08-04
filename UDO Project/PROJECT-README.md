# UDO Project v2.0

This is a project using the Universal Dynamic Orchestrator (UDO) framework v2.0.

## Quick Navigation

1. **First time?** Start with PROJECT_STATE.json and this README
2. **Working on the project?** Check `.project-catalog/sessions/` for recent work
3. **Need reference material?** See the `../UDO Framework/` directory
4. **Starting a session?** Read `../UDO Framework/START_HERE.md` and then this file

## Project Structure

### Core Configuration Files
- **PROJECT_STATE.json** - Current project status and metadata
- **PROJECT_META.json** - Project identity and configuration
- **CAPABILITIES.json** - Feature matrix and integrations
- **HARD_STOPS.md** - Project-specific boundaries (extends framework rules)
- **NON_GOALS.md** - What this project explicitly does NOT do
- **LESSONS_LEARNED.md** - Insights and patterns from project work

### Memory Management (`.memory/`)
Three-level memory system:
- **canonical/** - Permanent, authoritative knowledge
- **working/** - Session-scoped working context
- **disposable/** - Ephemeral prompt-level memory

### Project Operations (`.project-catalog/`)
Central record-keeping:
- **sessions/** - Complete logs of all work
- **decisions/** - Decision records with rationale
- **backups/** - Full state snapshots
- **checkpoints/** - Recovery points

### Project Work Areas
- **.outputs/** - Generated deliverables
- **.inputs/** - Source materials and requirements
- **.checkpoints/** - State snapshots for recovery
- **.agents/** - External agent definitions
- **.rules/** - Project-specific rules
- **User Uploads/** - User-provided materials

## Key Principles

1. **Framework Inheritance** - This project uses and extends UDO Framework, but does not modify it
2. **Protocol is the Product** - Session management protocol is core to reliability
3. **Immutable Framework** - Framework in `../UDO Framework/` is read-only
4. **Mutable Project** - This project folder changes as work progresses

## Session Workflow

### Starting Work
1. Read `../UDO Framework/START_HERE.md`
2. Read the framework `../UDO Framework/ORCHESTRATOR.md` as reference
3. Review `PROJECT_STATE.json` for current status
4. Check `.project-catalog/sessions/` for recent work context
5. Verify compliance with HARD_STOPS.md (both framework and project)

### During Work
- Document progress in notes
- Create `.checkpoints/` snapshots when reaching milestones
- Update PROJECT_STATE.json regularly (per HS-UDO-008: every 5 prompts)
- Reference all decisions in work logs

### Ending a Session (Handoff)
- Create session log in `.project-catalog/sessions/`
- Update PROJECT_STATE.json with final status
- Create backup in `.project-catalog/backups/`
- Capture learnings in LESSONS_LEARNED.md or `.memory/canonical/`
- Verify all hard stops compliance

## Commands

See `../UDO Framework/COMMANDS.md` for available operations:
- `bu` - Backup (full mid-session save)
- `h` - Handoff (session end protocol)
- `r` - Resume (continue from checkpoint)

## Important Files & Directories

| Path | Purpose |
|------|---------|
| `PROJECT_STATE.json` | Current status |
| `.memory/canonical/` | Permanent knowledge |
| `.project-catalog/sessions/` | Work history |
| `.project-catalog/decisions/` | Decision records |
| `.outputs/` | Deliverables |
| `../UDO Framework/` | Immutable framework |

## Framework Reference

For complete specification, see:
- `../UDO Framework/ORCHESTRATOR.md` - Full system specification
- `../UDO Framework/HARD_STOPS.md` - Mandatory rules. See that file for the authoritative list (some IDs are retired tombstones).
- `../UDO Framework/COMMANDS.md` - Available operations
- `../UDO Framework/README.md` - Framework overview

## Project Information

- **UDO Version**: 2.0
- **Framework Version**: 2.0
- **Created**: 2026-03-10
- **Owner**: [Set in PROJECT_META.json]
- **Status**: [See PROJECT_STATE.json]

## Getting Help

1. **Framework questions** → See `../UDO Framework/ORCHESTRATOR.md`
2. **Protocol questions** → See `../UDO Framework/HARD_STOPS.md`
3. **Project history** → See `.project-catalog/`
4. **Recent work** → See `.project-catalog/sessions/`
5. **Lessons learned** → See `LESSONS_LEARNED.md`

---

**Last Updated**: 2026-03-10
**Next Review**: Set after first session
