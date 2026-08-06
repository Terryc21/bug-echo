# bug-echo

![Version](https://img.shields.io/github/v/tag/Terryc21/bug-echo?label=version) ![Last commit](https://img.shields.io/github/last-commit/Terryc21/bug-echo) ![Stars](https://img.shields.io/github/stars/Terryc21/bug-echo?style=flat) ![Issues](https://img.shields.io/github/issues/Terryc21/bug-echo) ![License](https://img.shields.io/github/license/Terryc21/bug-echo) ![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-Plugin-blueviolet)

**You just fixed a bug. bug-echo asks the obvious next question: does this same buggy pattern appear anywhere else? It looks at the fix you just made, works out what the underlying pattern was, and searches the rest of your project for that same pattern hiding in other spots. Then it hands you a plain report: here's a real one, here's a false alarm, here's one you should look at yourself.**

> **Companion:** [bug-prospector](https://github.com/Terryc21/bug-prospector) hunts for bugs you *haven't* found yet. bug-echo runs *after* you fix one. Together they cover both halves of the job.

Built while shipping [Stuffolio](https://stuffolio.app), an iOS/macOS app, through real App Store submission cycles. bug-echo is free, open source, Apache 2.0.

*~7 min read. Scan the TL;DR if you only have 30 seconds.*

## New here? Start with this

**The problem it solves.** When you fix a bug, you fix it in one spot. But the same buggy pattern often lives in three other places you've forgotten about: copy-pasted, re-typed from habit, or left behind when a refactor or an API change didn't reach every site. Those copies sit quietly in your project until one of them breaks for a user weeks later. Finding them by hand means remembering every place the same shape could occur, which is exactly the thing humans are bad at.

**What bug-echo does.** Right after you fix a bug, you run one command. bug-echo:

1. Looks at the change you just made and works out what the underlying buggy pattern was.
2. Double-checks its own understanding against the broken version of the file. If it got the pattern wrong, it stops instead of wasting your time.
3. Searches your whole project for other places with that same pattern.
4. Reads each one and tells you which are real bugs, which are fine, and which need your eyes.

You get a short written report you can act on. That's the whole loop.

**Why this beats a normal code checker.** Tools like linters check your code against a fixed list of known problems that someone wrote down in advance. bug-echo is different. The problem it looks for is one that *just proved it was real*, in your own code, fifteen minutes ago. Nobody had to predict it. Reality picked the pattern for you. That's why it catches bugs your other tools have no rule for. (More on this below. The two work well together.)

### A few terms, once

If some words here are new, this is the whole vocabulary in one place:

- **Skill / plugin.** A skill is a set of instructions Claude Code knows how to follow. Once installed, you type `/bug-echo` and Claude does the work. You don't memorize anything.
- **A "fix" / a "diff."** When you change code, the before-and-after difference is called a *diff*. bug-echo reads your most recent diff to learn what the bug was.
- **Sibling bug.** Another spot in your project with the same underlying buggy pattern as the one you just fixed.
- **BUG / OK / REVIEW.** How bug-echo labels each spot it finds: a real problem, a false alarm, or "not sure, you decide."

That's enough to use it. The rest of the README goes deeper for people who want the mechanics.

## TL;DR

- **What:** A Claude Code skill you run right after fixing a bug. It learns the buggy pattern from your fix and searches the rest of your project for that same pattern elsewhere. Each hit is labeled BUG / OK / REVIEW with an exact file and line number.
- **Why it works:** The pattern it searches for is one that just proved itself real in your code. That beats checking against a pre-written list, because the pattern was chosen by an actual bug, not by someone guessing in advance.
- **Install:** Two `/plugin` commands in Claude Code. Then `/bug-echo` works in any project.
- **Try it:** After your next bug fix, run `/bug-echo`. It takes about 2 minutes on a typical codebase.
- **Example output:** [a real sibling-bug scan on Stuffolio](skills/bug-echo/examples/2026-05-03-bug-echo-deep-viewbuilder-crash.md). Also: [describe-mode example on TypeScript (synthesized)](skills/bug-echo/examples/describe-mode-await-in-forEach.md).
- **See it work:** [a real run that caught a 2-week-old sibling bug in 2 minutes](#a-worked-example).
- **Maturity:** v1.3.4, used through real App Store submission cycles. Works in any language for building the search pattern, with a few Apple-specific niceties currently Swift-only.
- **Recent releases:** v1.3.4 trimmed the skill file to execution-only content (no behavior change). v1.3.0 brought large-codebase hardening. On a big project swept across several sessions, bug-echo now skips sites it already fixed in a prior run (checked against git history, then re-verified against live source so a reintroduced bug is still caught), and offers to tighten an over-broad pattern before classifying hundreds of matches. Both are threshold-gated, so small projects run exactly as before. Earlier, [the v1.2.0 recon scout](skills/bug-echo/examples/recon-scout-rationale.md) added report-shaping that cuts about 39% of runs to a one-line note or short inline table instead of a full report file.

## bug-echo vs. a linter (they work together)

Short version: keep both. They catch different bugs at different moments.

A **linter** (SwiftLint, ESLint, and similar) checks every file, every time you save, against a fixed list of known problems. It's fast, cheap, and constant. It catches a whole class of issues bug-echo would never bother running for. You wouldn't fire off a whole-project scan for every missing `@MainActor`. **A linter will find issues bug-echo won't.**

**bug-echo** flips the direction. It runs *once, after a fix*, and only looks for the specific pattern you just fixed, a pattern that **just proved itself real in your own code, fifteen minutes ago**. The fix is the proof. That's far more accurate than checking against a fixed list, because the pattern was chosen by an actual bug rather than by a rule author guessing. **It finds copies of a bug your linter has no rule for**, because the bug was novel enough to need fixing in the first place.

The safeguard that makes this trustworthy: before searching, bug-echo checks that it understood the bug correctly by testing its guess against the broken version of the file. If the guess doesn't match, the skill stops rather than searching for the wrong thing. You never get a report built on a misread.

| A linter is better at | bug-echo is better at |
|---|---|
| Running on every save (cheap, continuous) | Running once per fix (focused, narrow) |
| A list of well-understood problems | The specific bug you just hit |
| Style and formatting rules | Finding copies of your latest real bug |
| A mature, established ecosystem | New bugs with no rule written for them |

If your project already uses SwiftLint or another pattern-based checker, keep it. bug-echo runs at a different moment for a different purpose.

## bug-echo vs. bug-prospector — which do I use?

Both have "bug" in the name, but they answer different questions and run at different times.

| | bug-echo | [bug-prospector](https://github.com/Terryc21/bug-prospector) |
|---|---|---|
| **When you run it** | Right after you fix a bug | Before a release, after a crash, while exploring |
| **The question it asks** | "Where else does this same buggy pattern appear?" | "What could go wrong that I haven't found yet?" |
| **What it needs** | The fix you just made | Just your code |
| **Where its pattern comes from** | Learned from your actual fix and checked against the broken file | 7 forward-looking lenses (assumptions, state machines, boundaries, lifecycle, errors, time, platform) |

Many people run both: bug-prospector before releases, bug-echo after every fix.

## Install

These go into Claude Code itself, typed at the prompt where you'd normally ask it a question. Not Terminal.

**First**, add this repository as a source:

```
/plugin marketplace add Terryc21/bug-echo
```

You'll see a confirmation that the marketplace was added.

**Then**, install the plugin:

```
/plugin install bug-echo@bug-echo
```

Run these one at a time. If you paste both at once, Claude Code reads the second line as part of the first command and fails with a confusing "SSH authentication failed" message.

**To check it worked:** type `/` and look for `bug-echo` in the list that appears.

The easiest way to try it: wait until you next fix a real bug, save that fix to git (commit it, or just stage it), then run:

```
/bug-echo
```

It reads your fix, works out what the underlying pattern was, and looks for other places in your project with the same pattern. You'll have a report you can act on in about two minutes.

Worth knowing before you start: bug-echo needs a git repository, and it works best right after a real fix — that fix is the evidence it learns the pattern from.

### Optional: install bug-prospector too

bug-echo runs after a fix. [bug-prospector](https://github.com/Terryc21/bug-prospector) runs before one, the same loop from the opposite end. Most people want both:

```
/plugin marketplace add Terryc21/bug-prospector
/plugin install bug-prospector@bug-prospector
```

(Same one-at-a-time rule applies.)

## How you'll actually use it

The loop is short:

1. Fix a bug. Save the fix (commit or stage it).
2. Run `/bug-echo`.
3. bug-echo reads your fix, works out the buggy pattern, double-checks its understanding against the broken version, then searches your project.
4. For each spot it finds, it reads the surrounding code and labels it:
   - **BUG** — the same pattern, and here it's a real problem.
   - **OK** — the code looks similar but is actually fine or intentional here (for example, the line sits inside an iOS-only block on a Mac-specific pattern).
   - **REVIEW** — not enough context to be sure; you decide.
5. Optionally, it can walk you through fixing each one, asking permission before every change. It never edits anything without your OK.

**No recent fix to point at?** You can also describe the pattern in your own words:

```
/bug-echo "anywhere we open a file but never close it"
```

Useful when you have a hunch to chase, when a fix's before-and-after is too messy to learn from cleanly, or when the bug is more of an idea than a single line ("anywhere we start a background task in a view without cleaning it up").

## A worked example

I'd just fixed a bug in Stuffolio. On one screen, a "save" action was accidentally closing the whole window on Mac instead of just finishing the save. The fix itself was one small change.

After saving the fix, I ran `/bug-echo`. Here's what it did:

1. **Figured out the buggy pattern** by reading my fix.
2. **Checked its own work** against the broken version of the file, to confirm it understood the bug correctly. If it hadn't, it would have stopped here.
3. **Searched all 596 files** in the project. Two seconds, three hits.
4. **Read each hit in context and labeled it.** One was my fix itself (OK). One only looked similar but was harmless (OK). **One was a real sibling bug**, a "Done" button on the *same screen* with the exact same buggy pattern, just written slightly differently.
5. **Wrote a report** with the file, the line number, how serious it was, and a suggested fix.

That sibling bug had been sitting in shipping code for weeks. It would have hit a real user eventually. bug-echo found it in two minutes.

The full sample report from a different real run is here: [example output](skills/bug-echo/examples/2026-05-03-bug-echo-deep-viewbuilder-crash.md). It shows the standard format (BUG findings, WATCH classifications, the rating table, suggested fixes). A second example shows **describe-mode** on a TypeScript codebase, where a developer sweeps for a known async mistake before fixing it: [describe-mode example, synthesized](skills/bug-echo/examples/describe-mode-await-in-forEach.md). It's marked synthesized because the pattern is real but the codebase is illustrative; the report shape and rules match real runs.

> **Want the exact code, the search it built, and the file paths?** They're in [Under the hood](#under-the-hood-technical-detail) below.

---

## Under the hood: technical detail

Everything below is for readers who want the mechanics: how the search pattern is built, how classification works, and how to compose bug-echo with other tools. If you just wanted to use the skill, you can stop above.

### The worked example, in full technical detail

I fixed a SwiftUI captured-`self` staleness bug. The save handler called `dismiss()` on macOS inline in a `NavigationSplitView`, which closes the host window. The bug was in this line, repeated in two slightly different shapes:

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

1. **Inferred the pattern.** Read the diff and built the regex (a text-search pattern) `\w+\s*\?\?\s*\{[^}]*dismiss\(\)`, narrow enough to catch the staleness shape, broad enough to catch syntactic variants.
2. **Self-validated.** Checked the pre-fix file (`git show HEAD~1:Sources/Features/StuffScout/StuffScoutView.swift`) and confirmed the regex matched the original buggy line. If it hadn't, the skill would have stopped.
3. **Scanned 596 Swift files.** Three matches, two seconds.
4. **Classified each in context.** One was the fix itself (OK). One was inside a regular function, not a SwiftUI body (OK; no captured-`self` lifecycle). **One was a sibling bug**: a Done button in the same file using `(dismissOverride ?? { dismiss() })()` inside a `Button` action, the exact same staleness pattern in a different syntactic wrapper.
5. **Wrote a markdown report** to `.agents/research/2026-05-06-bug-echo-swiftui-captured-self-staleness.md` with file:line citations, severity ratings, and a suggested fix for the BUG finding.

### Pattern construction details

**From a diff:** the skill parses unified diff format, extracts the removed (`-`) lines, identifies a distinctive substring shared across the bug instances, and builds a regex narrow enough to avoid false positives but broad enough to catch reasonable syntactic variation. It deliberately avoids matching on whitespace or trailing punctuation. If your diff includes unrelated cleanup (renames, formatting, comment additions), the inferred pattern will be too narrow; switch to describe mode in that case.

**Self-validation:** before scanning, the skill compares the inferred pattern against the pre-fix file. If the pattern doesn't match anything there, it stops and reports the failure. There's no scanning with a bad pattern.

**Classification:** each match is read in at least a 20-line window so the skill can see the surrounding context. A `try?` inside test code is OK; the same `try?` inside production code is BUG. A force-unwrap on an IBOutlet is OK; the same on a network response is BUG. The skill doesn't batch-judge.

**Platform conditionals (Swift):** if a pattern matches inside a `#if os(...)` block that excludes the platform where the pattern is buggy, the match is automatically OK. This avoids false flags on Universal codebases where the same code shape is correct on iOS and incorrect on macOS (or vice versa).

### Optional: AST-grep for higher precision

bug-echo defaults to regex via the Grep tool. Regex is fast and catches most patterns. AST-grep (a tool that matches code by its structure rather than its text) is meaningfully better when:

- The pattern spans multiple lines and indentation varies between match sites
- You want to match a specific syntactic construct (a `Button` action closure, a `@MainActor` function call) rather than a textual shape
- You're in a codebase where formatter runs have produced inconsistent whitespace
- The anti-pattern depends on code structure (for example, "any closure assigned to a `let` whose type is `() -> Void`")

If `ast-grep` is on PATH, the skill detects it and uses it automatically. To install: `brew install ast-grep`. Regex still works fine if you skip this; the skill notes which tool produced the matches in the report header.

### Scoping a run

bug-echo's scope is set by **which pattern it's scanning for**, not by a file path. The skill always scans the whole repo (Grep + Glob across all source files); the only question is how the pattern gets built.

| Goal | Command |
|---|---|
| Sweep for siblings of the bug you just fixed | `/bug-echo` (after `git commit` or `git add`) |
| Hypothesis-driven sweep (no recent fix) | `/bug-echo "<pattern description>"` |
| Sweep but write the report elsewhere | `/bug-echo output=docs/audits/` |
| Sweep with explicit AST-grep precision | `/bug-echo --ast-grep` (auto-detected if `ast-grep` is on PATH) |

**Fresh vs prior history.** Every bug-echo run is fresh by design. The skill re-reads the diff (or the description), re-validates the inferred pattern against the pre-fix file, and re-scans the codebase. There's no cache of previous runs and no resume mode. Prior reports live in `.agents/research/` and can be compared by hand, but the skill won't auto-skip findings it flagged last time. This is deliberate: if the pattern is real, finding it again on the next run is a feature, not noise. It tells you the sibling never got fixed. A "recurrence detection across prior reports" mode is planned for a future release; today, you compare reports manually.

## Output format

Reports go to `.agents/research/YYYY-MM-DD-bug-echo-*.md` in your project by default. The `.agents/research/` directory is a convention shared with radar-suite, bug-prospector, and other Coffee & Code audit skills; if your project doesn't use it, the skill creates it. Override the location by passing `output=<path>` in the invoking prompt (for example, `/bug-echo output=docs/audits/`). Standard format across the radar/audit ecosystem:

- File and line citations for every claim
- 9-column rating table: #, Finding, Urgency, Risk: Fix, Risk: No Fix, ROI, Blast Radius, Fix Effort, Status. The Status column reads `Open` on first display and updates to `Fixed`, `Deferred`, or `Skipped` after the guided-fix session in Step 6.
- 4-class classification: BUG, WATCH, OK, REVIEW (see SKILL.md Step 4). Each finding gets one classification plus all eight rating-table dimensions.
- Suggested fix for each BUG finding when one is mechanical; documentation-only suggestion for each WATCH finding

### Reading the reports

The 9-column rating table needs a wide terminal (~180 chars) to render as a horizontal table. In a narrower window the cells stack vertically and the report becomes harder to scan. For best readability:

- **GitHub or GitLab**: open the report file in the web UI; tables render natively.
- **Markdown viewer apps**: [Bear](https://bear.app/) (Mac/iOS, free tier; import .md as a note), [MacDown](https://macdown.uranusjr.com/) (Mac, free), [Marked 2](https://marked2app.com/) (Mac, paid) or [iA Writer](https://ia.net/writer) (Mac/iOS/Windows/Android, paid), [Obsidian](https://obsidian.md/) or [Typora](https://typora.io/) (cross-platform).
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

bug-echo isn't a CI-shaped tool. It needs a real fix to compare against, ideally with the pre-fix version available via git, and the per-match classification step uses Claude, which isn't something you want firing on every commit. Two options for automation:

- **Manual gate.** Add a step to your release checklist that runs `/bug-echo` after each merged bug-fix PR. Captures sibling bugs before they reach a release branch.
- **Selective trigger.** A pre-merge hook that runs only when the commit message contains a specific tag (for example, `[bug-fix]`). The hook calls Claude Code via the `claude` CLI. Cost-effective for teams that label bug-fix commits.

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

The shape is **surface, then verify, then generalize**: confirm the issue is real and current, confirm the fix is real, then look for siblings. It's slower than running bug-echo alone (typically 60-90 minutes for a real chain), but for bugs where shipping an incomplete fix would be expensive, it's the most thorough close-out I've found. Standalone bug-echo is fine for normal fixes.

A real chain example: an iPhone-only crash deferred for a month was marked Fixed by `unforget`, then `radar-suite focus on collapsibleSectionsStack` reported the fix had actually shipped weeks earlier in two specific commits and the ledger was stale. Closed as Fixed. `bug-echo "VStack with 12+ if-conditional children in one scope"` then found one BUG (a list-row view with 16 conditional children) and three WATCH sites at 10-12. Fixed the BUG with the same split pattern. Total time ~90 minutes.

## Status

Current version: 1.3.4. Built primarily for Swift/SwiftUI. The pattern construction is language-agnostic; the platform-conditional handling is currently Swift-specific.

Release history is in [CHANGELOG.md](CHANGELOG.md).

**Planned for future releases:** a built-in catalog mode for common Swift/SwiftUI anti-patterns (run when there's no recent fix to infer from), JSON sidecar output for chaining into downstream skills, recurrence detection across prior reports (catches bug classes that keep returning despite individual fixes), and a `known-intentional.yaml` user file for explicit suppression of patterns the user has confirmed are not bugs.

v1.3.0 shipped the conservative git-history slice of recurrence detection — the already-swept exclusion in Step 2.5, which reads commit history rather than prior reports. The deferred half is the report-cross-referencing analysis.

## Contributing: scale invariants

bug-echo must run identically on a 20-file package and a 5,000-file app *on the common path*. Large-codebase handling is always a branch entered by an explicit threshold, never a tax on the default flow. Any edit to `SKILL.md` must preserve these invariants:

1. **The sub-500-file scan path is untouched by scale logic.** File-count branching lives only in Step 3; a repo under 500 files scans directly and never enters sub-agent dispatch, dedup-across-batches, or any large-repo accommodation.
2. **Count-gated features are inert below their threshold.** The already-swept exclusion (Step 2.5, gated ≥6 candidates + prior bug-echo commits) and the high-count tighten offer (Step 2.5, gated ≥25 candidates) must be no-ops below their gates. A small or first-ever run may make at most one cheap, empty `git log` call and must otherwise behave exactly as v1.2 did.
3. **Thresholds are absolute, not relative to repo size.** The 25-match tighten offer keys off raw match count, not a fraction of files, so it never fires spuriously on a small codebase where a pattern legitimately repeats.
4. **No feature promotes a large-codebase branch to the default.** Sub-agent dispatch, git-history reads, and pattern-tightening prompts are opt-in-by-threshold. Making any of them unconditional is a regression, not an enhancement.

If you add scale handling, gate it and add it to this list. A change that makes the small-codebase path slower or more talkative has failed review regardless of what it does for large repos.

## Sibling skills

- [**bug-prospector**](https://github.com/Terryc21/bug-prospector) — runs *before* a fix; 7-lens forward-looking audit. Companion skill.
- [**workflow-audit**](https://github.com/Terryc21/workflow-audit) — 5-layer SwiftUI behavioral flow audit
- [**unforget**](https://github.com/Terryc21/unforget) — one-file deferred-work ledger
- [**radar-suite**](https://github.com/Terryc21/radar-suite) — 6-skill suite tracing user behavior paths through the app (iOS + macOS)
- [**prompter**](https://github.com/Terryc21/prompter) — prompt rewriting before execution
- [**skill-reviewer**](https://github.com/Terryc21/skill-reviewer) — candid reviews of other Claude Code skills
- [**tutorial-creator**](https://github.com/Terryc21/tutorial-creator) — annotated tutorials from your codebase

## Author

Terry Nyberg, [Coffee & Code LLC](https://stuffolio.app/). If bug-echo catches a real bug for you, [a coffee](https://buymeacoffee.com/stuffolio) is appreciated. Issue reports about what worked or didn't are more useful.

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=flat&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/stuffolio)

## License

Apache 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
