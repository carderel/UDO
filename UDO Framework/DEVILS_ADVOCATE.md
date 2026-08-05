# Devil's Advocate Protocol

A critical review pass that runs after deliverables are complete but before final handoff to the user. The purpose is to surface gaps, weaknesses, and alternative interpretations that the user should be aware of.

**This is not about being negative; it's about being complete.**

---

## When to Run Devil's Advocate

**MANDATORY before:**
- Delivering recommendations or strategy
- Presenting analysis or research findings
- Submitting decision support documents
- Any output where the user will take action based on it

**OPTIONAL for:**
- Creative content (unless accuracy matters)
- Simple formatting tasks
- Direct transcription or summarization

**Invoke with:** `Devil's advocate` or `DA check` or `Challenge this`

---

## The Devil's Advocate Mindset

When running this protocol, adopt these perspectives:

### The Skeptic
"What evidence is actually weak here? What are we treating as proven that isn't?"

### The Contrarian  
"What's the strongest argument AGAINST this conclusion? Who would disagree and why?"

### The Edge Case Hunter
"What scenarios would break this? What assumptions need to hold for this to work?"

### The Missing Piece Detector
"What did we NOT look at? What questions didn't we ask?"

### The Stakeholder Simulator
"Who else is affected? Whose perspective is missing?"

---

## Devil's Advocate Checklist

Run through each category and document findings:

### 1. Evidence Gaps
- [ ] Are there claims without strong evidence?
- [ ] Is any evidence outdated or potentially stale?
- [ ] Are we relying on single sources where multiple would be better?
- [ ] What data would we WANT but don't have?

### 2. Logic Gaps
- [ ] Are there leaps in reasoning?
- [ ] Do the conclusions actually follow from the evidence?
- [ ] Are there logical fallacies present?
- [ ] Is correlation being treated as causation?

### 3. Alternative Interpretations
- [ ] Could the same evidence support a different conclusion?
- [ ] What's the strongest counter-argument?
- [ ] Are there competing frameworks that would analyze this differently?

### 4. Assumption Vulnerabilities
- [ ] What assumptions are we making?
- [ ] Which assumptions, if wrong, would invalidate the conclusion?
- [ ] Are any assumptions untested or unverified?

### 5. Scope Blindness
- [ ] What perspectives are missing?
- [ ] What time horizons weren't considered?
- [ ] What second-order effects weren't explored?
- [ ] Who/what might be affected that we didn't consider?

### 6. Confidence Calibration
- [ ] Is the stated confidence level appropriate?
- [ ] Are we more certain than the evidence warrants?
- [ ] Are uncertainties clearly communicated?

---

## Devil's Advocate Report Format

```markdown
# Devil's Advocate Review

**Document Reviewed:** [Name/description]
**Review Date:** [YYYY-MM-DD]
**Reviewer Mode:** Devil's Advocate Protocol

---

## Summary Verdict

[One of:]
- ✅ SOLID - Minor points only, ready for delivery
- ⚠️ REVIEW RECOMMENDED - Notable gaps the user should consider
- 🛑 SIGNIFICANT CONCERNS - Major issues that may affect decisions

---

## Evidence Challenges

### [Challenge 1 Title]
**The claim:** [What's being stated]
**The concern:** [Why it might be weak]
**What would strengthen it:** [What evidence would help]
**Severity:** [Low / Medium / High]

[Repeat as needed]

---

## Logic Challenges

### [Challenge 1 Title]
**The reasoning:** [The logical chain being used]
**The concern:** [Where it might break down]
**Alternative interpretation:** [Different way to read the evidence]
**Severity:** [Low / Medium / High]

[Repeat as needed]

---

## Missing Perspectives

- **[Perspective 1]:** [What viewpoint wasn't considered and why it might matter]
- **[Perspective 2]:** [...]

---

## Key Assumptions at Risk

| Assumption | If Wrong, Then... | Likelihood Wrong | Impact |
|------------|-------------------|------------------|--------|
| [Assumption] | [Consequence] | [Low/Med/High] | [Low/Med/High] |

---

## Questions the User Should Consider

1. [Question that might reveal context we don't have]
2. [Question about user's specific situation]
3. [Question about priorities or tradeoffs]

---

## Recommendation

[What, if anything, should be done before delivering this output?]

---

## Note to User

These challenges are not assertions that the output is wrong. They are areas where:
- Additional context you have might resolve the concern
- You may want to verify before acting
- Limitations should be kept in mind

Your situational knowledge may make some of these moot. Review and discard as appropriate.
```

---

## How to Use Devil's Advocate Findings

### For the AI
1. Run DA protocol after output is "complete"
2. Generate the DA report
3. Present BOTH the output AND the DA report to user
4. Do NOT automatically revise based on DA findings (that's the user's call)

### For the User
1. Review the output
2. Review the DA challenges
3. Decide which challenges:
   - Are valid and need addressing
   - Are moot given your context
   - Are acceptable risks
4. Either approve as-is or request revisions

---

## Integration with Dual-Mode System

```
RC Mode (Analysis)
       ↓
Handoff Packet
       ↓
Persona Mode (Writing)
       ↓
Draft Output
       ↓
Devil's Advocate Review  ← YOU ARE HERE
       ↓
[Output + DA Report] → User
       ↓
User Decision: Approve / Revise / Investigate
```

The Devil's Advocate runs AFTER persona mode creates the output but BEFORE delivery to user.

---

## Devil's Advocate is NOT

- **Not a blocker:** It surfaces concerns, it doesn't veto output
- **Not a rewrite:** It doesn't change the output, it annotates it
- **Not adversarial:** it's collaborative, helping the user see the full picture
- **Not required to find problems:** "No significant concerns" is a valid finding

---

## Quick DA (Abbreviated Version)

For lower-stakes outputs, use the quick version:

```markdown
## Quick Devil's Advocate

**Strongest counter-argument:** [One sentence]
**Weakest evidence point:** [One sentence]  
**Key assumption to verify:** [One sentence]
**Missing perspective:** [One sentence]

**Verdict:** ✅ / ⚠️ / 🛑
```

---

## Commands

| Command | What It Does |
|---------|--------------|
| `Devil's advocate` | Full DA review of current output |
| `DA check` | Same as above |
| `Quick DA` | Abbreviated DA review |
| `Challenge this` | Same as Devil's advocate |
| `Red team` | Same as Devil's advocate |
| `What could go wrong?` | Triggers DA protocol |
