# PROJECT_STATE Schema (v2.2)

PROJECT_STATE.json is the single source of truth for a project's execution state, tracking progress, risks, and health across UDO phases.

## Element Shapes

```json
todos[] item:         {"id": "T-001", "task": "text", "status": "pending|in_progress|done", "priority": "high|normal|low"}
deferred_debt[] item: {"id": "D-001", "item": "text", "owner": "name", "deferred": "YYYY-MM-DD", "resolve_by": "YYYY-MM-DD or next-session", "status": "open|cleared|waived", "waive_reason": null}
checkpoints[] item:   {"name": "text", "timestamp": "YYYY-MM-DD", "trigger": "phase-boundary|pre-risk|session-end|manual", "description": "text"}
scope_locked:         boolean. Build/spec phases MUST NOT begin while false. Set true only on explicit user confirmation of scope.
```

## Field Descriptions

- **project_name**: Human-readable name for the project.
- **project_id**: Unique identifier for tracking and referencing the project.
- **goal**: The stated objective or deliverable the project is working toward.
- **status**: Current state of the project (initialized, active, paused, completed, halted).
- **udo_version**: UDO framework version this project was initialized with.
- **created**: ISO date the project was created.
- **last_updated**: ISO date the project state was last updated.
- **last_updated_by**: Name or identifier of the agent/user who last modified state.
- **current_phase**: Current phase in the UDO lifecycle (setup, planning, development, testing, deployment, closure).
- **scope_locked**: Boolean flag that prevents build/spec phases from beginning unless true; requires explicit user confirmation.
- **completion_percentage**: Numeric estimate of overall project completion.
- **owner**: Name or identifier of the project owner.
- **active_agent**: Current agent managing the project, or null if inactive.
- **session_count**: Total number of sessions executed on this project.
- **prompt_count**: Total number of prompts issued across all sessions.
- **prompt_counter**: Tracks prompts since last state update (count_since_last_state_update) and the session where it last reset (last_state_update_session).
- **todos**: Array of structured tasks with id, task text, status, and priority; supports granular progress tracking.
- **deferred_debt**: Array of deferred work items with owner, due date, and resolution status; prevents work from slipping into oblivion.
- **checkpoints**: Array of significant events or milestones recorded with timestamp, trigger type, and description.
- **auto_checkpoint**: Configuration for automatic checkpointing (enabled flag, trigger type, and timestamp of last auto-checkpoint).
- **circuit_breaker**: Flags when the project has halted due to risk (triggered boolean, reason, timestamp).
- **context_health**: Estimated token usage and timestamp of the last archive; helps prevent context overflow.
- **notes**: Freeform notes about the current state or outstanding concerns.

## Session Log Requirement

Completed work is recorded in session logs (`.project-catalog/sessions/`), NOT appended to PROJECT_STATE. This prevents the bloat and corruption seen in the 2026-03 incident and keeps state focused on actionable risk and progress.
