# bug-echo

A Claude Code skill: after you fix a bug, find other instances of the same pattern in the codebase.

## What it does

You fix one bug. bug-echo identifies the pattern from your fix, scans the rest of the codebase for the same anti-pattern, and produces a rated report. Each finding is classified as **BUG**, **OK**, or **REVIEW** with severity, fix effort, and blast-radius columns.

## How it works

1. **Pattern source.** Three modes:
   - **Inferred from your recent fix** — reads the diff, derives the anti-pattern, self-validates against the pre-fix file before scanning.
   - **You describe it** — you write out what to look for.
   - **Catalog** — pick from built-in patterns (Swift/SwiftUI focus).
2. **Scan.** Uses AST-grep where available; falls back to regex. Respects `#if os(...)` blocks so iOS-only patterns don't flag macOS-correct code.
3. **Classify.** Every match is read in context (≥20 lines around it) and classified individually — no batch judgments.
4. **Report.** Writes `.agents/research/YYYY-MM-DD-bug-echo-<slug>.md` plus a JSON sidecar. Each BUG finding includes Urgency, Risk-of-Fix, Risk-of-No-Fix, ROI, Blast Radius, Fix Effort.
5. **Follow-up.** Optional guided fix flow with explicit approval per finding.

## When to use it

- After fixing a bug, before committing — catch sibling instances of the same mistake.
- After a code review where one issue surfaced — check whether it's localized or systemic.
- During pre-release passes — feed the report into `safe-refactor` or similar follow-on skills.

## Distinguishing features

- **Self-validation before scanning.** If the inferred pattern doesn't match the pre-fix file, bug-echo refuses to scan rather than produce nonsense findings.
- **Recurrence warning.** If the same pattern appears in 3 of the last 4 scans, the report flags it and recommends an architectural fix or custom lint rule instead of another point fix.
- **Per-finding classification.** OK and REVIEW classifications are first-class outputs — not just BUG.

## Install

```bash
git clone https://github.com/Terryc21/bug-echo.git
cp -r bug-echo ~/.claude/skills/

# Or for a single project
cp -r bug-echo /path/to/your/project/.claude/skills/
```

Invoke with `/skill bug-echo` or natural-language triggers like *"scan for similar bugs"*, *"echo this fix"*, *"after-fix scan"*.

## Optional dependency

- `ast-grep` for higher-precision Swift matching: `brew install ast-grep`. Falls back to regex if absent.

## Output

Reports live in `.agents/research/`. The Markdown report is human-readable; the JSON sidecar is for chaining into other skills.

## Status

Current version: 1.0.0. Built primarily for Swift/SwiftUI codebases; the methodology is language-agnostic but the catalog and AST queries are Swift-focused.

## License

Apache-2.0. See [LICENSE](LICENSE).

## Author

Terry Nyberg, Coffee & Code LLC.
