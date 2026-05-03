---
name: bug-echo
description: 'After fixing a bug, find and rate other instances of the same pattern in the codebase. Two modes: described, or inferred from a recent fix with self-validation. Triggers: "run bug-echo", "echo this fix", "scan for similar bugs", "find other instances", "after-fix scan".'
version: 1.0.0
author: Terry Nyberg, Coffee & Code LLC
license: Apache-2.0
allowed-tools: [Grep, Glob, Read, Write, Edit, Bash, AskUserQuestion, Agent]
metadata:
  tier: execution
  category: debugging
---

# bug-echo

> **Quick Ref:** After a bug fix, identify the pattern, scan the codebase, classify findings, and produce a rated report.
> Output: `.agents/research/YYYY-MM-DD-bug-echo-<slug>.md`.

## Best invoked after a real fix

bug-echo is most effective when the **pattern came from a fix that just shipped**. A real fix proves which anti-pattern matters in your specific codebase. Pattern matching after a real fix is dramatically more accurate than pattern matching from a theoretical catalog — the fix is the evidence the pattern is a bug.

The high-leverage loop is **surface → verify → generalize**, three skills working in sequence:

1. **Surface** — `/unforget` (or any tracker) shows you a deferred row you're about to mark Fixed.
2. **Verify** — Before trusting the closure, confirm the fix is real. `/radar-suite focus on <symbol>` (or just reading the file) catches stale Open rows where the fix shipped weeks ago and nobody updated the ledger.
3. **Generalize** — Run `/bug-echo` with a one-sentence description of what the fix replaced. The output is a rated list of every echo of that anti-pattern across the codebase — including instances **that haven't crashed yet** but sit under the same runtime conditions.

Bugs that haven't fired yet are the highest-ROI thing in any audit cycle. They cost the same to fix as crashed bugs, but you skip the cost of the crash itself (lost user trust, support tickets, root-cause investigation under deadline). bug-echo is the systematic way to find them.

**Companion skills:**
- **unforget** (`https://github.com/Terryc21/unforget`) — the surface; consolidates deferred work in one file
- **radar-suite** (`https://github.com/Terryc21/radar-suite`) — the verifier; confirms the fix is real before bug-echo generalizes

bug-echo also runs standalone when you describe the pattern manually (Step 2A below) — useful when no recent fix exists but you've spotted a shape worth chasing.

---

**YOU MUST EXECUTE THIS WORKFLOW. Do not just describe it.**

**Required output:** Every BUG finding MUST include Urgency, Risk of Fixing, Risk of Not Fixing, ROI, Blast Radius, and Fix Effort using the 9-column Issue Rating Table format defined in Step 5. Findings missing any of the six dimensions are invalid.

This skill uses Claude's native tools only. No external scripts or pattern catalogs. AST-grep is optional; if it is installed, prefer it for higher precision on Swift, otherwise fall back to regex via the Grep tool.

---

## Pre-flight

Before any scanning work, verify the working environment is sane.

1. **Check for uncommitted changes:**
   - Run `git status --porcelain` via Bash.
   - If output is non-empty (uncommitted changes exist), use AskUserQuestion to ask: "There are uncommitted changes. Commit before scanning, or proceed anyway?" Options: "Commit first", "Proceed (accept risk)", "Cancel". On "Commit first", show files changed and stop with a request that the user commit. On "Cancel", stop. On "Proceed (accept risk)", log "User accepted risk of uncommitted changes" and continue.

2. **Check the codebase compiles (best-effort):**
   - This is a soft check. If `Package.swift`, `xcodeproj`, `Cargo.toml`, `package.json`, or similar build manifest is detected via Glob in the project root, note this. Do NOT actually run a build (too slow, too platform-specific). The user is responsible for ensuring their codebase builds before running bug-echo. If you detect build manifests are missing, mention it but continue.

3. **Ensure output directory exists:**
   - If `.agents/research/` does not exist, create it via `mkdir -p .agents/research/` via Bash.

### Freshness rule

Base all findings on the current source tree only. Do not read prior reports in `.agents/research/`, `scratch/`, or auto-memory caches as a source of findings. Prior reports are not consulted in v1.0.

---

## Step 1: Determine pattern source

Two modes are supported in v1.0:

1. **User-described:** the invoking prompt includes a description of the pattern. Skip to Step 2A.
2. **Inferred from recent fix:** the session has a recent edit (in conversation context or from `git log -p -1`). Use AskUserQuestion to confirm. Go to Step 2B.

If both are possible, disambiguate with AskUserQuestion:

```
Question (header: "Source"): "How should I identify the pattern?"
Options:
- "Infer from my recent fix" (Recommended). Analyze the diff and derive the pattern.
- "I'll describe it". I'll write out the pattern.
- "Cancel". Stop.
```

A planned v1.1 mode (catalog selection from a built-in pattern library) is not yet available.

---

## Step 2A: User-described pattern

Summarize the pattern back to the user:

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

This is bug-echo's distinctive mode. Execute these steps directly using Bash and native tools:

1. **Identify the diff source.** In priority order:
   - Staged changes: `git diff --cached` via Bash.
   - Unstaged changes: `git diff` via Bash.
   - Most recent commit: `git log -p -1` via Bash.
   Use the first non-empty result. If all are empty, fall back to Step 2A.

2. **Parse the diff.**
   - Lines starting with `-` (and not `---`) are removed lines (the anti-pattern).
   - Lines starting with `+` (and not `+++`) are added lines (the correct pattern).
   - Strip leading whitespace differences when constructing the pattern.

3. **Construct a search pattern from the removed lines.**
   - Identify the smallest distinctive substring of the removed code that captures the anti-pattern. Avoid matching on comments, formatting, or unrelated changes.
   - If `which ast-grep` returns a path via Bash, prefer constructing an AST-grep pattern. Otherwise construct a regex compatible with the Grep tool.
   - Keep the pattern focused. A pattern that matches `try?` would match every optional-try in the codebase; that's not useful. Prefer something like `try?\\s+context\\.fetch` for a try?-on-fetch fix.

4. **Self-validate against the pre-fix file.**
   - Determine the file the fix was applied to (from the diff header `--- a/path/to/file.swift`).
   - Read the pre-fix version: `git show HEAD~1:path/to/file.swift` via Bash (or HEAD if working tree). Compare against the constructed pattern using Grep.
   - **If the pattern matches the pre-fix file:** validated. Proceed.
   - **If the pattern does not match anything:** unvalidated. The constructed pattern doesn't actually find the bug it's supposed to find. Halt and try one of:
     - Construct a different pattern (broader or narrower).
     - Fall back to Step 2A and ask the user to describe the pattern manually.
     - Abort with explanation.
   - **Do not scan with an unvalidated pattern.** Scanning with a bad pattern produces nonsense findings and erodes user trust.

5. **Present the inferred pattern** using the Step 2A summary format and confirm with the user before scanning.

The validation step is non-negotiable. If you cannot construct a pattern that matches the pre-fix file, the inference has failed. Do not proceed with a guess.

---

## Step 3: Execute the scan

Run the validated pattern across the codebase.

1. **Build the file list:**
   - Use Glob with the pattern's `search_scope` (default `**/*.swift` for Swift fixes; adjust by language).
   - For multiplatform Swift codebases, Claude must respect `#if os(...)` and `#if !os(...)` blocks during classification. Code inside an excluded platform branch is not flagged.

2. **Choose the scan strategy based on file count:**
   - **Under 50 files:** Scan directly using Grep with the pattern.
   - **50 to 500 files:** Scan directly. Acceptable performance.
   - **Over 500 files:** Dispatch sub-agents via the Agent tool. Split files into batches of ~100. Each sub-agent receives the pattern, its file list, and the classification rules from Step 4. Sub-agents return structured findings (matches with file:line context). Aggregate results in the main agent.

3. **AST-grep precision (optional, opt-in):**
   - If AST-grep is installed and the language is Swift, run AST-grep against the pattern via Bash for higher precision.
   - If AST-grep is not installed or fails, fall back to regex via Grep. Note in the report which tool produced the matches.

---

## Step 4: Classify findings

For each match, regardless of how it was found:

1. **Read the file** at the match location (Read tool), at minimum 20 lines around the match. Multi-platform code may need a wider window to capture surrounding `#if` blocks.

2. **Check for known intentional usages.**
   - In v1.0, this is in-context judgment by Claude. Common intentional uses (e.g., `try?` in test code where failure is acceptable, force-unwrap of an IBOutlet) are classified as OK. A future v1.1 may add a `known-intentional.yaml` file the user can populate.

3. **Classify** as one of:
   - **BUG:** matches the anti-pattern, correctness issue confirmed in this context.
   - **OK:** correct usage, no action needed (e.g., `as!` after a validated `is` check; strong `self` capture in a SwiftUI struct view).
   - **REVIEW:** context unclear, requires human judgment.

Classify each match individually. Do not batch-judge a directory or file.

---

## Step 5: Generate report

Write the report directly to `.agents/research/YYYY-MM-DD-bug-echo-<slug>.md` using the Write tool. The slug is a short kebab-case description of the pattern.

### Report format

```markdown
# bug-echo Report: [Pattern Name]

**Date:** YYYY-MM-DD
**Pattern source:** [user-described | inferred from fix]
**Scan tool:** [ast-grep | regex]
**Files scanned:** [N]
**Pattern validated against pre-fix file:** [yes | n/a for user-described]

## Pattern

**Anti-pattern:** [description]
**Correct pattern:** [description]
**Search regex:** `[pattern]` (or `ast-grep query: ...`)

## Summary

- BUG findings: [N]
- OK findings: [N]
- REVIEW findings: [N]

## BUG Findings

### Issue Rating Table

| # | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | [short description] | [🔴 CRITICAL / 🟡 HIGH / 🟢 MEDIUM / ⚪ LOW] | [⚪ Low / 🟡 High / 🔴 Critical] | [⚪ Low / 🟢 Medium / 🟡 High / 🔴 Critical] | [🟠 Excellent / 🟢 Good / 🟡 Marginal / 🔴 Poor] | [⚪ 1 file / 🟢 N files / 🟡 N+ files] | [Trivial / Small / Medium / Large] | Open |

The Status column is `Open` on first display. After fixes are applied, the column updates to `Fixed`, `Deferred`, or `Skipped`.

### Detailed findings

For each BUG finding:

```
**[N]. [short description]**

`path/to/file.swift:[line]`

[code snippet, 5-10 lines around the match]

**Why this is a bug:** [1-2 sentences]
**Suggested fix:** [1-2 sentences]
```

## OK Findings (intentional, no action needed)

For each OK match, one line:
- `path/to/file.swift:[line]` - [reason it's OK]

## REVIEW Findings (need human judgment)

For each REVIEW match:
- `path/to/file.swift:[line]` - [why context is unclear]
```

The report is human-readable and self-contained. A future v1.1 may add a JSON sidecar for downstream skill chaining (e.g., feeding findings into `safe-refactor`).

---

## Step 6: Follow-up

After the report is written, offer guided fixes via AskUserQuestion:

```
Question (header: "Next"): "How would you like to proceed?"
Options:
- "Fix all BUG findings". Walk through each finding; apply fixes with approval.
- "Fix selected". Choose which findings to fix.
- "Report only". I'll handle fixes manually.
```

**For guided fixes:**
1. Present the BUG finding with file:line, code snippet, and suggested fix.
2. Show the proposed Edit (old_string and new_string).
3. Ask for explicit approval before applying.
4. Apply via the Edit tool only after the user confirms.
5. Update the report's Issue Rating Table to mark Status as `Fixed`, `Skipped`, or `Deferred` for each finding processed.

Re-display the rating table at the end of the fix session with all Status columns populated.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Diff parsing fails because the recent edit is not a bug fix (rename, comment change, formatting) | Pattern self-validation will fail. Fall back to Step 2A and ask the user to describe the pattern manually. |
| Too many matches | Narrow the scope by passing a directory in the user's pattern description (e.g., `Sources/Features/Auth/`). |
| AST-grep not installed | Use regex via the Grep tool. Install with `brew install ast-grep` for higher precision on Swift if precision matters. |
| All matches classified OK | Pattern is localized to the original file. Report zero BUG findings and stop. That's a successful run, not a failed one. |
| Sub-agent dispatch fails | Fall back to sequential scan in the main agent. Slower but functional. |
| Mixed intentional and buggy matches | Classify each individually using Step 4 rules. Do not batch-judge. |
| Pattern matches across `#if os(...)` boundaries | Honor platform conditionals during classification. Code inside the wrong `#if` block is OK, not BUG. |

---

## Deferred to v1.1+

These features are documented for future releases:

- **Catalog mode (Step 2C):** a built-in pattern library for common Swift/SwiftUI anti-patterns the user can pick from when described and inferred modes both fail.
- **JSON sidecar:** machine-readable output alongside the Markdown report, for chaining into downstream skills.
- **Recurrence detection:** comparing the new report against prior reports in `.agents/research/` to detect recurring patterns and suggest architectural fixes.
- **`known-intentional.yaml` user file:** explicit suppression of patterns the user has confirmed are intentional, so they don't surface again.
- **Multi-language pattern construction beyond Swift:** the v1.0 inference works for any language (regex from diff is language-neutral), but v1.1 may add language-specific tuning.
