# bug-echo

**A Claude Code skill that runs after you fix a bug and finds other places in your code with the same bug, so you can fix those too before they ship.**

Built while shipping [Stuffolio](https://stuffolio.app), an iOS/macOS app I work on every day. Free, open source, no paid tier, no referral links.

<a href="https://buymeacoffee.com/stuffolio"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" width="120"></a>

If bug-echo catches a real bug for you, a [coffee](https://buymeacoffee.com/stuffolio) is appreciated. Issue reports about what worked or didn't are even more useful.

---

## What is this, and why might I want it?

If you're newer to Claude Code and unsure what an "audit skill" does, here's the short version.

A **skill** is a markdown file Claude Code knows how to run. When you type `/bug-echo`, Claude follows the instructions in that skill, looks at your code, and writes you a report. You don't have to memorize anything. The skill tells Claude what to do; you read the report.

What this particular skill does: when you fix a bug, the bug almost always has a *shape*. Same kind of mistake. Same code pattern. The first place you noticed it is rarely the only place it lives. bug-echo runs after you finish a fix, looks at what you just changed, and searches the rest of your codebase for the same shape. Anything it finds is rated and listed in a report you can act on or ignore.

The most useful thing about it: the pattern bug-echo searches for is one that **just demonstrated it was a real bug** in your project. That's a much sharper search than a generic "look for these 50 anti-patterns" linter, because the proof that it matters is the fix you just shipped.

---

## Install

Two commands in Claude Code:

```
/plugin marketplace add Terryc21/bug-echo
```

```
/plugin install bug-echo@bug-echo
```

Run them one at a time and wait for the first to confirm before running the second.

That's it. The skill is now available everywhere you use Claude Code.

> **Why one at a time?** If you paste both lines at once, Claude Code treats the second `/plugin` as text inside the first command and tries to clone a repo with a malformed name. Running them one at a time avoids that trap.

---

## Your first run (start here)

You don't need to set anything up. Just fix a bug like normal, then run:

```
/bug-echo
```

Claude reads your most recent fix, figures out the pattern, validates the pattern by checking it against the pre-fix version of the file (if it can't find a match there, it stops rather than scanning with a bad pattern), and then sweeps the rest of your codebase. The output is a markdown report saved to `.agents/research/` in your project, with each match rated and labeled:

- **BUG** — same pattern as your fix, almost certainly a problem
- **OK** — the pattern matches but in a context where it's intentional or harmless
- **REVIEW** — context unclear, you should look

You decide what to do with the findings. The skill doesn't change your code.

---

## A real example

I had a SwiftUI bug where saving from one screen made the macOS window vanish. The fix was three lines: snapshot a closure into a body-local `let` before passing it to a child view, so the closure captured a value instead of `self`.

After I shipped the fix I ran:

```
/bug-echo
```

It inferred the pattern from my diff (a regex matching the specific `??`-with-fallback shape that caused the bug), validated it against the pre-fix file, and scanned 596 Swift files. Three matches. One was the fix itself. One was a function on a different code path that wasn't actually buggy (correctly classified as OK). One was a sibling bug in the same file: a Done button doing the exact same staleness pattern in a different syntax. Same fix shape resolved it.

That sibling bug had been sitting in production code for weeks. It would have hit a user eventually. bug-echo found it in two minutes.

You can read the full sample report from a different real run here: [example output](skills/bug-echo/examples/2026-05-03-bug-echo-deep-viewbuilder-crash.md).

---

## When to skip it

bug-echo isn't worth running for every fix. Skip it when:

- The fix is a typo or single-character change
- The bug was in one-off code that nothing else calls
- You're cleaning up a migration whose patterns are on their way out
- The fix doesn't have a recognizable shape (it's a one-line wording change in a string, for example)

A good rule of thumb: if the bug surprised you, it's probably worth running bug-echo. Surprises are bug shapes you didn't know to look for, and those are the patterns most likely to repeat.

---

## What the output looks like

The report is a single markdown file in `.agents/research/`. Each finding has:

- A short description of the match
- The exact file and line where it lives
- A rating table (urgency, risk-of-fix, risk-of-no-fix, ROI, blast radius, fix effort)
- A suggested fix when one is obvious

The report is human-readable. You can scan it in two minutes, decide what's worth investigating, and ignore the rest. After fixing any of the BUG findings, the skill optionally asks if you want to run another round to look for *their* siblings.

---

## How the skill keeps itself honest

A few things bug-echo does to avoid producing nonsense findings:

- **Self-validates the pattern before scanning.** If the pattern Claude inferred from your diff doesn't actually match the pre-fix version of the file, the skill refuses to scan and asks you to describe the pattern by hand instead. A pattern that doesn't find the bug it was extracted from is not a pattern worth searching for.
- **Reads each match in context (at least 20 lines around it) before classifying.** No batch judgments. Two files that both match the same regex can mean different things; the skill doesn't pretend otherwise.
- **Respects platform conditionals (`#if os(iOS)` etc.) on Swift codebases.** A pattern that's correct on one platform but a bug on another won't get flagged on the wrong side.

---

## Honest about limits

This skill is a tool, not an oracle. Things to keep in mind:

- It can only find patterns that have a code shape. Bugs that exist in the *relationship between two correct files* (cross-context mutations, race conditions, distributed state) won't show up.
- The pattern is inferred from your diff. If your fix was unusual or your diff includes unrelated cleanup, the inferred pattern might be too narrow or too broad. You can always describe the pattern manually in that case.
- A clean run means zero matches for the inferred pattern. It doesn't mean zero bugs in your codebase.

The right way to use any audit skill: treat findings as leads to investigate, not items to fix blindly. Verify critical findings before committing.

---

## Optional: faster Swift matching

bug-echo uses regex by default and works fine for most projects. If you want more precise matching on Swift code, install `ast-grep`:

```
brew install ast-grep
```

bug-echo will detect it and use it automatically. If `ast-grep` isn't installed, regex still works.

---

## Advanced: the post-fix sweep (three skills together)

When you have a real fix that closes a known issue and you want maximum confidence, you can chain bug-echo with two other skills I've built:

| Stage | Skill | What it does |
|---|---|---|
| 1. Surface | [unforget](https://github.com/Terryc21/unforget) | Shows you a deferred row you're about to mark Fixed |
| 2. Verify | [radar-suite](https://github.com/Terryc21/radar-suite) | Confirms the fix is real (catches stale Open rows where the fix shipped weeks ago and nobody updated the ledger) |
| 3. Generalize | bug-echo (this skill) | Sweeps the codebase for sibling instances of the bug you just verified |

You don't need this workflow for bug-echo to be useful. bug-echo runs standalone perfectly well. But if you also use `unforget` and `radar-suite`, the chain is the most thorough way to close a bug class. Install the others through the same `/plugin marketplace add` and `/plugin install` commands as bug-echo, with their own repo names substituted in.

---

## Other Claude Code skills I've built

- [code-smarter](https://github.com/Terryc21/code-smarter) — turns a file from your project into an annotated tutorial with vocabulary, quizzes, and gap analysis. Works for any language.
- [prompter](https://github.com/Terryc21/prompter) — rewrites your Claude Code prompt for clarity and fixes typos before acting.
- [workflow-audit](https://github.com/Terryc21/workflow-audit) — 5-layer audit of SwiftUI user flows. Finds dead ends, dismiss traps, and unwired features.
- [radar-suite](https://github.com/Terryc21/radar-suite) — 6 audit skills for iOS/macOS Swift codebases. Covers data models, time-bomb code, navigation, backup/restore, visual quality.

All free, all Apache 2.0, all built while shipping Stuffolio.

---

## Status

Current version: 1.0.0 (initial public release). Built primarily for Swift/SwiftUI, but the methodology is language-agnostic. The pattern construction (regex from diff) works for any language; the platform-conditional handling is currently Swift-specific.

Planned for v1.1: a built-in catalog mode for common Swift/SwiftUI anti-patterns, JSON sidecar output, recurrence detection across prior reports, and a `known-intentional.yaml` file for explicit suppression of patterns you've confirmed are not bugs.

---

## Deeper documentation

The previous, more detailed README is preserved as [README-detailed.md](README-detailed.md). It covers the post-fix sweep in more depth, includes a worked example using all three companion skills, and has the original "distinguishing features" framing.

---

## License

Apache 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

## Author

Terry Nyberg, [Coffee & Code LLC](https://stuffolio.app/).
