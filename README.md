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
