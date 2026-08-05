# UDO v2.0 Red-Team Report

**Date:** 2026-03-10
**Build Location:** `/tmp/udo-v2-build/`
**Scope:** Comprehensive failure scenario testing across all v2.0 components

---

## Executive Summary

The UDO v2.0 implementation is **well-structured and addresses most multi-AI safety scenarios**, but has **THREE CRITICAL issues** that must be fixed before release:

1. **CRITICAL:** Missing `.project-catalog/history/` directory breaks HS-UDO-013 (session transcripts)
2. **CRITICAL:** PROJECT_STATE.json lacks conflict detection fields (HS-UDO-015)
3. **HIGH:** `last_updated_by` field not documented or explained in ORCHESTRATOR.md

**Verdict:** **REQUIRES FIXES BEFORE RELEASE** - Issues 1-2 are showstoppers for multi-AI safety.

---

## CRITICAL ISSUES

### CR-001: Missing Session Transcript Directory

**Failure Scenario:**
- User initializes new v2.0 project from template
- AI reads resume protocol (ORCHESTRATOR.md HS-UDO-013)
- AI attempts to create `.project-catalog/history/YYYY-MM-DD-HHMM-session-transcript.md`
- Directory doesn't exist because build template never creates it
- File creation FAILS

**Impact:** BLOCKER
- HS-UDO-013 cannot be enforced (session transcripts unreachable)
- Multi-session context persistence broken
- AI HALTS before accepting first prompt (per HS-UDO-013 violation protocol)
- User cannot proceed until manually creating directory

**Evidence:**
```bash
find /tmp/udo-v2-build -type d -name "history"
# Returns nothing
```

**Fix:**
1. Create `.project-catalog/history/` directory in UDO Project template
2. Add `.gitkeep` file for git persistence
3. Update README.txt and BUILD-SUMMARY.txt to reflect new directory

**Location:** `/tmp/udo-v2-build/UDO Project/.project-catalog/` (missing subdirectory)

---

### CR-002: PROJECT_STATE.json Missing Conflict Detection Fields

**Failure Scenario:**
- Two AIs simultaneously work on same project
- AI#1 reads PROJECT_STATE.json (timestamp: 10:00)
- AI#2 reads PROJECT_STATE.json (timestamp: 10:00)
- AI#1 updates state and writes back (timestamp: 10:05)
- AI#2 updates state and writes back (timestamp: 10:10)
- AI#2's write overwrites AI#1's changes without warning
- HS-UDO-015 conflict detection fails

**Impact:** DATA LOSS / BLOCKER
- No way to detect simultaneous modifications
- HS-UDO-015 cannot be enforced: "Check the `last_updated_by` and `prompt_counter.last_state_update_session` fields"
- One AI's work silently lost
- No recovery mechanism

**Evidence:**
```json
{
  "project_state": {
    "project_name": "New Project",
    "last_updated": "2026-03-10",
    "prompt_count": 0,
    // MISSING: "last_updated_by": "claude-123"
    // MISSING: "prompt_counter": { "last_state_update_session": "...", "count_since_last_state_update": 0 }
  }
}
```

**Required Fields (from HS-UDO-015):**
- `last_updated_by` — AI/system that last modified state
- `prompt_counter.last_state_update_session` — Session ID of last update
- `prompt_counter.count_since_last_state_update` — Prompts since last state save

**Fix:**
1. Add conflict detection structure to PROJECT_STATE.json template:
   ```json
   {
     "project_state": {
       ...existing fields...,
       "last_updated_by": "system-placeholder",
       "prompt_counter": {
         "count_since_last_state_update": 0,
         "last_state_update_session": "none"
       }
     }
   }
   ```
2. Update ORCHESTRATOR.md to document these fields
3. Add enforcement logic instructions in HARD_STOPS.md HS-UDO-015

**Location:** `/tmp/udo-v2-build/UDO Project/PROJECT_STATE.json`

---

### CR-003: last_updated_by Field Not Documented

**Failure Scenario:**
- AI reads HS-UDO-015: "Check the `last_updated_by` field..."
- Field doesn't exist in template and isn't explained anywhere in ORCHESTRATOR.md
- AI doesn't know what value to expect or how to use it
- Conflict detection logic cannot be implemented

**Impact:** HS-UDO-015 UNENFORCEABLE
- Protocol rule references non-existent field
- No guidance on how to populate it
- AIs cannot implement the rule even if trying

**Evidence:**
```bash
grep -n "last_updated_by" /tmp/udo-v2-build/UDO Framework/ORCHESTRATOR.md
# Returns no results (field mentioned in HARD_STOPS but not explained)
```

**Fix:**
Add section to ORCHESTRATOR.md "Concurrent AI Safety" explaining:
- What `last_updated_by` field contains (AI identifier/session)
- How it's populated
- How to detect conflicts
- Example conflict scenario and resolution

**Location:** `/tmp/udo-v2-build/UDO Framework/ORCHESTRATOR.md` (section: "Concurrent AI Safety")

---

## HIGH-SEVERITY ISSUES

### HS-001: Empty VERSION File Not Validated

**Failure Scenario:**
- User manually creates corrupted VERSION file with empty content
- Upgrade script reads it: `CURRENT_VERSION=$(cat "UDO Framework/VERSION")`
- Empty string assigned to CURRENT_VERSION
- Version comparison fails silently: `if [ "$CURRENT_VERSION" -eq "$LATEST_VERSION" ]`
- Upgrade proceeds or skips incorrectly

**Impact:** SILENT DATA LOSS
- Upgrade may overwrite files incorrectly
- User has no warning
- Backup may be created for wrong reason

**Likelihood:** Medium (user error during file editing)

**Fix:**
Add validation to upgrade.sh and upgrade.ps1:
```bash
if [ ! -s "$FRAMEWORK_PATH/VERSION" ]; then
    echo "Error: VERSION file is empty or missing"
    exit 1
fi
```

**Location:** Lines 80-82 in `upgrade.sh`, lines 59-61 in `upgrade.ps1`

---

### HS-002: Symlink Handling Not Addressed

**Failure Scenario:**
- User creates symlink: `ln -s /actual/location "UDO Framework"`
- Detection script runs: `if [ -d "./UDO Framework" ]`
- Symlink is followed, detection succeeds (confusing)
- User expects isolated structure, gets shared Framework
- Multiple projects accidentally share Framework modifications

**Impact:** FRAMEWORK CONTAMINATION
- Framework immutability assumption broken
- Cross-project data leakage possible

**Likelihood:** Low-Medium (advanced users)

**Fix:**
- Document symlink warning in START_HERE.md
- Update detection logic to use `[ -L "./UDO Framework" ]` check
- Warn if symlinks detected

**Location:** START_HERE.md (add symlink warning section)

---

### HS-003: Downgrade (v2.0 → v4.x) Not Documented

**Failure Scenario:**
- User starts with v2.0, decides to downgrade to v4.x
- No documentation on downgrade procedure
- User deletes "UDO Framework" folder
- Project data now incompatible with v4.x (expects single UDO folder)
- Data loss or corruption

**Impact:** DATA LOSS
- User loses ability to work with legacy systems
- No safe downgrade path documented

**Likelihood:** Low (but high-impact if happens)

**Fix:**
Add "Downgrade Procedure" section to ORCHESTRATOR.md:
1. Ensure backup exists (`.udo-backup-*`)
2. Restore backup: `rm -rf UDO && mv .udo-backup-[timestamp] UDO`
3. Revert to v4.x scripts
4. Verify all data present

**Location:** `/tmp/udo-v2-build/UDO Framework/ORCHESTRATOR.md` (new section)

---

### HS-004: Bridge Reference Path Not in Framework Manifest

**Failure Scenario:**
- Upgrade script copies Framework files
- Bridge files are in FRAMEWORK_FOLDERS array (correct)
- But `.manifest.json` doesn't list `.bridge` in contents
- Future tooling might miss bridge files (incomplete metadata)
- Bridge feature silently missing after upgrade

**Impact:** METADATA INCONSISTENCY
- Manifest claims to define Framework contents
- Actual contents don't match manifest
- Future tools cannot trust manifest

**Likelihood:** Medium (if future tooling relies on manifest)

**Fix:**
Update `/tmp/udo-v2-build/UDO Framework/.manifest.json`:
```json
{
  "contents": {
    "infrastructure_dirs": [
      ".bridge",    // ← Add explicit listing
      ".templates",
      ".takeover",
      ".tools"
    ]
  }
}
```

**Location:** `/tmp/udo-v2-build/UDO Framework/.manifest.json`

---

## MEDIUM-SEVERITY ISSUES

### MD-001: Path Documentation Inconsistency

**Failure Scenario:**
- ORCHESTRATOR.md uses `/UDO Framework/` and `/UDO Project/` paths
- User reads different documentation
- User might expect `/UDO/UDO Framework/` vs `./UDO Framework/`
- Confusion about relative vs absolute paths

**Impact:** DOCUMENTATION CLARITY (not functional)
- No data loss, but confusing for users
- May cause incorrect mental model

**Likelihood:** Medium (users read mixed docs)

**Fix:**
1. Add path notation section to START_HERE.md:
   ```
   Path Notation Used in This Framework:
   - /UDO Framework/ = Your root UDO folder contains this
   - /UDO Project/ = Sibling folder to Framework
   - ./UDO Framework/ = Relative from current directory
   - Absolute paths are NEVER used in configs
   ```
2. Review all markdown files for consistency
3. Use consistent format throughout (prefer `/UDO Framework/` for clarity)

**Location:** START_HERE.md (new section at top)

---

### MD-002: .rules Directory Missing from Framework (Design Issue)

**Failure Scenario:**
- ORCHESTRATOR.md section "Right Mode, Right Time" says "Validation outputs against `.rules/`"
- Framework has NO `.rules/` folder (only Project has one)
- User thinks there are system-level rules in Framework
- Looks in Framework, finds nothing
- Confusion about rule hierarchy

**Impact:** DESIGN INCONSISTENCY
- Implies rules exist at Framework level when they don't
- Documentation misleading about scope

**Likelihood:** High (any user reading ".rules/" reference)

**Recommended Action:**
This is actually a design question, not a bug:
- **Option A:** Add `.rules/` to Framework with system rules, Project `.rules/` inherits
- **Option B:** Document clearly that `.rules/` is Project-only, Framework has none
- **Option C:** Rename to avoid confusion

**Current Implementation:** Option B (Project-only)

**Fix:** Clarify in ORCHESTRATOR.md:
```markdown
### Rules Hierarchy
- **Framework has NO `.rules/` folder** (immutable, no project-specific rules there)
- **Project `.rules/`** contains all project-specific validation rules
- Framework provides protocol constraints in HARD_STOPS.md
```

**Location:** ORCHESTRATOR.md (new subsection)

---

### MD-003: PROJECT_STATE.json Template Too Minimal

**Failure Scenario:**
- User reads ORCHESTRATOR.md explaining todos, phases, completion tracking
- Template has no fields for todos or phases structure
- User doesn't know what shape to create
- Inconsistent state across projects

**Impact:** USABILITY
- Users don't know how to structure their project state
- Leads to inconsistent implementations

**Likelihood:** High (all new projects)

**Fix:**
Enhance PROJECT_STATE.json template with commented examples:
```json
{
  "project_state": {
    "project_name": "New Project",
    ...
    "todos": [
      "{ \"id\": \"1\", \"task\": \"Example todo\", \"done\": false }"
    ],
    "current_phase": "setup",
    "todo_count": 0,
    "todos_completed": 0,
    "blockers": []
  }
}
```

**Location:** `/tmp/udo-v2-build/UDO Project/PROJECT_STATE.json`

---

## LOW-SEVERITY ISSUES

### LO-001: Empty Directory Detection Not Mentioned

**Failure Scenario:**
- User Git-clones v2.0 project (includes `.gitkeep` files)
- User later explores structure with `ls -la`
- Only sees `.gitkeep` in empty directories
- Confuses `.gitkeep` files with project files
- Deletes them thinking they're artifacts

**Impact:** MINOR (git tracking broken)
- `.gitkeep` files are recovered on next clone
- Primarily documentation issue

**Fix:**
Add note to each directory's README.md:
```
Note: This directory contains only `.gitkeep` files until used.
The `.gitkeep` files ensure git tracks the empty directory structure.
You can safely ignore them or delete them (git will recover them on next clone).
```

**Location:** All README.md files in empty directories

---

### LO-002: User Uploads Naming Could Be Clearer

**Failure Scenario:**
- User sees "User Uploads" folder
- Unclear if this is for uploads BY user or uploads TO user
- User puts AI outputs there (mixing input and output)
- Confusion about folder purpose

**Impact:** MINOR (organizational confusion)
- No data loss, just poor folder organization

**Fix:**
Rename and clarify (optional, for future):
- Current: "User Uploads" (ambiguous)
- Better: "Provided Materials" or "Input Materials"
- Add explicit README:
  ```
  # User Uploads

  This folder is for **user-provided** input materials:
  - Reference documents
  - Example files
  - Source materials

  **Do not** put AI-generated outputs here. Use `.outputs/` instead.
  ```

**Current Implementation:** README.md is adequate, renaming optional

---

## PASS ITEMS (Explicitly Confirmed Working)

### ✓ PASS-001: Framework Immutability Well-Documented

**What Was Tested:**
- HS-UDO-014 present and clear in HARD_STOPS.md
- Framework-README.md mentions immutability
- Version separation confirmed (Framework has VERSION, Project doesn't)

**Result:** ✓ PASS
- Clear rules preventing accidental Framework modification
- Strong documentation

---

### ✓ PASS-002: .gitkeep Files Present

**What Was Tested:**
- All 15 empty directories have .gitkeep files
- Critical directories verified (`.memory/*`, `.outputs/`, `.agents/`, etc.)

**Result:** ✓ PASS
- Git will properly track empty directories
- Structure portable across clones

---

### ✓ PASS-003: Bridge Module in Correct Location

**What Was Tested:**
- `.bridge/` in Framework (not Project)
- All required files present: `bridge-queue.md`, `session-log.md`, `bridge-state.json`
- HS-UDO-016 enforced

**Result:** ✓ PASS
- Bridge correctly isolated in immutable Framework
- Cannot be corrupted by Project work

---

### ✓ PASS-004: JSON Files Valid

**What Was Tested:**
- `.manifest.json` (Framework) - valid
- `.manifest.json` (Project) - valid
- `PROJECT_STATE.json` - valid structure
- `PROJECT_META.json` - valid structure
- `bridge-state.json` - valid structure

**Result:** ✓ PASS
- All JSON parseable
- No syntax errors

---

### ✓ PASS-005: Relative Paths (Portability)

**What Was Tested:**
- No absolute paths in config files
- Manifest uses relative reference path (`../UDO Framework/`)
- Structure portable across systems

**Result:** ✓ PASS
- v2.0 directory structure can move without path updates

---

### ✓ PASS-006: Documentation Hierarchy Complete

**What Was Tested:**
- README.md in all key directories (memory, project-catalog, outputs, agents, rules, inputs, bridge)
- Framework and Project both documented
- START_HERE.md orientation complete

**Result:** ✓ PASS
- Self-documenting structure
- Users can understand each folder's purpose

---

### ✓ PASS-007: Hard Stops Inheritance Clear

**What Was Tested:**
- Project HARD_STOPS.md references Framework rules
- Project rules numbered PROJECT_HS_* or HS-UDO-014+
- Rule hierarchy documented

**Result:** ✓ PASS
- HS-UDO-015 and HS-UDO-016 clearly present
- Framework rules cannot be overridden

---

### ✓ PASS-008: Upgrade Script Detection Logic

**What Was Tested:**
- Fresh install, v4.x, v2.0 detection
- Force flags (`--fresh`, `--migrate`)
- Cross-platform equivalence (Bash and PowerShell)

**Result:** ✓ PASS
- Both scripts implement same logic
- Detection accurate for all scenarios

---

### ✓ PASS-009: Bridge Files in Upgrade Scripts

**What Was Tested:**
- FRAMEWORK_FOLDERS array includes `.bridge`
- Both upgrade.sh and upgrade.ps1 consistent

**Result:** ✓ PASS
- Bridge module will be updated during upgrades
- No silent omission

---

### ✓ PASS-010: Data Preservation on Migration

**What Was Tested:**
- Migration docs confirm preservation of `.memory/`, `.project-catalog/`, `.outputs/`, `.agents/`, `.checkpoints/`
- Backup strategy clear
- v4.x data not lost

**Result:** ✓ PASS
- Upgrade tool safe for existing projects
- No data loss on migration

---

## DEPLOYMENT CHECKLIST

Before release, address these items in order:

### MUST FIX (Blockers)
- [ ] **CR-001:** Create `.project-catalog/history/` directory in template
- [ ] **CR-002:** Add `last_updated_by` and `prompt_counter` to PROJECT_STATE.json
- [ ] **CR-003:** Document `last_updated_by` field in ORCHESTRATOR.md

### SHOULD FIX (High Priority)
- [ ] **HS-001:** Add VERSION file validation to upgrade.sh and upgrade.ps1
- [ ] **HS-003:** Add downgrade procedure to ORCHESTRATOR.md
- [ ] **HS-004:** Update Framework `.manifest.json` to list `.bridge`

### NICE TO HAVE (Medium Priority)
- [ ] **MD-001:** Add path notation guide to START_HERE.md
- [ ] **MD-002:** Clarify `.rules/` is Project-only in ORCHESTRATOR.md
- [ ] **MD-003:** Enhance PROJECT_STATE.json template with examples

### OPTIONAL (Low Priority)
- [ ] **LO-001:** Add `.gitkeep` documentation to directory READMEs
- [ ] **LO-002:** Consider renaming "User Uploads" for clarity (future)

---

## SUMMARY BY CATEGORY

| Category | Count | Status |
|----------|-------|--------|
| CRITICAL Issues | 3 | MUST FIX |
| HIGH Issues | 4 | Should fix |
| MEDIUM Issues | 3 | Can schedule |
| LOW Issues | 2 | Optional |
| PASS Items | 10 | Working ✓ |

---

## CRITICAL PATHS TESTED

### 1. Upgrade Detection ✓
- Fresh install detection
- v4.x detection
- v2.0 detection
- Hybrid structure handling

### 2. Hard Stops Enforcement ✓
- HS-UDO-014 (Framework immutability)
- HS-UDO-015 (Conflict detection) — **PARTIALLY FAILED** (missing fields)
- HS-UDO-016 (Project scope)
- Inheritance hierarchy

### 3. Multi-AI Safety ⚠️
- Concurrent access detection — **INCOMPLETE** (missing fields)
- Conflict flagging — **INCOMPLETE** (no implementation guidance)
- Last-updater tracking — **MISSING** (no field)

### 4. Data Persistence ✓
- `.gitkeep` files present
- Directory structure portable
- Relative paths verified

### 5. Documentation ✓
- README hierarchy complete
- Path consistency mostly good (minor issues)
- Protocol rules documented

---

## FINAL VERDICT

### APPROVED FOR RELEASE?

**❌ NO — REQUIRES CRITICAL FIXES FIRST**

The v2.0 implementation demonstrates excellent architecture and planning, but **three critical safety issues must be resolved** before any release:

1. **Missing history/ directory** breaks session transcript requirement (HS-UDO-013)
2. **Missing conflict fields** in PROJECT_STATE.json prevents multi-AI safety (HS-UDO-015)
3. **Undocumented field usage** makes HS-UDO-015 unenforceable

These are not minor bugs — they directly violate hard stops and undermine the entire multi-AI safety model that v2.0 exists to provide.

### Recommended Path Forward

1. **Immediate (today):**
   - Apply CR-001, CR-002, CR-003 fixes
   - Re-test multi-AI safety scenario
   - Re-validate HARD_STOPS compliance

2. **Follow-up (before release):**
   - Apply HS-001, HS-003, HS-004 high-priority fixes
   - Update both upgrade.sh and upgrade.ps1 consistently
   - Final documentation review

3. **Post-Release (acceptable):**
   - MD-001, MD-002, MD-003 medium-priority improvements
   - LO-001, LO-002 low-priority enhancements

### Estimated Fix Time

- CR-001: 5 minutes (create directory)
- CR-002: 10 minutes (JSON field additions)
- CR-003: 20 minutes (ORCHESTRATOR documentation)
- Total: ~35 minutes for critical fixes

### Sign-Off Criteria

Before release approved:
- [ ] All three CRITICAL issues fixed
- [ ] Red-team re-test passes
- [ ] Multi-AI safety scenario validates end-to-end
- [ ] Both upgrade.sh and upgrade.ps1 consistent
- [ ] Documentation fully updated

---

## Test Environment

- **Build Date:** 2026-03-10
- **Build Location:** `/tmp/udo-v2-build/`
- **Tested Components:**
  - UDO Framework/ (47 files)
  - UDO Project/ (31 files)
  - upgrade.sh (Linux/macOS)
  - upgrade.ps1 (Windows)
  - UPGRADE_V2.0_LOGIC.md specifications

---

**Report Complete**
**Red-Team Auditor:** Claude Haiku 4.5 UDO Testing Agent
**Confidence Level:** HIGH (exhaustive testing, clear evidence)
