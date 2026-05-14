# bug-echo

![Last commit](https://img.shields.io/github/last-commit/Terryc21/bug-echo) ![Stars](https://img.shields.io/github/stars/Terryc21/bug-echo?style=flat) ![Issues](https://img.shields.io/github/issues/Terryc21/bug-echo) ![License](https://img.shields.io/github/license/Terryc21/bug-echo) ![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-Plugin-blueviolet)

**A Claude Code skill that runs after a fix lands, infers the anti-pattern from your diff, validates the pattern against the pre-fix file, and scans the rest of the codebase for sibling instances. Each match is read in context and classified BUG / OK / REVIEW.**

> **Companion:** [bug-prospector](https://github.com/Terryc21/bug-prospector) — runs *before* a fix to find bugs you haven't seen yet. The two skills cover opposite halves of the bug-finding loop.

bug-echo and pattern-based linters are complementary, not competitive: linters check every file against pre-built rules on every save; bug-echo runs once per fix to scan for siblings of a bug that just demonstrated itself. **A thorough audit uses both.**

Built while shipping [Stuffolio](https://stuffolio.app), an iOS/macOS app currently at build 33. Free, open source, Apache 2.0.

## TL;DR

- **What:** A Claude Code skill that runs *after* a bug fix, infers the anti-pattern from the diff, and scans the codebase for sibling instances. Each match classified BUG / OK / REVIEW with file:line citations.
- **Why:** The pattern bug-echo scans for is one that *just demonstrated itself in your codebase*. After-the-fact pattern matching beats catalog matching because the pattern was selected by reality, not by a rule author guessing.
- **Install:** Two `/plugin` commands in Claude Code; then `/bug-echo` is available in any project.
- **Try first:** After your next bug fix, run `/bug-echo`. It reads the diff, self-validates the inferred pattern, and scans in ~2 minutes on a typical Swift codebase.
- **Example output:** [a real sibling-bug scan on Stuffolio](skills/bug-echo/examples/2026-05-03-bug-echo-deep-viewbuilder-crash.md). Also: [describe-mode example on TypeScript](skills/bug-echo/examples/describe-mode-await-in-forEach.md).
- **Maturity:** v1.0.0; used through real App Store submission cycles; works on any language for pattern construction, with platform-conditional handling currently Swift-specific.

## What bug-echo is for vs what linters are for

bug-echo and linters are complementary — they catch different bugs at different times in your workflow.

**Pattern-based linters (SwiftLint, ESLint, custom rule sets)** check every file against a pre-built catalog on every save. The catalog reflects what someone *thought* was a bug at the time the rule was written. Linters are fast, cheap, and catch a real class of style and pattern violations that bug-echo would never run for (you wouldn't fire a sibling scan for every missing `@MainActor`). **They will find issues bug-echo won't.**

**bug-echo** flips the direction. It runs *once per fix*, in response to a bug that **just demonstrated itself in your codebase, fifteen minutes ago, in production code you wrote**. The fix is the proof. After-the-fact pattern matching is dramatically more accurate than catalog matching because the pattern was selected by reality, not by a rule author guessing. **It will find sibling instances of bugs your linter has no rule for** — because the bug was novel enough to need fixing in the first place.

The trick that makes this practical: bug-echo self-validates the inferred pattern against the pre-fix version of the file before scanning. If the pattern doesn't match the bug it was extracted from, the skill stops rather than scanning with a bad search. You never get findings from a misinterpreted diff.

| What linters do better | What bug-echo does better |
|---|---|
| Run on every save (cheap, continuous) | Run once per fix (focused, narrow) |
| Catalog of well-understood violations | Pattern from your most recent real bug |
| Catch style and pattern violations | Catch siblings of the bug you just fixed |
| Mature ecosystem | Novel-bug propagation; no catalog needed |

If your project already uses SwiftLint or another pattern-based audit, keep it. bug-echo runs at a different moment for a different purpose.

## bug-echo vs. bug-prospector — which should you use?

Both have "bug" in the name; they answer different questions and run at different times.

| | bug-echo | [bug-prospector](https://github.com/Terryc21/bug-prospector) |
|---|---|---|
| **When you run it** | Right after you fix a bug | Before a release, after a crash report, during exploration |
| **What it asks** | "Where else does this exact thing live?" | "What could go wrong?" |
| **What it needs** | The diff of a fix you just committed | Just code |
| **Pattern source** | The pattern is inferred from your actual diff and validated against the pre-fix file | 7 forward-looking lenses (assumptions, state machines, boundaries, lifecycle, errors, time, platform) |

Many people run both — bug-prospector before releases, bug-echo after every bug fix. They complement each other.

## Install

Two commands in Claude Code, run one at a time:

```
/plugin marketplace add Terryc21/bug-echo
```

```
/plugin install bug-echo@bug-echo
```

> **Why two commands?** Claude Code's slash-command dispatcher treats the second `/plugin` as text inside the first command and tries to clone a repo with a malformed name. The error message ("SSH authentication failed") is misleading. Run them one at a time.

After installing, the easiest way to try it: wait until your next real bug fix, commit (or stage) it, then run:

```
/bug-echo
```

The skill reads the diff, self-validates the inferred pattern against the pre-fix file, and scans in ~2 minutes on a typical Swift codebase. You'll get a real report you can act on.

### Optional: install bug-prospector alongside

bug-echo runs after a fix. [bug-prospector](https://github.com/Terryc21/bug-prospector) runs before one — same workflow loop, opposite end. Most users want both:

```
/plugin marketplace add Terryc21/bug-prospector
/plugin install bug-prospector@bug-prospector
```

(Same one-at-a-time rule applies.)

## Workflow

The expected loop is short:

1. Fix a bug. Commit (or stage) the fix.
2. Run `/bug-echo`.
3. Skill reads the diff, infers a regex from removed lines, validates against `git show HEAD~1:path/to/file` (or the unstaged baseline), then scans the codebase.
4. Each match is read in a 20-line window and classified individually:
   - **BUG** — same anti-pattern, contextually a real problem
   - **OK** — pattern matches but the surrounding code makes it correct or intentional (e.g., the matched line is inside a `#if os(iOS)` block on a Swift codebase where the pattern is macOS-specific)
   - **REVIEW** — context insufficient for a confident call; you decide
5. Optional guided fix flow with explicit approval per finding. Skill never edits without confirmation.

You can also invoke the skill in **describe mode** (`/bug-echo "<pattern description>"`) when there's no recent diff. Useful for hypothesis-driven sweeps, for fixes whose diff is too noisy to infer from cleanly, or when the bug is conceptual ("anywhere we use `Task { ... }` inside a SwiftUI view body without `[weak self]`").

## A worked example

I fixed a SwiftUI captured-`self` staleness bug. Save handler called `dismiss()` on macOS inline in a `NavigationSplitView` — which closes the host window. The bug was in this line, repeated in two slightly different shapes:

```swift
// Pre-fix (buggy)
ScoutResultView(
    onSaveComplete: saveCompletionOverride ?? { dismiss() },
)

// Post-fix
let resolved: () -> Void = saveCompletionOverride ?? { dismiss() }
ScoutResultView(
    onSaveComplete: resolved,
)
```

The `??` looks harmless, but inline in a SwiftUI body it captures `self` lazily. On a re-render, the captured `self` was stale (override = nil) even though the live one had it set, so the dismiss fallback fired and took the window. Snapshotting at body time fixes it because the closure captures a value, not `self`.

After committing, I ran `/bug-echo`. Here's what the skill did:

1. **Inferred the pattern.** Read the diff and constructed the regex `\w+\s*\?\?\s*\{[^}]*dismiss\(\)` — narrow enough to catch the staleness shape, broad enough to catch syntactic variants.
2. **Self-validated.** Checked the pre-fix file (`git show HEAD~1:Sources/Features/StuffScout/StuffScoutView.swift`) and confirmed the regex matched the original buggy line. If it hadn't, the skill would have stopped.
3. **Scanned 596 Swift files.** Three matches, two seconds.
4. **Classified each in context.** One was the fix itself (OK). One was inside a regular function, not a SwiftUI body (OK; no captured-`self` lifecycle). **One was a sibling bug**: a Done button in the same file using `(dismissOverride ?? { dismiss() })()` inside a `Button` action, exact same staleness pattern, different syntactic wrapper.
5. **Wrote a markdown report** to `.agents/research/2026-05-06-bug-echo-swiftui-captured-self-staleness.md` with file:line citations, severity ratings, and a suggested fix for the BUG finding.

That sibling had been in production code for weeks. It would have hit a user eventually. bug-echo found it in two minutes.

The full sample report from a different real run is here: [example output](skills/bug-echo/examples/2026-05-03-bug-echo-deep-viewbuilder-crash.md). It demonstrates the standard output format (BUG findings, WATCH classifications, the issue rating table, suggested fixes).

A second example showing **describe-mode** on a TypeScript codebase (a senior dev sweeps for `await` inside `Array.forEach` before fixing): [describe-mode example](skills/bug-echo/examples/describe-mode-await-in-forEach.md).

## Pattern construction details

**From a diff:** the skill parses unified diff format, extracts the removed (`-`) lines, identifies a distinctive substring shared across the bug instances, and constructs a regex narrow enough to avoid false positives but broad enough to catch reasonable syntactic variation. It deliberately avoids matching on whitespace or trailing punctuation. If your diff includes unrelated cleanup (renames, formatting, comment additions), the inferred pattern will be too narrow; switch to describe mode in that case.

**Self-validation:** before scanning, the skill compares the inferred pattern against the pre-fix file. If the pattern doesn't match anything there, it stops and reports the failure. There's no scanning with a bad pattern.

**Classification:** each match is read in at least a 20-line window so the skill can see the surrounding context. A `try?` inside test code is OK; the same `try?` inside production code is BUG. A force-unwrap on an IBOutlet is OK; the same on a network response is BUG. The skill doesn't batch-judge.

**Platform conditionals (Swift):** if a pattern matches inside a `#if os(...)` block that excludes the platform where the pattern is buggy, the match is automatically OK. This avoids false flags on Universal codebases where the same code shape is correct on iOS and incorrect on macOS (or vice versa).

### Optional: AST-grep for higher precision

bug-echo defaults to regex via the Grep tool. Regex is fast and catches most patterns. AST-grep is meaningfully better when:

- The pattern spans multiple lines and indentation varies between match sites
- You want to match a specific syntactic construct (a `Button` action closure, a `@MainActor` function call) rather than a textual shape
- You're in a codebase where formatter runs have produced inconsistent whitespace
- The anti-pattern depends on AST structure (e.g., "any closure assigned to a `let` whose type is `() -> Void`")

If `ast-grep` is on PATH, the skill detects it and uses it automatically. To install: `brew install ast-grep`. Regex still works fine if you skip this; the skill notes which tool produced the matches in the report header.

## Output format

Reports go to `.agents/research/YYYY-MM-DD-bug-echo-*.md` in your project. Standard format across the radar/audit ecosystem:

- File and line citations for every claim
- 9-column rating table: severity, urgency, risk-of-fix, risk-of-no-fix, ROI, blast radius, fix effort, status, axis classification
- 3-axis classification: Axis 1 (release-blocking), Axis 2 (quality), Axis 3 (hygiene)
- Suggested fix for each BUG finding when one is mechanical

### Reading the reports

The 9-column rating table needs a wide terminal (~180 chars) to render as a horizontal table. In a narrower window the cells stack vertically and the report becomes harder to scan. For best readability:

- **GitHub or GitLab**: open the report file in the web UI; tables render natively.
- **Markdown viewer apps**: [MacDown](https://macdown.uranusjr.com/) (Mac, free), [Marked 2](https://marked2app.com/) (Mac, paid), [Obsidian](https://obsidian.md/) or [Typora](https://typora.io/) (cross-platform).
- **VS Code**: built-in Markdown Preview (cmd-shift-V on Mac).

If tables look broken in your terminal (rendered as vertical blocks instead of horizontal rows), widen the window or use one of the apps above.

## When to skip the skill entirely

A few cases where running it isn't worth the tokens:

- Trivial fixes (typos, single-character changes, isolated state).
- Fixes to one-off code with no callers.
- Migration cleanups where the pattern is on its way out and finding more instances doesn't change the migration plan.
- Fixes whose diff is dominated by unrelated cleanup. The inferred pattern will be noisy; either clean the diff or use describe mode.

Rule of thumb: if the bug surprised you, run bug-echo. Surprise is a signal the bug shape isn't on your mental list of things to look for, which makes it the kind of pattern most likely to repeat unspotted elsewhere.

## CI and pre-commit integration

bug-echo isn't a CI-shaped tool. It needs a real fix to compare against, ideally with the pre-fix version available via git, and the per-match classification step uses Claude — that's not something you want firing on every commit. Two options for automation:

- **Manual gate.** Add a step to your release checklist that runs `/bug-echo` after each merged bug-fix PR. Captures sibling bugs before they reach a release branch.
- **Selective trigger.** A pre-merge hook that runs only when the commit message contains a specific tag (e.g., `[bug-fix]`). The hook calls Claude Code via the `claude` CLI. Cost-effective for teams that label bug-fix commits.

Don't put bug-echo on every commit. The pre-fix-vs-post-fix premise breaks down for ordinary feature work, and the budget impact is real.

## Honest limits

The skill catches what regex (or AST) can express, classified with a 20-line context window and Claude's judgment. Things it can't catch:

- Bugs that exist in the *relationship between two correct files* (cross-context mutations, race conditions, distributed-state issues). Each individual file passes; the bug is in the coordination. No code shape to match.
- Bugs whose pattern is heavily overloaded with false positives. If the regex catches 200 matches and 195 are OK, the report is hard to act on. Switch to describe mode and tighten manually.
- Bugs whose fix doesn't have a recognizable shape (a one-line wording change in user-facing string content, a single-character constant tweak, a comment update). Nothing to extract.

A clean bug-echo run means zero matches for the inferred pattern. It does not mean zero bugs.

**Where to look for the bugs bug-echo won't find:** pattern-based linters (SwiftLint, etc.) catch single-file style violations; [bug-prospector](https://github.com/Terryc21/bug-prospector) catches forward-looking behavioral assumptions; runtime profiling (Instruments, sanitizers) catches concurrency and memory issues; targeted unit tests catch business-logic correctness. bug-echo covers the sibling-bug-after-a-fix slot in that picture.

## Advanced: the post-fix sweep (three skills together)

For high-stakes fixes (P0 incidents, security-adjacent bugs, fixes to widely-shared code), bug-echo composes with two other skills:

| Stage | Skill | Behavior |
|---|---|---|
| 1. Surface | [unforget](https://github.com/Terryc21/unforget) | Lists deferred items, including the row about to be marked Fixed. Forces you to reconcile against your tracker before declaring the bug closed. |
| 2. Verify | [radar-suite](https://github.com/Terryc21/radar-suite) | Runs an audit focused on the area the fix touched. Catches cases where the deferred row is stale (the fix shipped weeks ago, nobody updated the ledger) or the fix is incomplete (passes locally, fails another check). |
| 3. Generalize | bug-echo (this skill) | Sweeps for sibling instances. Closes the bug class, not just the individual bug. |

The shape is **surface → verify → generalize**: confirm the issue is real and current, confirm the fix is real, then look for siblings. It's slower than running bug-echo alone (typically 60-90 minutes for a real chain), but for bugs where shipping an incomplete fix would be expensive, it's the most thorough close-out I've found. Standalone bug-echo is fine for normal fixes.

A real chain example: an iPhone-only crash deferred for a month was marked Fixed by `unforget`, then `radar-suite focus on collapsibleSectionsStack` reported the fix had actually shipped weeks earlier in two specific commits and the ledger was stale. Closed as Fixed. `bug-echo "VStack with 12+ if-conditional children in one scope"` then found one BUG (a list-row view with 16 conditional children) and three WATCH sites at 10-12. Fixed the BUG with the same split pattern. Total time ~90 minutes.

## Other Claude Code skills

Companion tools built on the same shipping-real-software loop:

- [**bug-prospector**](https://github.com/Terryc21/bug-prospector) — runs *before* a fix; 7-lens forward-looking audit. Companion skill.
- [**radar-suite**](https://github.com/Terryc21/radar-suite) — 6 audit skills for iOS/macOS Swift codebases. Covers data models, time-bomb code that fails on aged data, UI navigation, backup/restore round-trips, visual quality, and a capstone that aggregates the rest.
- [**workflow-audit**](https://github.com/Terryc21/workflow-audit) — 5-layer audit of SwiftUI user flows. Finds dead ends, dismiss traps, unwired features, and platform parity gaps.
- [**tutorial-creator**](https://github.com/Terryc21/tutorial-creator) — turns a file from your project into an annotated tutorial with vocabulary tracking, pre/post tests, and gap analysis. Works for any language.
- [**unforget**](https://github.com/Terryc21/unforget) — consolidates deferred work (paused plans, audit findings, observed bugs) into one structured file.
- [**prompter**](https://github.com/Terryc21/prompter) — rewrites your Claude Code prompt for clarity before acting.

All free, all Apache 2.0, all built while shipping Stuffolio.

## Status

Current version: 1.0.0. Built primarily for Swift/SwiftUI. The pattern construction is language-agnostic; the platform-conditional handling is currently Swift-specific.

Planned for v1.1: a built-in catalog mode for common Swift/SwiftUI anti-patterns (run when there's no recent fix to infer from), JSON sidecar output for chaining into downstream skills, recurrence detection across prior reports (catches bug classes that keep returning despite individual fixes), and a `known-intentional.yaml` user file for explicit suppression of patterns the user has confirmed are not bugs.

## License

Apache 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

## Author

Terry Nyberg, [Coffee & Code LLC](https://stuffolio.app/). If bug-echo catches a real bug for you, [a coffee](https://buymeacoffee.com/stuffolio) is appreciated. Issue reports about what worked or didn't are even more useful.
