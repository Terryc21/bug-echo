---
name: bug-echo
description: 'After fixing a bug, find and rate other instances of the same pattern in the codebase. Three modes: described, inferred from recent fix (with self-validation), or selected from a built-in catalog. Triggers: "run bug-echo", "echo this fix", "scan for similar bugs", "find other instances", "after-fix scan".'
version: 1.0.0
author: Terry Nyberg, Coffee & Code LLC
license: Apache-2.0
allowed-tools: [Grep, Glob, Read, Write, Edit, Bash, AskUserQuestion, Task]
metadata:
  tier: execution
  category: debugging
---

# bug-echo

> **Quick Ref:** After a bug fix, identify the pattern, scan the codebase using AST-aware matching, classify findings, and produce a rated report.
> Output: `.agents/research/YYYY-MM-DD-bug-echo-<slug>.md` + `.json` sidecar.

**YOU MUST EXECUTE THIS WORKFLOW. Do not just describe it.**

**Required output:** Every BUG finding MUST include Urgency, Risk of Fixing, Risk of Not Fixing, ROI, Blast Radius, and Fix Effort using the Issue Rating Table format. Findings missing any of the six dimensions are invalid.

---

## Pre-flight

Run `scripts/preflight.sh`. It checks:

- Uncommitted changes in tracked files.
- Build state — whether the codebase last compiled successfully.
- Presence of `.agents/research/` for report output (creates if missing).

If uncommitted changes exist, ask the user via AskUserQuestion whether to commit before proceeding. If the user declines, log "User accepted risk of uncommitted changes" and continue.

If the codebase does not compile, **halt** and inform the user. Scanning a broken codebase produces unreliable findings because the parser may be reading syntactically incomplete files. Resume only after the user confirms the codebase compiles, or accepts the risk explicitly.

### Freshness rule

Base all findings on the current source tree only. Do not read prior reports in `.agents/research/`, `scratch/`, or auto-memory caches **during the scan**. Prior reports are read only in Step 5 for recurrence detection — never as a source of findings.

---

## Step 1: Determine pattern source

Three modes are supported, in priority order:

1. **User-described** — the invoking prompt includes a description of the pattern. Skip to Step 2A.
2. **Infer from recent fix** — the session has a recent edit (in conversation context or `git log -p -1`). Offer this as the default when available.
3. **Catalog** — neither of the above. Prompt the user to select from `patterns/*.yaml`.

When more than one mode is available, disambiguate with AskUserQuestion:

```json
[
  {
    "question": "How should I identify the pattern?",
    "header": "Source",
    "options": [
      {"label": "Infer from my recent fix", "description": "Analyze the diff and derive the pattern"},
      {"label": "Pick from catalog", "description": "Choose a common Swift/SwiftUI anti-pattern"},
      {"label": "I'll describe it", "description": "I'll write out the pattern"},
      {"label": "Cancel", "description": "Stop"}
    ],
    "multiSelect": false
  }
]
```

---

## Step 2A: User-described pattern

Summarize the pattern back:

```markdown
**Pattern:** [name]
**Anti-pattern:** [what the bad code looks like]
**Correct pattern:** [what it should be]
**Search scope:** [file globs or directories]
**Platforms:** [iOS, iPadOS, macOS, watchOS, or "all"]
```

Confirm with AskUserQuestion (Yes scan now / Refine / Cancel) before proceeding to Step 3.

---

## Step 2B: Infer from recent fix

This is bug-echo's distinctive mode. Run `scripts/infer-pattern-from-diff.sh`:

1. Identifies the diff source — staged changes, unstaged changes, or `git log -p -1` — whichever is most recent.
2. Parses the diff into removed lines (anti-pattern) and added lines (correct pattern).
3. Constructs a candidate AST query (or regex fallback) from the removed code.
4. **Self-validates** by applying the candidate to the pre-fix version of the file. Returns:
   - `validated` — the candidate matches the pre-fix file. Proceed.
   - `ambiguous` — multiple candidate patterns possible. Present top candidates via AskUserQuestion.
   - `unvalidated` — cannot confirm the pattern matches anything bug-shaped (e.g., the edit was a comment change, rename, or formatting fix). **Fall back to Step 2A or 2C — do not scan with an unvalidated pattern.**

When `validated`, present the inferred pattern using the Step 2A summary format and confirm before scanning.

The validation step is non-negotiable. Scanning with an unvalidated pattern produces nonsense findings and erodes user trust in the skill.

---

## Step 2C: Catalog selection

Read `patterns/index.yaml` for available patterns. Present names and one-line descriptions via AskUserQuestion. On selection, load the full definition from `patterns/<name>.yaml`.

See `references/pattern-schema.md` for the YAML schema. Patterns include AST queries, regex fallbacks, false-positive guards, default urgency, and applicable platforms.

---

## Step 3: Execute the scan

Run `scripts/run-scan.py` with the validated pattern. The script:

1. Builds the file glob from pattern + scope (default `**/*.swift`).
2. Dispatches subagents via the Task tool when the glob exceeds 20 files. Each subagent receives the pattern, its file list, and the classification contract; returns structured findings without polluting the main agent's context.
3. Aggregates findings into a single list.

For small scans (< 20 files), the main agent performs the scan directly.

### Multiplatform handling

If the pattern's `applies_to_platforms` is restricted, the scanner respects `#if os(...)` and `#if !os(...)` blocks. Code inside an excluded platform branch is **not** flagged. This prevents false positives like flagging macOS-correct code as iOS-buggy.

---

## Step 4: Classify findings

For each match, regardless of how it was found:

1. **Read the file** — at minimum 20 lines around the match. Multi-platform code may need a wider window to capture surrounding `#if` blocks.
2. **Check `references/false-positives.md`** for known intentional usages of this pattern.
3. **Check the pattern's `false_positive_guards`** from its YAML definition.
4. **Classify** as one of:
   - **BUG** — matches the anti-pattern, correctness issue confirmed.
   - **OK** — correct usage, no action needed (e.g., `as!` after a validated `is` check; strong `self` capture in a SwiftUI struct view).
   - **REVIEW** — context unclear, requires human judgment.

Classify each match individually. Do not batch-judge a directory or file.

---

## Step 5: Generate report

Run `scripts/render-report.py` to produce both outputs:

- `.agents/research/YYYY-MM-DD-bug-echo-<slug>.md` — human-readable, includes the Issue Rating Table.
- `.agents/research/YYYY-MM-DD-bug-echo-<slug>.json` — machine-readable sidecar for chaining with downstream tools (e.g., `safe-refactor` consuming bug-echo findings).

See `references/report-format.md` for the full report template, including the Issue Rating Table column conventions, color coding, and the Status column for re-display after fixes.

### Prior-report awareness

After writing the new report, `scripts/check-recurrence.py` compares against prior bug-echo reports in `.agents/research/`. If the same pattern appears in 3 of the last 4 scans, append a **Recurrence Warning** section recommending an architectural fix or custom SwiftLint rule rather than another point fix. Recurring patterns are a signal that point fixes are not addressing the root cause.

---

## Step 6: Follow-up

Offer guided fixes via AskUserQuestion:

```json
[
  {
    "question": "How would you like to proceed?",
    "header": "Next",
    "options": [
      {"label": "Fix all BUG findings", "description": "Walk through each finding; apply fixes with approval"},
      {"label": "Fix selected", "description": "Choose which findings to fix"},
      {"label": "Report only", "description": "I'll handle fixes manually"}
    ],
    "multiSelect": false
  }
]
```

For guided fixes: present the BUG finding, show current code, propose the fix, apply **only** after explicit user approval. Update the JSON sidecar's Status field for each finding (Open → Fixed / Skipped / Deferred). The Status column is included in re-displays of the rating table after fixes are applied.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `infer-pattern-from-diff.sh` returns `unvalidated` | The recent edit may not be a bug fix (refactor, comment change, formatting). Fall back to Step 2A or 2C. |
| Too many matches | Narrow the glob via `scope` (e.g., `Sources/Features/Auth/`). |
| AST-grep not installed | Falls back to regex. Install with `brew install ast-grep` for higher precision on Swift. |
| All matches classified OK | Pattern may be localized to the original file. Report zero bugs and stop — that's a successful run, not a failed one. |
| Subagent dispatch fails | Falls back to sequential scan in the main agent. Slower but functional. |
| Mixed intentional and buggy matches | Classify each individually. Do not batch-judge. |
| Pattern matches across `#if os(...)` boundaries | The scanner should already respect platform blocks. If false positives appear, verify the pattern YAML's `applies_to_platforms` field is correct. |

---

## Required references

- `references/pattern-schema.md` — YAML schema for `patterns/*.yaml`.
- `references/report-format.md` — full report template and Issue Rating Table conventions.
- `references/false-positives.md` — known intentional usages, expanded from real-world findings.
- `references/ast-grep-quickstart.md` — AST query syntax for users new to AST-grep.
