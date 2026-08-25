---
name: bug-echo
description: 'After fixing a bug, find and rate other instances of the same pattern in the codebase. Two modes: described, or inferred from a recent fix with self-validation. Triggers: "run bug-echo", "echo this fix", "scan for similar bugs", "find other instances", "after-fix scan".'
license: Apache-2.0
allowed-tools: [Grep, Glob, Read, Write, Edit, Bash, AskUserQuestion, Agent]
metadata:
  version: 1.5.1
  author: Terry Nyberg, Coffee & Code LLC
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

This is a workflow to run, not a procedure to summarize. The user invoked it because they want the scan performed and the findings in hand; a description of what bug-echo would do leaves them exactly where they started.

**Rate every BUG finding on all six dimensions** — Urgency, Risk of Fixing, Risk of Not Fixing, ROI, Blast Radius, and Fix Effort — using the Issue Rating Table in Step 5. The six exist because "here are 14 bugs" is not actionable: the user has to decide what to fix before the next release and what to leave. A finding missing Risk of Not Fixing or Blast Radius can't be triaged against the others, so it silently drops out of that decision no matter how real the bug is.

This skill uses Claude's native tools only. No external scripts or pattern catalogs. AST-grep is optional; if it is installed, prefer it for higher precision on Swift, otherwise fall back to regex via the Grep tool.

---

## Pre-flight

Before any scanning work, verify the working environment is sane.

1. **Check for uncommitted changes:**
   - Run `git status --porcelain` via Bash.
   - If output is non-empty (uncommitted changes exist), use AskUserQuestion to ask: "There are uncommitted changes. If these are from a prior bug-echo session, commit them first so this run has a clean baseline. Otherwise: commit before scanning, or proceed anyway?" Options: "Commit first", "Proceed (accept risk)", "Cancel". On "Commit first", show files changed and stop with a request that the user commit. On "Cancel", stop. On "Proceed (accept risk)", log "User accepted risk of uncommitted changes" and continue.

2. **Note build manifest presence (advisory):**
   - Detect via Glob whether `Package.swift`, `xcodeproj`, `Cargo.toml`, `package.json`, or a similar build manifest exists in the project root. Note the result in the report header. Do NOT run a build — that's the user's responsibility before applying any fix this skill suggests. If no manifest is detected, mention it but continue scanning. This step is advisory metadata for the report, not a gate.

3. **Resolve output directory:**
   - **Default:** `.agents/research/`. This is a convention shared with radar-suite, bug-prospector, and other Coffee & Code audit skills; if your project doesn't already use it, this run creates it via `mkdir -p .agents/research/`.
   - **Override:** if the invoking prompt contains `output=<path>` (e.g., `/bug-echo output=docs/audits/`), use that path instead. Create it with `mkdir -p` if missing. Trailing slash is optional.
   - Write the resolved path to a variable used by Step 5's report-generation step. The report header should also record the resolved path so the user can find it.

### Freshness rule

Base all findings on the current source tree only. Do not read prior reports in `.agents/research/`, `scratch/`, or auto-memory caches as a source of findings. A prior report describes a tree that has since changed; treating it as evidence means reporting bugs that may already be fixed, which is the fastest way to make the output untrustworthy.

### Scale gates

Three features in this skill are gated on absolute counts, not on repo size: the already-swept exclusion (Step 2.5, ≥6 candidates *and* prior `bug-echo:` commits), the high-count tighten offer (Step 2.5, ≥25 candidates), and sub-agent dispatch (Step 3, >500 files). Below its gate, each is a no-op.

Treat those gates as real thresholds rather than hints. A small repo should feel exactly as fast and as quiet as it did before any of them existed — reaching for a large-codebase accommodation on a 40-file package spends the user's time defending against a problem they don't have.

---

## Step 1: Determine pattern source

Two modes are supported:

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

There is deliberately no third "pick from a catalog of known anti-patterns" mode. A catalog tells you what tends to be a bug in general; a fix tells you what *is* a bug here. If neither mode applies, see § When inference fails below.

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

**Conditions form (recommended for multi-condition patterns).** Many real bug shapes only fire when 2-3 conditions hold together. Asking the user to articulate them up front produces a sharper scan than free-form prose. Suggested form:

```markdown
**Condition 1:** [e.g., "Identifiable struct with `let id = UUID()`"]
**Condition 2:** [e.g., "constructed inside a computed `var`/`func` returning `[T]`"]
**Condition 3:** [e.g., "that array feeds a SwiftUI `ForEach` / `List` / `Picker`"]
**Consumer impact:** [why the conditions together produce the bug]
```

A single-condition pattern (e.g., a deprecated API name) doesn't need this form. Free-form prose is fine. Use the conditions form when the user's description includes "and" twice or more, or when the pattern is shape-based rather than name-based.

Confirm with AskUserQuestion (Yes scan now / Refine / Cancel) before proceeding to Step 3.

---

## Step 2B: Infer from recent fix

This is bug-echo's distinctive mode. Execute these steps directly using Bash and native tools:

1. **Identify the diff source.** In priority order:
   - Staged changes: `git diff --cached` via Bash.
   - Unstaged changes: `git diff` via Bash.
   - Most recent commit: `git log -p -1` via Bash.
   Use the first non-empty result. If all are empty, fall back to Step 2A.

   **Guard against inferring from bug-echo's own fix commit.** This applies *only* when the selected source is the most recent commit (`git log -p -1`) — staged and unstaged diffs are genuine new work and are never blocked. Step 6 commits applied fixes with a subject line starting `bug-echo:`. If a user runs `/bug-echo`, applies fixes, commits via that flow, then runs `/bug-echo` again with no intervening real fix, `git log -p -1` would hand back bug-echo's own fix commit — and inferring a pattern from it just re-derives the pattern those fixes already resolved. To prevent this degenerate self-referential loop: before parsing the most-recent-commit diff, run `git log -1 --format=%s` via Bash. If the subject starts with `bug-echo:`, do NOT infer from it. Skip to Step 2A (described mode) and explain briefly: "The most recent commit is a bug-echo fix commit — inferring from it would just re-derive the pattern it already fixed. Describe the pattern you want scanned, or point me at a different fix (e.g., `HEAD~1`)." This check is universal (not size-gated) and inert unless HEAD is a bug-echo commit.

2. **Parse the diff.**
   - Lines starting with `-` (and not `---`) are removed lines (the anti-pattern).
   - Lines starting with `+` (and not `+++`) are added lines (the correct pattern).
   - Strip leading whitespace differences when constructing the pattern.

2.1 **Check whether the removed lines are self-sufficient.**

   Before building a pattern, ask: *reading the removed lines alone, with no other context, can you tell this is a bug?*

   - **Yes, self-sufficient.** `try? context.fetch(...)` swallowing an error is wrong on sight. Continue to step 3 unchanged. This is the common case.
   - **No, the removed lines look ordinary.** The line reads as unremarkable code, and what made it a bug is somewhere else in the enclosing scope: a guard two lines up, a state the function sets before reaching it, a lock not held, an early return that should have fired. The bug is the *combination*, and the changed line is only half of it.

   **If not self-sufficient**, read the enclosing scope from the pre-fix file (the function or method containing the change; use the whole type only if the function boundary is unclear) and identify the **precondition**: the thing that had to also be true for this line to be a bug.

   Then build **two** patterns, not one:
   - the **primary pattern**, from the removed lines, exactly as in step 3;
   - a **precondition pattern**, from the enclosing scope, describing the state that makes the primary a bug.

   Carry both forward. The recon scout (Step 2.5) and the scan (Step 3) use the primary pattern to find candidates; the precondition pattern is checked against each candidate's enclosing scope during Step 4 classification. A match with the primary but not the precondition is classified **OK**, with the reason naming the missing precondition.

   🛑 **Do not fold the precondition into the primary pattern.** A conjoined regex only matches where both appear on the same line, which is exactly what the precondition case is not, and it would silently drop the siblings you are trying to find. Two patterns, applied at different stages.

   ⚠️ **If you cannot name the precondition, say so and switch to Step 2A described mode.** Do not proceed with the primary pattern alone and report a clean run. A zero-match result from a pattern that was never able to express the bug is a false all-clear, and it is worse than admitting the inference failed. Tell the user plainly: "The fixed line looks ordinary on its own and I can't tell what made it a bug from the diff. Describe the pattern and I'll scan for it."

   *Why this step exists: pattern inference reads the removed lines only. Context is used at classification (a 20-line window) but never at construction, so a precondition living outside the diff never reaches the search. The result is a confident zero-match run on a codebase that may hold many siblings. Raised 2026-08-25 by a user on r/claudeskills who reported better results feeding their own checker the enclosing function rather than just the changed lines.*

3. **Construct a search pattern from the removed lines.**
   - Identify the smallest distinctive substring of the removed code that captures the anti-pattern. Avoid matching on comments, formatting, or unrelated changes.
   - If `which ast-grep` returns a path via Bash, prefer constructing an AST-grep pattern. Otherwise construct a regex compatible with the Grep tool.
   - Keep the pattern focused. A pattern that matches `try?` would match every optional-try in the codebase; that's not useful. Prefer something like `try?\\s+context\\.fetch` for a try?-on-fetch fix.

4. **Self-validate against the pre-fix file.**
   - Determine the file the fix was applied to (from the diff header `--- a/path/to/file.swift`).
   - Read the pre-fix version using whichever of these matches the diff source:
     - **Staged diff** (Step 1 used `git diff --cached`): the pre-fix version is the HEAD baseline. Use `git show HEAD:path/to/file.swift`.
     - **Unstaged diff** (Step 1 used `git diff`): the pre-fix version is HEAD. Use `git show HEAD:path/to/file.swift`.
     - **Most recent commit** (Step 1 used `git log -p -1`): the pre-fix version is HEAD~1. Use `git show HEAD~1:path/to/file.swift`. If this returns empty because the repo has only one commit (`git rev-list --count HEAD` returns 1), abort with "no pre-fix baseline available; switch to Step 2A described mode."
     - **File renamed in the most recent commit:** detect via `git log --follow --name-status -1 -- path/to/file.swift`. If the `R<score>` line shows a prior path, use `git show HEAD~1:<prior-path>` instead.
   - Compare the result against the constructed pattern using Grep.
   - **If the pattern matches the pre-fix file:** validated. Proceed.
   - **If the pattern does not match anything:** unvalidated. The constructed pattern doesn't actually find the bug it's supposed to find. Halt and try one of:
     - Construct a different pattern (broader or narrower).
     - Fall back to Step 2A and ask the user to describe the pattern manually.
     - Abort with explanation.
   - **Do not scan with an unvalidated pattern.** Scanning with a bad pattern produces nonsense findings and erodes user trust.

5. **Present the inferred pattern** using the Step 2A summary format and confirm with the user before scanning. **If step 2.1 produced a precondition pattern, show both**, labelled, with one line on what the precondition means: the primary finds candidates, the precondition decides which of them are bugs. The user is the best check on whether the precondition you named is the real one.

The validation step is non-negotiable. If you cannot construct a pattern that matches the pre-fix file, the inference has failed. Do not proceed with a guess.

---

## Step 2.5: Recon scout (decide report shape)

Before running the full scan + classify + rate + write ceremony, run the validated pattern once to count candidates. The count decides the response shape. This step prevents the most common over-spend in bug-echo runs: rendering a 200-line rated report on a pattern that turns out to be already localized.

**Execute:**

1. Run a single Grep with the validated pattern across the project's source tree (use the search scope from Step 2A or the file's directory from Step 2B). No classification yet — just count `file:line` matches.
2. **Exclude sites you already swept (large-codebase multi-pass guard).** On a big codebase you will often bug-echo the *same* anti-pattern across several sessions as you chip away at it. Sites fixed-and-committed in a prior bug-echo run should not resurface as fresh candidates.

   **Gate — run this sub-step only when ALL of these hold:**
   - `recon_candidate_count` from step 1 is **≥ 6** (below that, the bucket is already lightweight and the extra work is not worth it), AND
   - `git log --grep="^bug-echo:" --oneline -1` via Bash returns at least one commit (i.e., this repo has prior bug-echo fix commits).

   If either condition is false, **skip this sub-step entirely** — set `recon_swept_count = 0` and continue. On a small codebase, or a first-ever run, this is a single cheap `git log` call that returns empty and changes nothing.

   **When the gate opens:**
   - Read the file:line pairs touched by prior bug-echo commits: `git log --grep="^bug-echo:" --name-only --format="%H" -n 50` via Bash. Collect the set of files those commits modified. **Cap the walk at the 50 most recent `bug-echo:` commits** (the `-n 50` above): the cost of the walk is bounded by commit count, not calendar time, so it stays predictable no matter how long the project has used bug-echo. If more than 50 exist, note in the reconciliation line that older bug-echo commits were not cross-referenced — those sites simply get re-classified as fresh, which is safe (the worst case is a little redundant work, never a wrongly hidden bug).
   - For each current candidate match, if its file appears in that set, re-read the match site (Read tool, 5-line window) and check whether the anti-pattern is still present. **Git history says the file was touched; only the live source says whether this specific line is still buggy.** Do not exclude on filename alone — a later edit may have reintroduced the pattern, and re-finding it is exactly the value.
   - Exclude a candidate only when the prior-swept file *and* the current line no longer matches the anti-pattern. Count excluded sites as `recon_swept_count`.
   - Subtract `recon_swept_count` from `recon_candidate_count` before bucketing in the next step. Report both numbers so the user sees the reconciliation (e.g., "9 raw matches, 3 already swept in prior bug-echo commits, 6 fresh").

   This is the conservative, ground-truth-only slice of the deferred "recurrence detection" feature: it reads git commit history (authoritative record of what was fixed), never prior `.agents/research/` reports (which the Freshness rule forbids as a finding source).
3. **Exclude the just-fixed site itself.** When in Step 2B inference mode, the original-fix file already has the fix applied; if the pattern is constructed from removed lines, it should produce 0 matches there. When in Step 2A described mode, no exclusion needed.
4. Bucket the result:

| Candidates | Report shape |
|---|---|
| **0** | Emit a one-line note in conversation: "No echoes found. Pattern appears localized to the original fix site." Do NOT write a `.agents/research/` report. Stop. |
| **1-5** | Lightweight inline report. Classify each match in conversation using Step 4 rules. Render a single Issue Rating Table for confirmed BUGs. Skip the OK / REVIEW / WATCH sections unless something interesting appears. Do NOT write a `.agents/research/` file unless the user asks for one. |
| **6+** | Full skill flow — proceed to Step 3 and write a `.agents/research/` report per Step 5. |

**High-count guard (offer to tighten before classifying).** A pattern can pass self-validation (it matches the pre-fix line) yet still be too broad, returning a large match set that is mostly OK. Classifying hundreds of sites to confirm they are noise is the single most expensive way to run this skill.

**Gate — trigger this offer only when BOTH hold:**
- `recon_candidate_count` (after the already-swept exclusion in Execute step 2) is **≥ 25**, AND
- the pattern is name-based or shape-based rather than an exact-once construct — i.e., a broad match is plausible. (A pattern built from a distinctive multi-token substring that happens to hit 25+ real sites is a legitimate big sweep, not noise. If uncertain, still offer; the user can decline in one keystroke.)

The **25** threshold is absolute, not relative to codebase size. A 40-file project where a pattern legitimately appears 30 times should trigger the same offer as a 5,000-file one — the cost being avoided is *classifying 30 sites*, which is the same work regardless of repo size. Below 25, never show this; the classify step is cheap enough that interrupting the user is the worse trade.

**When the gate opens**, use AskUserQuestion before proceeding to Step 3:

```
Question (header: "Breadth"): "[N] candidate sites match — enough that some are likely false positives. Tighten the pattern before I classify all [N]?"
Options:
- "Tighten first" (Recommended). Show me the current pattern; I'll narrow it (add a qualifier, require an adjacent token) and re-run the recon count.
- "Classify all [N]". The breadth is expected; scan and classify everything.
- "Sample first". Classify a 10-site sample across the match set; if the BUG rate is low, I'll suggest tightening then.
```

On "Tighten first": present the current regex/AST pattern, propose one or two narrower variants with a one-line rationale each, and on the user's pick re-run Execute steps 1-4 (recount, re-exclude swept, re-exclude the fix site, re-bucket) with the tighter pattern. On "Sample first": classify 10 matches spread across the file list; if fewer than ~20% are BUG, recommend tightening and re-offer.

This guard directly addresses the "heavily overloaded with false positives" case in the README's Honest Limits, moving the tightening decision *before* the expensive per-site classification rather than after.

**Why the buckets matter.** Across 18 real bug-echo runs on a 600-file Swift project, 2 found zero real bugs after the full ceremony and another 5 found 1-3. In those 7 cases (~39% of runs), the full `.agents/research/` write was over-spend — the report's structure carried more weight than the findings did. The recon-scout step matches output shape to actual signal. (Run-by-run data, and the limits of an N=18 single-codebase sample, are in [recon-scout-rationale.md](examples/recon-scout-rationale.md).)

**When to override the bucket:**

- The user explicitly asked for a written report (`/bug-echo write-report` or similar invocation). Always write the file.
- The pattern is one the user wants to track across releases (multi-pass cleanup, sweep-style). Always write the file so the next run can reference it. Detect via Step 2A user description ("track this", "sweep", "we'll address in multiple passes") or via the user's prior reports in `.agents/research/` (already excluded as a finding source per Freshness rule, but discoverable for this purpose via `ls`).
- The 1-5 bucket contains a finding the user describes as release-blocking. Promote that finding's writeup to a small report anyway.

If you override, say which bucket the count fell into and why you wrote the report anyway.

**State emitted to later steps:** `recon_candidate_count` (integer), `recon_report_mode` (`none` / `inline` / `full`). Steps 3-5 read these.

---

## Step 3: Execute the scan

> **Note for `recon_report_mode = none`:** skip Step 3-5 entirely. The recon scout already produced the answer. Emit the one-line "no echoes found" note and stop.
>
> **Note for `recon_report_mode = inline`:** the recon scout already produced the match list. Skip building file lists from scratch; just read each match site for classification (Step 4) and render a single inline rating table (Step 5 lightweight form). No file write.

Run the validated pattern across the codebase.

1. **Build the file list:**
   - Use Glob with the pattern's `search_scope` (default `**/*.swift` for Swift fixes; adjust by language).
   - For multiplatform Swift codebases, Claude must respect `#if os(...)` and `#if !os(...)` blocks during classification. Code inside an excluded platform branch is not flagged.

2. **Choose the scan strategy based on file count:**
   - **Under 50 files:** Scan directly using Grep with the pattern.
   - **50 to 500 files:** Scan directly. Acceptable performance.
   - **Over 500 files:** Dispatch sub-agents via the Agent tool. Split files into batches of ~100. Follow the sub-agent aggregation contract in Step 3.5 — it defines exactly what each sub-agent receives, what it returns, and how the main agent merges the batches. Do not improvise the merge; a large run's correctness depends on deterministic aggregation.

3. **AST-grep precision (optional, opt-in):**
   - If AST-grep is installed and the language is Swift, run AST-grep against the pattern via Bash for higher precision.
   - If AST-grep is not installed or fails, fall back to regex via Grep. Note in the report which tool produced the matches.

4. **Language-specific custom analyzers (rare, opt-in):**
   - For patterns that neither regex nor AST-grep can express cleanly — e.g., counting scope-direct conditional children at the lexical scope level (see `examples/2026-05-03-bug-echo-deep-viewbuilder-crash.md`, which uses a custom Python brace-depth analyzer) — a custom analyzer is acceptable. Invoke an external script (Python, Swift, etc.) via the Bash tool. The script must accept a list of paths and emit findings with `file:line` context the classification step in Step 4 can consume. Note the tool in the report header's "Scan tool:" field.
   - This is rare. Default is Grep; AST-grep is the first fallback; custom analyzers are the second.

---

## Step 3.5: Sub-agent aggregation contract (>500-file branch only)

This step governs the `Over 500 files` branch of Step 3.2 exclusively. **Codebases at or under 500 files never reach it** — they scan directly in the main agent and go straight to Step 4, so nothing here touches the common path (see § Scale invariants). On a large codebase the batched scan is the path that runs on essentially every run, so its merge must be deterministic rather than improvised.

### What each sub-agent receives

Every sub-agent dispatched via the Agent tool gets an identical instruction payload, differing only in its file-list slice:

1. **The validated pattern**, verbatim — the exact regex (or AST-grep query) from Step 2B/2A, not a paraphrase.
2. **Its ~100-file batch**, as an explicit list of paths. Batches must be disjoint where possible; see the dedup rule below for the overlap case.
3. **The Step 4 classification rules, copied VERBATIM.** Do not summarize, shorten, or restate the BUG / WATCH / OK / REVIEW definitions. Every sub-agent must classify against byte-identical criteria, or two batches will render different verdicts for the same code shape. Paste the full text of Step 4's classification list (the four definitions and the "classify each match individually" rule) into each sub-agent's prompt.
4. **The platform-conditional rule** from Step 3.1: honor `#if os(...)` / `#if !os(...)` blocks; code inside an excluded platform branch is not flagged.

### What each sub-agent returns

Each sub-agent returns a structured list — one object per match, no prose wrapper — so the main agent can merge without re-parsing free text. Required fields per match:

```
{
  "file": "relative/path/to/File.swift",   // repo-relative, forward slashes
  "line": 142,                              // 1-indexed line of the match
  "snippet": "…5-10 lines around the match…",
  "classification": "BUG",                  // one of BUG | WATCH | OK | REVIEW
  "canon": false,                           // OK only: true if this site is the reference implementation (Step 4)
  "rationale": "one sentence: why this classification"
}
```

A sub-agent that finds nothing in its batch returns an empty list, not a message.

### How the main agent merges

1. **Concatenate** every sub-agent's list into one candidate set.
2. **Deduplicate on the `(file, line)` key.** Overlapping globs or a pattern that spans a batch boundary can make two sub-agents report the same site. Keep one entry per `(file, line)`. If the two entries agree on classification, collapse silently. If they **disagree** on classification for the same `(file, line)`, do not pick arbitrarily — this is a consistency failure; handle it in step 3.
3. **Spot-check for divergent classifications of near-identical shapes.** Beyond exact `(file, line)` collisions, scan the merged set for structurally near-identical sites (same syntactic shape, same surrounding context) that received *different* classifications across batches. For each such divergence, the main agent re-reads both sites (Read tool, 20-line window per Step 4.1) and issues the authoritative classification itself, overriding the sub-agent verdicts. Record in the report header how many divergences were reconciled (e.g., `Cross-batch reconciliations: 2`), so a reader knows the merge was checked, not assumed.
4. **Propagate any `canon: true` site across the whole merged set.** A sub-agent sees only its own batch, so the batch holding the reference implementation is usually not the batch holding the BUG findings that should cite it. After dedup, collect every `canon: true` entry and make it available to all BUG findings, whichever batch reported them. Without this the citation required by Step 4 silently doesn't happen on exactly the large sweeps where re-derivation is most costly.
5. **Carry the reconciled set into Step 4** as if it had come from a direct scan. Step 4's per-match work (the 20-line read, the intentional-usage check) still applies to any match the main agent did not already re-read during reconciliation; matches re-read in step 3 above are already classified and need not be re-read again.

### Failure handling

If a sub-agent dispatch fails or returns malformed output (not the structured shape above), fall back to a sequential scan of that batch in the main agent (per the Troubleshooting row "Sub-agent dispatch fails"). Slower, but the aggregation contract still holds because the main agent produces the same structured entries.

---

## Step 4: Classify findings

For each match, regardless of how it was found:

1. **Read the file** at the match location (Read tool), at minimum 20 lines around the match. Multi-platform code may need a wider window to capture surrounding `#if` blocks.

1.5. **Check the precondition pattern, if step 2.1 produced one.** When the inference ran with a precondition (removed lines were not self-sufficient), read the candidate's enclosing scope and test the precondition pattern against it. If the precondition is absent, classify **OK** and state which precondition was missing. Only candidates carrying BOTH the primary and the precondition remain eligible for BUG.

2. **Check for known intentional usages.**
   - This is in-context judgment by Claude. Common intentional uses (e.g., `try?` in test code where failure is acceptable, force-unwrap of an IBOutlet) are classified as OK. There is no suppression file to consult — every run re-judges from the source, so a usage that was intentional last month still has to read as intentional today.

3. **Classify** as one of:
   - **BUG:** matches the anti-pattern, correctness issue confirmed in this context.
   - **WATCH:** matches the anti-pattern but is contextually near-threshold or already has an architectural defense in place (e.g., the match sits inside a `@ViewBuilder` split that scoped a known crash, but if more conditions are added the scope could cross back into BUG territory). WATCH findings get a row in the Issue Rating Table with urgency typically ⚪ LOW or 🟢 MEDIUM and a documentation-only suggested fix (e.g., add a comment warning future maintainers about the threshold). Use WATCH when the code is correct today but the path to incorrect is short and foreseeable; use REVIEW when you can't tell.
   - **OK:** correct usage, no action needed (e.g., `as!` after a validated `is` check; strong `self` capture in a SwiftUI struct view).
     - **OK (CANON):** correct *and* it is the shape the BUG findings in this same sweep should be made to look like — the codebase already solved this problem here. Tag it `OK (CANON)` and record its `file:line`. This is a sub-label of OK, not a fifth classification: it changes nothing about the verdict, only what the report can cite. It applies when the pattern is fixed in some copies and not others, which happens whenever a past fix landed on one site and missed its siblings.
       A worked example — a real run where two correct siblings existed and five copies had drifted — is in [examples/canon-reference-implementation.md](examples/canon-reference-implementation.md).
       🛑 **Most sweeps have no CANON site, and that is the normal result.** A young repo, a first sweep against a uniformly-broken pattern, or a genuinely novel bug will have no correct instance to point at. Tag CANON only when an OK site is unmistakably the same shape solving the same problem — never to satisfy this rule. Inventing a reference is worse than having none, because every BUG row would then be told to converge on something that isn't actually the answer. When there is no CANON site, everything below is a no-op and the report is exactly what it was before this label existed.
   - **REVIEW:** context unclear, requires human judgment.

Classify each match individually. Do not batch-judge a directory or file.

**If — and only if — a CANON site was found, every BUG row's `Suggested fix` cites it** (`file:line`) instead of describing a fix from scratch. A finding whose remedy already exists in-repo is propagation, not design: rate it `verified` rather than `probable`, and rate Risk-of-Fixing and Fix Effort against copying the reference, not against inventing one. Omitting the citation when one exists is how a codebase ends up with several drifted copies of something a sibling already got right. When no CANON site was found, write the suggested fix normally — this adds no step.

---

## Step 5: Generate report

The report shape depends on `recon_report_mode` from Step 2.5:

### `none` — no-echo note

Emit ONE LINE in conversation. No file. Suggested template:

```
No echoes found for [pattern name]. Scanned [N] candidate sites against [search scope]; all are either the original-fix site or non-matches. Pattern appears localized.
```

Stop. Do not invoke Write.

### `inline` — lightweight 1-5 finding report

Render in conversation, not to a file. Single Issue Rating Table with one row per BUG. Skip OK/REVIEW/WATCH sections unless something interesting appears (and if it does, document it inline, not in a separate section). Suggested shape:

```markdown
## bug-echo: [pattern name] — [N] echo(es) found

| # | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast | Effort | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | ... | ... | ... | ... | ... | ... | ... | Open |

**Detail:**
- **[N]. [short description]** at `path/file.swift:[line]`. [Why this is a bug, 1-2 sentences.] Suggested fix: [1-2 sentences.]

**Recon classifications:** [N] BUG, [N] OK (cite line numbers if relevant), [N] REVIEW.
```

🛑 **A CANON site is the one OK finding inline mode never omits.** The "skip the OK section" rule above exists to suppress noise, but a reference implementation is the opposite of noise — it is the answer to every BUG row in the table. Render it as a `**Reference implementation:** path/file.swift:[line]` line beneath the table whenever one was found.

After rendering, proceed to Step 6 (follow-up).

### `full` — full audit report (6+ candidates)

Write the report directly to `<output_dir>/YYYY-MM-DD-bug-echo-<slug>.md` using the Write tool, where `<output_dir>` is the path Pre-flight Step 3 resolved (default `.agents/research/`, or the `output=<path>` override from the invoking prompt). The slug is a short kebab-case description of the pattern.

### Report format (full mode)

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
- WATCH findings: [N]
- OK findings: [N]
- REVIEW findings: [N]

## BUG Findings

### Issue Rating Table

| # | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | [short description] | [🔴 CRITICAL / 🟡 HIGH / 🟢 MEDIUM / ⚪ LOW] | [⚪ Low / 🟡 High / 🔴 Critical] | [⚪ Low / 🟢 Medium / 🟡 High / 🔴 Critical] | [🟠 Excellent / 🟢 Good / 🟡 Marginal / 🔴 Poor] | [⚪ 1 file / 🟢 N files / 🟡 N+ files] | [Trivial / Small / Medium / Large] | Open |

The Status column is `Open` on first display. After fixes are applied, the column updates to `Fixed`, `Deferred`, or `Skipped`.

**On the missing `Target` column.** Some Issue Rating Table conventions carry a tenth `Target` column naming the file or component. bug-echo deliberately omits it: every finding here is a single match site whose `file:line` is printed directly beneath the table in the detailed findings, so a Target column would restate what the row already points at. If you are reconciling a bug-echo report against a project convention that expects Target, read the detailed-findings path as that column.

### Detailed findings

For each BUG finding:

```
**[N]. [short description]**

`path/to/file.swift:[line]`

[code snippet, 5-10 lines around the match]

**Why this is a bug:** [1-2 sentences]
**Suggested fix:** [1-2 sentences. If a CANON site exists, cite it — "mirror `path/File.swift:311`" — rather than describing a fix from scratch.]
```

If the sweep produced any `OK (CANON)` sites, name them once directly beneath the BUG table so the reader sees the reference before the individual findings:

```
**Reference implementation:** `path/to/File.swift:311` — this codebase already solves this pattern here. The findings below should converge on it rather than each inventing a fix.
```

## WATCH Findings (near-threshold, defensive only)

WATCH findings use the same Issue Rating Table shape as BUG, but typically with documentation-only suggested fixes (e.g., add a comment near the threshold warning future maintainers, or convert the conditional shape to one that scales better). They are not release-blocking; they record what's currently safe but easy to break.

### Issue Rating Table

Same columns as the BUG table above. Urgency is typically ⚪ LOW or 🟢 MEDIUM.

### Detailed findings

For each WATCH finding:

```
**[N]. [short description]**

`path/to/file.swift:[line]`

[code snippet, 5-10 lines around the match]

**Why this is WATCH not BUG:** [1-2 sentences explaining the architectural defense or near-threshold status]
**Suggested fix (defensive, not urgent):** [1-2 sentences, typically a comment or refactor recommendation]
```

## OK Findings (intentional, no action needed)

For each OK match, one line:
- `path/to/file.swift:[line]` - [reason it's OK]

## REVIEW Findings (need human judgment)

For each REVIEW match:
- `path/to/file.swift:[line]` - [why context is unclear]
```

The report is human-readable and self-contained — write it for a person, not for a parser. There is no machine-readable sidecar, so don't emit one alongside it.

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
6. After all selected fixes are applied, present an AskUserQuestion:

   ```
   Question (header: "Commit"): "Commit these bug-echo fixes now?"
   Options:
   - "Yes, commit as `bug-echo: applied N fixes from <slug>`" (Recommended).
     Stage only the files this skill edited (track them as Step 6.4 applies
     each Edit), then `git commit` via Bash with the message
     `bug-echo: applied <N> fixes from <slug> report`. The commit message
     references the report at `.agents/research/<date>-bug-echo-<slug>.md`
     so the commit and the report are linked.
   - "Leave uncommitted". The user commits later. Note: re-running bug-echo
     will trip Pre-flight's clean-tree check until these changes are
     committed or reverted.
   - "Cancel". Stop without committing.
   ```

   On "Yes, commit": run `git add <file1> <file2> ...` for only the files Step 6.4 edited (do not stage anything else), then `git commit -m "bug-echo: applied <N> fixes from <slug> report"`. Verify with `git status --porcelain` that only the bug-echo-edited files were committed.

Re-display the rating table at the end of the fix session with all Status columns populated.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Diff parsing fails because the recent edit is not a bug fix (rename, comment change, formatting) | Pattern self-validation will fail. Fall back to Step 2A and ask the user to describe the pattern manually. |
| Too many matches | Narrow the scope by passing a directory in the user's pattern description (e.g., `Sources/Features/Auth/`). |
| AST-grep not installed | Use regex via the Grep tool. Install with `brew install ast-grep` for higher precision on Swift if precision matters. |
| All matches classified OK | Pattern is localized to the original file. Report zero BUG findings and stop. That's a successful run, not a failed one. Note: Step 2.5's recon scout should now catch this case earlier with the `none` report mode. |
| Recon scout shows 0 candidates but I'm sure there are siblings | Your search pattern is too narrow. Broaden it (e.g., drop a suffix qualifier, switch from `let` to `let\|var`) and re-run Step 2.5. If still 0, the pattern was already localized to the just-fixed site. |
| Sub-agent dispatch fails | Fall back to sequential scan in the main agent. Slower but functional. |
| Mixed intentional and buggy matches | Classify each individually using Step 4 rules. Do not batch-judge. |
| Pattern matches across `#if os(...)` boundaries | Honor platform conditionals during classification. Code inside the wrong `#if` block is OK, not BUG. |

---

## When inference fails: delegate to bug-prospector

If Step 2B's self-validation fails (the inferred pattern doesn't match the pre-fix file) and Step 2A's user-described mode also doesn't apply (no recent fix, no described pattern), bug-echo's job is done — it has no diff to work with. Rather than synthesize a catalog, the skill should suggest the right tool for the next step:

```
AskUserQuestion with questions:
[
  {
    "question": "I can't infer a pattern from a recent fix or description. Run bug-prospector instead?",
    "header": "Next",
    "options": [
      {"label": "Yes, run bug-prospector", "description": "It uses 7 forward-looking lenses to find bugs without needing a fix to reference"},
      {"label": "I'll describe a pattern manually", "description": "Restart bug-echo in Step 2A described mode"},
      {"label": "Cancel", "description": "Stop"}
    ],
    "multiSelect": false
  }
]
```

If "Yes, run bug-prospector": instruct the user to invoke `/bug-prospector` (skill must be installed separately — see [github.com/Terryc21/bug-prospector](https://github.com/Terryc21/bug-prospector)).

bug-prospector and bug-echo cover opposite halves of the bug-finding loop. bug-echo is reactive (after a fix); bug-prospector is forward-looking (before a fix). When bug-echo can't infer, the user's question is "what could go wrong?" not "where else does this live?" — that's bug-prospector's job, not a missing feature in bug-echo.

---

## Metadata keys

The frontmatter declares two metadata keys for cross-skill coordination across Coffee & Code's audit family (bug-prospector, radar-suite, workflow-audit, unforget):

- **`tier`** — where the skill operates in a typical workflow.
  - `execution` (used by bug-echo) — runs in response to a concrete event (a fix landed, a release approaches). Produces an artifact (a report, a commit) the user acts on directly.
  - `planning` — runs before an event to inform a decision (e.g., bug-prospector's forward-looking lenses, unforget's deferred-work survey).
  - `review` — runs over a finished artifact to grade or audit it (e.g., radar-suite's capstone, app-store-code-review).

- **`category`** — the domain the skill targets.
  - `debugging` (used by bug-echo) — finds bugs, traces causes, or generalizes fixes.
  - Other current values in the family: `architecture`, `release-prep`, `documentation`, `ui-audit`, `data-model`.

These keys are descriptive metadata only — no router currently reads them at activation time. They exist so users browsing multiple companion skills can recognize the workflow stage at a glance. If a future router or skill-family index starts reading them, the canonical list lives in the radar-suite README.
