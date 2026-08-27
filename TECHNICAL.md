# How bug-echo works

The mechanics: how it builds a search pattern, how it decides what's a real bug, and how to
compose it with other tools. You don't need any of this to use the skill — the
[README](README.md) is enough.

**Contents**

- [A run, in full detail](#a-run-in-full-detail)
- [Building the pattern](#building-the-pattern)
- [When the fixed line looks ordinary](#when-the-fixed-line-looks-ordinary)
- [Checking its own work](#checking-its-own-work)
- [Deciding what's a real bug](#deciding-whats-a-real-bug)
- [Higher precision with AST-grep](#higher-precision-with-ast-grep)
- [Ways to run it](#ways-to-run-it)
- [The report](#the-report)
- [Automating it](#automating-it)
- [Running it with two other skills](#running-it-with-two-other-skills)

---

## A run, in full detail

I fixed a SwiftUI bug where a save handler called `dismiss()` on macOS inside a
`NavigationSplitView` — which closes the whole window. The bug was one line, written two slightly
different ways:

```swift
// Before (buggy)
ScoutResultView(
    onSaveComplete: saveCompletionOverride ?? { dismiss() },
)

// After
let resolved: () -> Void = saveCompletionOverride ?? { dismiss() }
ScoutResultView(
    onSaveComplete: resolved,
)
```

The `??` looks harmless. Written inline in a SwiftUI body, it captures `self` lazily, so on a
redraw the captured `self` was out of date — the override read as empty even though the live one
was set. The dismiss ran, and the window went away. Pulling it into a `let` fixes it because the
closure then holds a value rather than `self`.

After committing, I ran `/bug-echo`:

1. **Read the diff and built a search:** `\w+\s*\?\?\s*\{[^}]*dismiss\(\)` — tight enough to
   avoid noise, loose enough to catch the same thing written differently.
2. **Checked itself** against the pre-fix file
   (`git show HEAD~1:Sources/Features/StuffScout/StuffScoutView.swift`) and confirmed the search
   matched the original bug. If it hadn't, the run would have stopped there.
3. **Searched 596 Swift files.** Three hits, two seconds.
4. **Read each hit in context.** One was the fix itself (OK). One was in a plain function rather
   than a SwiftUI body, so the lifecycle problem couldn't happen (OK). **One was a real sibling** —
   a Done button in the same file written as `(dismissOverride ?? { dismiss() })()` inside a
   `Button` action. Same bug, different clothes.
5. **Wrote a report** to `.agents/research/`, with file and line numbers, severity, and a
   suggested fix.

---

## Building the pattern

**From your fix.** The skill reads the diff, takes the removed (`-`) lines, finds a distinctive
piece of text they share, and builds a regular expression from it. It deliberately ignores
whitespace and trailing punctuation, which vary between sites for no meaningful reason.

If your diff also contains unrelated tidying — renames, reformatting, new comments — the pattern
comes out too narrow. Describe the bug in words instead: `/bug-echo "the pattern in your words"`.

---

## When the fixed line looks ordinary

Some bugs aren't in the line. They're in what the line assumed.

The removed code reads as perfectly normal, and what made it wrong was a check two lines above,
or a state the function had already put things into. Build a search from that line alone and you
get something that can't express the bug at all — so the run comes back clean on a project that
may be full of siblings.

So before building anything, the skill asks: **reading these removed lines on their own, can you
tell this is a bug?** Usually yes, and nothing more happens.

When the answer is no, it takes the values the removed line reads and walks back to where each
was last set or checked, discarding the rest of the function. One step, because that first place
is where the assumption lives. It takes a second step only when the first turns out to be a
pass-through (`x = y`, nothing changed or checked) — a wire, not an answer. It stops at three.

That gives a **second** pattern: the precondition. The first pattern finds candidates; the
precondition decides which are real. They're deliberately never merged into one search, since a
combined pattern would only match where both appear on the same line — which is exactly what this
kind of bug is not.

The walk reports how well it did. Either it found where the value came from, or it fell back to
the whole function and says the answer is approximate, or it can't name anything and tells you to
describe the pattern yourself rather than handing back a clean result it didn't earn.

**An approximate precondition produces a REVIEW, never a BUG.**

---

## Checking its own work

Before searching anything, the skill runs its pattern against the *broken* version of your file.
If the pattern doesn't match the bug it was built from, it stops and says so.

This is the safeguard that makes the rest trustworthy. You never get a report built on a
misunderstanding — the run either proves it understood your fix or it doesn't run.

---

## Deciding what's a real bug

Every match is read with at least 20 lines of surrounding code, because the same text is fine in
one place and broken in another:

- `try?` in a test is **OK**. The same `try?` in production is a **BUG**.
- A force-unwrap on an IBOutlet is **OK**. The same on a network response is a **BUG**.

Matches are judged one at a time, never in a batch.

**On Apple platforms**, a match inside a `#if os(...)` block that excludes the platform where the
bug happens is automatically OK. That prevents false alarms on projects where the same code is
correct on iOS and wrong on macOS.

---

## Higher precision with AST-grep

By default the skill searches text. [AST-grep](https://ast-grep.github.io/) searches code by its
structure instead, which is meaningfully better when:

- The pattern spans several lines and indentation differs between sites
- You want a specific construct (a `Button` action, a `@MainActor` call) rather than a shape of text
- A formatter has left inconsistent whitespace behind
- The bug depends on structure — "any closure assigned to a `let` of type `() -> Void`"

If `ast-grep` is on your PATH, the skill finds it and uses it. Install with `brew install ast-grep`.
Text search works fine without it; the report says which was used.

---

## Ways to run it

The skill always searches your whole project. The only question is where the pattern comes from.

| Goal | Command |
|---|---|
| Find siblings of the bug you just fixed | `/bug-echo` (after `git commit` or `git add`) |
| Search for a bug you haven't fixed yet | `/bug-echo "describe the pattern"` |
| Put the report somewhere else | `/bug-echo output=docs/audits/` |
| Force structural search | `/bug-echo --ast-grep` |

**Every run starts fresh.** There's no cache and no resume. The skill re-reads the diff,
re-checks its pattern, and re-searches. That's deliberate: if a sibling shows up again next run,
that's information — nobody fixed it. Old reports sit in `.agents/research/` if you want to
compare by hand.

*(On very large projects swept across several sessions, the skill does skip sites it already
fixed in a previous run — checked against git history, then re-checked against the live file so a
reintroduced bug still gets caught. This only kicks in past a size threshold; smaller projects
behave exactly as described above.)*

---

## The report

Reports are written to `.agents/research/YYYY-MM-DD-bug-echo-*.md`. That folder is shared with
radar-suite, bug-prospector, and the other Coffee & Code skills; it's created if missing. Override
with `output=<path>`.

Each report has:

- A file and line number for every claim
- A 9-column table: #, Finding, Urgency, Risk if you fix it, Risk if you don't, ROI, Blast radius,
  Effort, Status. Status starts at `Open` and becomes `Fixed`, `Deferred`, or `Skipped` after the
  guided fix session.
- One of four labels per finding: **BUG**, **WATCH**, **OK**, **REVIEW**
- A suggested fix for each BUG that's mechanical, and a documentation note for each WATCH

**Reading them.** Nine columns needs a wide window, roughly 180 characters. Narrower and the cells
stack vertically, which is hard to scan. GitHub, GitLab, VS Code's preview, Obsidian, Typora, Bear,
MacDown, iA Writer, and Marked 2 all render it properly. If a table looks broken in a terminal, the
file is fine — the window is too narrow.

---

## Automating it

**Short answer: mostly don't.** The skill needs a real fix to compare against, and judging each
match uses Claude, which you don't want firing on every commit. The premise also breaks down on
ordinary feature work, where there's no bug to learn from.

Two things that do work:

- **A checklist step.** Run `/bug-echo` after each merged bug-fix PR, so siblings get caught before
  they reach a release branch.
- **A tagged trigger.** A pre-merge hook that fires only when a commit message carries something
  like `[bug-fix]`, calling Claude Code through the `claude` CLI.

---

## Running it with two other skills

For high-stakes fixes — a production incident, anything security-adjacent, a change to code lots of
things depend on — three skills cover the ground in sequence:

| Stage | Skill | What it does |
|---|---|---|
| 1. Find copies | **bug-echo** | Same pattern elsewhere in the project |
| 2. Look ahead | [**bug-prospector**](https://github.com/Terryc21/bug-prospector) | What else could break that nobody's found |
| 3. Trace the path | [**radar-suite**](https://github.com/Terryc21/radar-suite) | Whether a user can still get through the flow (SwiftUI) |

Run them in that order. Each answers a question the previous one can't.
