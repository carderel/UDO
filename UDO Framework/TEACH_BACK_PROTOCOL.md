# Teach-Back Protocol

## Purpose

Evidence packets prove claims are sourced. But sourced claims don't equal understanding.

The Teach-Back Protocol ensures the human can **own and defend** the findings, not just trust them. By the time you've read the teach-back and challenged it, you've internalized the research enough to present it as your own.

---

## When This Protocol Applies

**Required for:**
- Any deliverable that has an Evidence Packet
- Work the human will present or defend to others
- Analysis where the human needs to answer follow-up questions
- Strategic recommendations requiring stakeholder buy-in

**Not required for:**
- Internal technical work staying within the project
- Deliverables the human won't need to explain
- Code or implementation files

---

## Requirements

### 1. Teach-Back Document

For every deliverable with an Evidence Packet, create:

```
.outputs/.evidence/{deliverable-name}/TEACH_BACK.md
```

### 2. Required Sections

The teach-back MUST include:

| Section | Purpose |
|---------|---------|
| **The Question** | What were we trying to answer? |
| **Plain Language Findings** | Key findings without jargon |
| **How I Got There** | The research path, step by step |
| **What Could Challenge This** | Honest counterarguments and responses |
| **What I'm Least Certain About** | Confidence ranking by finding |
| **Questions You Should Be Ready For** | Likely challenges and how to answer |
| **30-Second Pitch** | If you had to summarize in 30 seconds |

### 3. Writing Standards

- **No jargon**: write for a smart person who hasn't seen the data
- **Conversational tone**: not a formal report, an explanation
- **Honest about weaknesses**: flag what a skeptic would challenge
- **Actionable responses**: don't just list challenges, show how to address them

### 4. Confidence Transparency

Include a confidence table:

| Finding | Confidence | Why |
|---------|------------|-----|
| Finding 1 | HIGH | Multiple sources, direct evidence |
| Finding 2 | MEDIUM | Single source, directionally clear |
| Finding 3 | LOW | Inference from incomplete data |

---

## The Teach-Back Process

### For the AI:

1. Complete the deliverable
2. Complete the Evidence Packet
3. Write TEACH_BACK.md as if explaining to someone who will present this tomorrow
4. Include everything they'd need to defend it under questioning

### For the Human:

1. Read the teach-back fully
2. Note anything unclear or unconvincing
3. Challenge the AI on weak points
4. Ask follow-up questions until you understand the reasoning
5. Confirm you could explain the main findings without notes

---

## Success Criteria

The teach-back is successful when the human can:

- [ ] Explain the main findings in their own words
- [ ] Describe how the conclusions were reached
- [ ] Anticipate and respond to likely challenges
- [ ] Identify the weakest parts of the analysis
- [ ] Give a 30-second summary without looking at the document

---

## Integration with Other Protocols

| Protocol | Relationship |
|----------|--------------|
| Evidence Protocol | Teach-back references evidence packet for deep-dive |
| Devil's Advocate | DA review happens AFTER teach-back is written |
| Audience Anticipation | Teach-back feeds into audience-specific framing |
| Reasoning Contract | Evidence packet enforces RC requirements; teach-back explains them |

---

## Template

Use `.templates/teach-back.md` for structure.

---

## Failure Mode

If you cannot write a clear teach-back:
- The analysis may be too complex or unfocused
- Revisit the deliverable and simplify
- Break into smaller, explainable components

**If you can't teach it back clearly, the human can't defend it.**
