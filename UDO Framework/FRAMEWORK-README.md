# UDO Framework

The UDO Framework is the immutable core of the Universal Dynamic Orchestrator. This folder contains all system protocols, standards, and infrastructure required for proper AI session management.

## Framework Contents

### Core Documentation
- **ORCHESTRATOR.md** - Main framework specification and session management protocol
- **START_HERE.md** - Entry point for new users and agents
- **COMMANDS.md** - Available framework commands and their functions
- **HARD_STOPS.md** - Critical protocol rules and boundaries. See HARD_STOPS.md for the authoritative list (some IDs are retired tombstones).

### Protocol Files
- **REASONING_CONTRACT.md** - Standards for agent reasoning and decision-making
- **DEVILS_ADVOCATE.md** - Critical challenge protocol
- **AUDIENCE_ANTICIPATION.md** - Communication standards
- **EVIDENCE_PROTOCOL.md** - Standards for evidence-based claims
- **TEACH_BACK_PROTOCOL.md** - Knowledge transfer standards
- **OVERSIGHT_DASHBOARD.md** - Monitoring and visibility standards

### Handoff & Operations
- **HANDOFF_PROMPT.md** - Template for agent handoff prompts

### Infrastructure
- **.templates/** - Reusable templates for agents, projects, and components
- **.takeover/** - Agent takeover templates and procedures
- **.tools/** - Framework tools and utilities

## Framework Immutability

**This framework folder is read-only and immutable.** Projects reference and inherit from it but do not modify it. All project-specific customizations belong in the UDO Project folder, not here.

Framework updates are coordinated at the repository level and distributed via version management.

## Version
See VERSION file for current framework version.

## Usage

Each project that uses UDO includes a reference to this framework. The framework provides:
1. Standardized session management
2. Protocol definitions for agent behavior
3. Reusable infrastructure and templates
4. Standards for quality and communication

Projects inherit from the framework but maintain their own state, configuration, and customizations in the UDO Project folder.
