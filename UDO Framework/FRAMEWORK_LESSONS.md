# Framework Lessons

Lessons about UDO itself. Ships with the framework; project lessons go in `UDO Project/LESSONS_LEARNED.md`.

---

### LL-001: Protocol compliance is not optional, even when "busy"
**Date:** 2026-03-03
**Triggered by:** 2026-02-23 session created extensive work (docs, repos, upgrade tools) but skipped ALL UDO protocol: no session log, no PROJECT_STATE.json update, no checkpoints, handoff saved to wrong location.
**Root cause:** The AI prioritized visible output over framework compliance. The handoff *existed* but was in `User Provided Files/` instead of `.project-catalog/sessions/`, making it invisible to the resume protocol.
**Impact:** Next session (2026-03-03) started blind: no goal, no context, no history. Required user to manually provide the handoff file. The entire point of UDO (seamless session continuity) was defeated.
**Fix:** Added HS-UDO-004 through HS-UDO-007 to HARD_STOPS.md. Added mandatory Session End Verification checklist.
**Lesson:** Doing great work means nothing if the next AI can't find it. The protocol IS the product.

### LL-002: Handoff files outside .project-catalog/ are invisible
**Date:** 2026-03-03
**Triggered by:** Handoff from 2026-02-23 was saved to `User Provided Files/HANDOFF_2026-02-23.md`
**Lesson:** The resume protocol only checks `.project-catalog/sessions/`. Anything stored elsewhere might as well not exist. Always use the designated paths.
