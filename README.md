# bug-echo

![Version](https://img.shields.io/github/v/tag/Terryc21/bug-echo?label=version) ![Last commit](https://img.shields.io/github/last-commit/Terryc21/bug-echo) ![Stars](https://img.shields.io/github/stars/Terryc21/bug-echo?style=flat) ![Issues](https://img.shields.io/github/issues/Terryc21/bug-echo) ![License](https://img.shields.io/github/license/Terryc21/bug-echo) ![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-Plugin-blueviolet)

**You just fixed a bug. Is the same mistake somewhere else in your project?**

bug-echo looks at the fix you just made, works out what the underlying mistake was, and searches
the rest of your code for the same thing hiding elsewhere. You get a short report: here's a real
one, here's a false alarm, here's one you should look at yourself.

*4 min read · [how it works](TECHNICAL.md) · [what changed](CHANGELOG.md)*

---

## The problem

When you fix a bug, you fix it in one place. But the same mistake is often sitting in three other
places you've forgotten about — copy-pasted, typed again from habit, or left behind when a
refactor didn't reach every corner.

Those copies wait. One of them breaks for a real user, weeks later.

Finding them by hand means remembering every place the same shape could have appeared, which is
exactly what people are worst at.

---

## Why this catches things your other tools don't

A linter checks your code against a list of problems somebody wrote down in advance. That's
useful, and you should keep using one.

bug-echo works the other way round. It looks for one specific thing: **the bug that just proved
it was real, in your own code, fifteen minutes ago.** Nobody had to predict it. Reality picked it
out for you.

That's why it finds bugs your linter has no rule for — the bug was novel enough to need fixing in
the first place.

| A linter is better at | bug-echo is better at |
|---|---|
| Running on every save | Running once, after a fix |
| Problems everyone already knows about | The specific bug you just hit |
| Style and formatting | Copies of your latest real bug |
| Mature, well-tested rules | New bugs nobody wrote a rule for |

**The safeguard.** Before searching, bug-echo tests its understanding against the broken version
of your file. If it got the bug wrong, it stops rather than searching for the wrong thing. You
never get a report built on a misunderstanding.

---

## Try it

Type these into Claude Code, not Terminal. One at a time.

```
/plugin marketplace add Terryc21/bug-echo
```

```
/plugin install bug-echo@bug-echo
```

Then fix a bug, commit it, and run:

```
/bug-echo
```

About two minutes on a normal project.

<details>
<summary><strong>Installing by hand</strong></summary>

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/Terryc21/bug-echo.git ~/.claude/skills/bug-echo
```

Then use `/skill bug-echo` (with the prefix).
</details>

**No recent fix?** Describe the bug instead and it searches for that:

```
/bug-echo "await inside a forEach, so nothing actually waits"
```

---

## What a run looks like

A real one. I'd fixed a bug where saving on macOS closed the whole window.

1. **Read my fix** and worked out the pattern.
2. **Checked itself** against the broken version of the file. If it had misunderstood, it would
   have stopped here.
3. **Searched all 596 files.** Two seconds, three hits.
4. **Read each one in context.** One was my own fix. One only looked similar and was harmless.
   **One was real** — a "Done" button on the *same screen* with the same mistake, written
   slightly differently.
5. **Wrote a report** with the file, the line, how bad it was, and a suggested fix.

That third one had been in shipping code for weeks. It would have found a user eventually.

**[Read the full report →](skills/bug-echo/examples/2026-05-03-bug-echo-deep-viewbuilder-crash.md)**
· [the same thing in TypeScript](skills/bug-echo/examples/describe-mode-await-in-forEach.md)
· [a run where the fix already existed elsewhere](skills/bug-echo/examples/canon-reference-implementation.md)

Each finding is labelled **BUG** (real), **WATCH** (fine today, one small step from breaking),
**OK** (false alarm), or **REVIEW** (your call), with a file and line number.

---

## When the bug lives between two files

This is the most useful thing in this README, so it isn't buried at the bottom.

Some bugs aren't in any one file. Every file is fine on its own, and the problem only appears in
how they fit together.

A real one from my app: a screen added a button to its toolbar — correct. Its parent screen added
the same button — also correct. Neither file was wrong. But the parent drew the child inside its
own navigation stack, the two toolbars merged, and you saw the button twice.

**There is nothing to search for there.** You can't grep for "a screen that adds a toolbar button
while its parent also adds one." That isn't text, it's a relationship.

**So stop searching for the bug and search for the ingredient.** The bug has no shape; the
setup does:

1. **Search for one half.** In my case, every screen putting that button in a toolbar. 28 files.
2. **Open each one's callers.** Is it drawn inline, shown as a sheet, or pushed as a new screen?
   You cannot tell from the file itself.
3. **Only some of those are bugs.** Inline under a parent that owns a toolbar is broken. A sheet
   is fine — it gets its own. A pushed screen is fine.

Step 2 is the part no tool can do for you. Steps 1 and 3 are mechanical.

Mine took 20 minutes across 28 files and found nothing new. **That's still worth having** —
"I checked, there aren't any more" beats "I wonder if there are more" the day before you ship.

And here's the thing worth noticing: bug-echo would have handed me a 28-row list too, and every
row would have been a false alarm, because putting that button in a toolbar isn't a bug by
itself. I'd have done the walk anyway, after paying for a report first.

> **When *every* match is a false alarm, that usually isn't a pattern that needs tightening. It's
> a sign the bug isn't pattern-shaped and you've reached for the wrong tool.**

**How to tell in advance:** could you spot the bug reading one file top to bottom? Then bug-echo
is right. Would you need a second file open to know whether the first one is wrong? Do the walk.

For SwiftUI I eventually turned this walk into its own skill,
[ui-path-radar](https://github.com/Terryc21/radar-suite), because I kept doing it by hand.

---

## When not to bother

- Typos, one-character changes, anything isolated
- One-off code nothing else calls
- Cleanup where the pattern is on its way out anyway
- A fix whose diff is mostly unrelated tidying — describe the bug in words instead

**Rule of thumb: if the bug surprised you, run it.** Surprise means the shape wasn't on your
mental list of things to watch for, which makes it exactly the kind of thing likely to be sitting
somewhere else unnoticed.

---

## What it can't do

The skill finds what a search can express, judged with about 20 lines of surrounding code. It
will not find:

- **Bugs in the relationship between two correct files** — race conditions, coordination problems.
  Every file passes on its own. ([What to do instead](#when-the-bug-lives-between-two-files).)
- **Patterns buried in noise.** If the search matches 200 places and 195 are fine, the report is
  unusable. Describe the pattern by hand instead.
- **Fixes with no shape** — a reworded message, a changed constant, a comment. Nothing to learn
  from.

**A clean run means no matches for that pattern. It does not mean no bugs.**

For the rest: linters catch single-file style problems,
[bug-prospector](https://github.com/Terryc21/bug-prospector) looks for what hasn't broken yet,
profilers catch memory and concurrency, and tests catch wrong logic. bug-echo covers one slot —
copies of the bug you just fixed.

---

## bug-echo or bug-prospector?

| | bug-echo | [bug-prospector](https://github.com/Terryc21/bug-prospector) |
|---|---|---|
| **Run it** | Right after fixing a bug | Before a release, after a crash |
| **It asks** | "Where else is this same mistake?" | "What could go wrong that I haven't found?" |
| **It needs** | The fix you just made | Just your code |

Many people run both — prospector before releases, echo after every fix.

---

## Where it stands

**v1.6.0.** Used through real App Store release cycles on [Stuffolio](https://stuffolio.app), the
app it was built for. Works in any language for finding the pattern; a few conveniences are
Apple-specific.

**[Full version history →](CHANGELOG.md)**

**Contributing.** Pull requests welcome. One rule that matters: **projects under 500 files must
keep scanning directly**, with none of the large-project machinery in the path. If a change puts
extra steps in front of a small project's scan, it won't be accepted.

---

## Related skills

[**bug-prospector**](https://github.com/Terryc21/bug-prospector) — hunt for bugs before a release ·
[**workflow-audit**](https://github.com/Terryc21/workflow-audit) — trace SwiftUI behaviour ·
[**radar-suite**](https://github.com/Terryc21/radar-suite) — six skills tracing user paths ·
[**unforget**](https://github.com/Terryc21/unforget) — one file for everything you deferred ·
[**prompter**](https://github.com/Terryc21/prompter) — rewrite prompts before running them ·
[**skill-reviewer**](https://github.com/Terryc21/skill-reviewer) — candid reviews of other skills ·
[**tutorial-creator**](https://github.com/Terryc21/tutorial-creator) — lessons from your own code

---

**New to Claude Code?** A *skill* is a set of written instructions Claude Code knows how to
follow. Install it once, type `/bug-echo`, and it does the work. Two words worth knowing: a
**diff** is the before-and-after of a change you made, which is what bug-echo reads; a **sibling**
is another place in your project with the same mistake.

**Terry Nyberg**, [Coffee & Code LLC](https://stuffolio.app/). Built while shipping
[Stuffolio](https://stuffolio.app) through real App Store submissions. If bug-echo has caught
something for you, [a coffee](https://buymeacoffee.com/stuffolio) is appreciated — though a note
about how it went on a non-Swift project is worth more.

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=flat&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/stuffolio)

Apache 2.0 — see [LICENSE](LICENSE).
