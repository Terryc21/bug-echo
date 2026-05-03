# bug-echo

A Claude Code skill: after you fix a bug, find other instances of the same pattern in the codebase.

If bug-echo catches a real bug for you, a [coffee](https://buymeacoffee.com/stuffolio) is appreciated. Issue reports about what worked or didn't are even more useful.

<a href="https://buymeacoffee.com/stuffolio">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" width="150">
</a>

## What it does

You fix one bug. bug-echo identifies the pattern from your fix, scans the rest of the codebase for the same anti-pattern, and produces a rated report. Each finding is classified as **BUG**, **OK**, or **REVIEW** with severity, fix effort, and blast-radius columns.

## How it works

1. **Pattern source.** Two modes:
   - **Inferred from your recent fix.** Reads the diff, derives the anti-pattern, self-validates against the pre-fix file before scanning.
   - **You describe it.** You write out what to look for.
2. **Scan.** Uses AST-grep where available, falls back to regex. Respects `#if os(...)` blocks so iOS-only patterns don't flag macOS-correct code.
3. **Classify.** Every match is read in context (≥20 lines around it) and classified individually. No batch judgments.
4. **Report.** Writes a Markdown report to `.agents/research/YYYY-MM-DD-bug-echo-<slug>.md`. Each BUG finding includes Urgency, Risk-of-Fix, Risk-of-No-Fix, ROI, Blast Radius, Fix Effort.
5. **Follow-up.** Optional guided fix flow with explicit approval per finding.

## When to use it

- After fixing a bug, before committing. Catch sibling instances of the same mistake.
- After a code review where one issue surfaced. Check whether it's localized or systemic.
- During pre-release passes.
- **As the final stage of the post-fix sweep** (see below) when paired with `unforget` and `radar-suite`.

## The post-fix sweep (a three-skill workflow)

bug-echo is the third stage of a **surface → verify → generalize** loop that catches a class of bugs no single audit tool finds: bugs that haven't crashed yet but sit under the same runtime conditions as one that just did.

| Stage | Skill | What it does |
|---|---|---|
| 1. Surface | [unforget](https://github.com/Terryc21/unforget) | Shows you a deferred row you're about to mark Fixed |
| 2. Verify | [radar-suite](https://github.com/Terryc21/radar-suite) | Confirms the fix is real (catches stale Open rows where the fix shipped weeks ago and nobody updated the ledger) |
| 3. Generalize | **bug-echo** (this skill) | Scans the whole codebase for the same anti-pattern; rates each match BUG / OK / REVIEW |

### Why pattern-after-a-real-fix beats pattern-from-a-catalog

A standard auditor matches code against a pre-built rule catalog assembled in advance. The catalog reflects what the audit author thought was a bug at the time the rule was written.

bug-echo, run after a real fix, matches code against an anti-pattern that **just demonstrated it was a real bug in your specific codebase**. The fix is the proof. After-the-fact pattern matching is dramatically more accurate than pre-built pattern matching, and it's the systematic way to find unfired bugs sitting under the same runtime conditions that just produced a real one.

### Worked example

A real run from the development codebase of these skills:

| Stage | Command | Result |
|---|---|---|
| Surface | `/unforget` | Open row "iPhone crash tap item: collapsibleSectionsStack" had been Open for a month |
| Verify | `/radar-suite focus on collapsibleSectionsStack` | Reported the bug had shipped fixed weeks earlier in two specific commits. Current code had the corrected pattern. The ledger row was stale. Closed as Fixed. |
| Generalize | `/bug-echo "VStack with 12+ if-conditional children in one scope can crash on physical iPhone"` | Found one BUG (a list-row view with 16 children in its type tree, identical conditions) and three WATCH sites at 10-12 conditionals each. Fixed the BUG with the same split pattern. |

Total time: ~90 minutes. The list-row bug had never crashed because users hadn't accumulated enough records yet — but the runtime conditions were identical to the original. It would have hit a real user eventually. The post-fix sweep caught it before that.

### When to skip the loop

- Trivial fixes (typos, single-character changes, isolated state)
- Fixes to one-off code with no callers
- Cleanup of an already-failed migration where the pattern is on its way out

### Companion installs

```bash
# unforget
git clone https://github.com/Terryc21/unforget.git ~/.claude/skills/unforget

# radar-suite
git clone https://github.com/Terryc21/radar-suite.git ~/.claude/skills/radar-suite
```

bug-echo runs standalone too — see "How it works" above for the user-described mode that doesn't require a recent fix.

## Distinguishing features

- **Self-validation before scanning.** If the inferred pattern doesn't match the pre-fix file, bug-echo refuses to scan rather than produce nonsense findings.
- **Per-finding classification.** OK and REVIEW classifications are first-class outputs, not just BUG.
- **Self-contained.** No external scripts, no pattern catalog, no install dependencies beyond Claude Code itself. AST-grep is optional.

## Install

```bash
git clone https://github.com/Terryc21/bug-echo.git
cp -r bug-echo/skills/bug-echo ~/.claude/skills/

# Or for a single project
cp -r bug-echo/skills/bug-echo /path/to/your/project/.claude/skills/
```

Invoke with `/skill bug-echo` or natural-language triggers like *"scan for similar bugs"*, *"echo this fix"*, *"after-fix scan"*.

## Optional dependency

`ast-grep` for higher-precision Swift matching: `brew install ast-grep`. Falls back to regex via the Grep tool if absent.

## Output

Reports live in `.agents/research/`. The Markdown report is human-readable and self-contained.

## Status

Current version: 1.0.0 (initial release). Built primarily for Swift/SwiftUI codebases; the methodology is language-agnostic. The pattern construction (regex from diff) works for any language.

**Planned for v1.1:**
- Pattern catalog mode (built-in Swift/SwiftUI anti-pattern library)
- JSON sidecar output for chaining into downstream skills
- Recurrence detection across prior reports
- `known-intentional.yaml` user file for explicit suppression

## Other Claude Code skills I have built

- [code-smarter](https://github.com/Terryc21/code-smarter) -- prompter rewrites your prompt for clarity before Claude acts; tutorial-creator generates annotated code-reading lessons from your own codebase
- [workflow-audit](https://github.com/Terryc21/workflow-audit) -- 5-layer audit of SwiftUI user workflows; finds dead ends, broken promises, and missing data wiring
- [radar-suite](https://github.com/Terryc21/radar-suite) -- 6-skill audit suite for iOS/macOS Swift codebases. Behavioral, not grep-based: grep-based skills are the build inspector who confirms every bolt is torqued to spec; behavioral skills are the test driver who takes it on the road and finds that the GPS routes the user into a lake. Different layer, different bugs -- the two approaches complement each other, and a thorough audit uses both.

## License

Apache-2.0. See [LICENSE](LICENSE).

## Author

Terry Nyberg, Coffee & Code LLC.
