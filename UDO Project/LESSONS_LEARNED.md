# Lessons Learned

Document lessons, insights, and patterns discovered during project execution.

## Purpose

This file captures:
- Successful patterns and techniques
- Mistakes and how to avoid them
- Framework insights
- Domain-specific learnings
- Process improvements

## Format

```
## Session {Date}: [Lesson Title]

**Context**: Brief description of the situation

**Learning**: What was discovered or realized

**Action**: How this changed approach going forward

**Tags**: [category, type, confidence-level]
```

## Template Structure

### Example Entry

```
## Session 2026-03-10: Protocol Compliance Matters

**Context**: Session failed to follow canonical memory protocol

**Learning**: "The protocol IS the product" - cutting corners on process causes failures downstream

**Action**: All future sessions require explicit protocol checklist before handoff

**Tags**: [process, critical, high-confidence]
```

## Organization

Lessons are organized chronologically. Key patterns:
- Successes/failures with specific patterns
- Framework discoveries
- Domain insights
- Process improvements

## How This File Works

**Anti-recurrence rule:** any lesson that recurs twice is promoted immediately to a PROJECT_HS hard stop in HARD_STOPS.md plus an anti-recurrence memory in .memory/canonical/. A recorded lesson alone does not stop recurrence.

## Canonical Memory Link

Important lessons should be copied to `.memory/canonical/` for permanent retention across sessions.

## Usage

- Review before starting new work
- Reference when making decisions
- Consider when improving processes
- Share with incoming agents at handoff

## See Also

- `.memory/canonical/` - Permanent lessons
- PROJECT_STATE.json - Current project status
- .project-catalog/decisions/ - Specific decision rationale
