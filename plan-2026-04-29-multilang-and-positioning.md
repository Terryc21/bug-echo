# bug-echo: multi-language support, generalization step, and closure-framing positioning

**Status:** Deferred. Plan authored 2026-04-29 from observations in the Stuffolio Phase 5c production-deploy session. No work has started.

## Context

bug-echo's value proposition (post-fix scan to confirm no other instances of a fixed bug pattern exist) is sound and well-scoped. Three observations from running a Stuffolio Phase 5c hotfix session on 2026-04-29 surfaced gaps that are limiting bug-echo's actual usage.

The session shipped commit `45f90604` (a JavaScript ReferenceError fix in `cloudflare-worker/src/endpoints/stuff-scout.js:504` — a bare `{ assertedValue }` shorthand that referenced an undefined identifier in caller scope while the callee had a destructure parameter of that exact name). bug-echo would have been a perfect fit for closure: scan post-fix, confirm no other instances, declare done. **It was never invoked.**

The retrospective on why surfaced three discrete improvements. Each is independently valuable and they are listed in priority order. The work can be done as one bundle (~4-5 hours) or three separate sessions (~1-2 hours each).

## Rating

| # | Improvement | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort |
|---|---|---|---|---|---|---|---|
| 1 | Language auto-detection at preflight; remove Swift-default scope | 🟡 HIGH | ⚪ Low | 🟡 High (skill seen as Swift-only) | 🟠 Excellent | 🟢 4 files | Medium |
| 2 | Generalization step in Step 2B (specific pattern vs bug class) | 🟢 MEDIUM | 🟢 Medium | 🟢 Medium | 🟢 Good | 🟢 3 files | Medium |
| 3 | Reframe triggers and description as closure protocol; author the empty README | 🟡 HIGH | ⚪ Low | 🟡 High (skill not invoked when needed) | 🟠 Excellent | 🟢 2 files | Small |

Why #1 is HIGH urgency despite being the largest change: every additional session run on a non-Swift codebase that does not invoke bug-echo is a missed closure opportunity that erodes confidence in any "this is fixed" claim. The 2026-04-29 session is one data point; the worker-only sessions across the Stuffolio backlog likely produce many more.

## Improvement 1: Language auto-detection at preflight

### Problem

`SKILL.md:117` declares the default file glob as `**/*.swift`. The catalog patterns (per `references/pattern-schema.md` referenced at `SKILL.md:198`) are presumed Swift-shaped. The "infer from recent fix" mode at Step 2B (line 86) does not consider the language of the diff. Net effect: bug-echo is positioned as a general post-fix scanner but in practice gates itself to Swift, which means users on multi-language repos (iOS app + backend worker, iOS app + Node tools, etc.) do not reach for it during non-Swift fixes.

### Change

In `scripts/preflight.sh`, before any prompt, detect the working directory's primary language(s):

| Signal | Language | Default scope |
|---|---|---|
| `*.xcodeproj`, `*.xcworkspace`, `Package.swift` | Swift | `**/*.swift` |
| `package.json` (no Swift sibling) | JavaScript / TypeScript | `**/*.{js,jsx,ts,tsx,mjs,cjs}` |
| `wrangler.toml` (no `package.json`) | JavaScript (Cloudflare Worker) | `**/*.{js,mjs}` |
| `pyproject.toml`, `requirements.txt`, `setup.py` | Python | `**/*.py` |
| `Cargo.toml` | Rust | `**/*.rs` |
| `go.mod` | Go | `**/*.go` |
| Mixed (Swift + JS) | Multi | Defer to Step 2B's diff-path detection, or prompt user |

When in `infer from recent fix` mode (Step 2B), override the preflight detection with the diff path's language: if the diff touches `*.js`, scan JS regardless of repo-root language. This handles the cross-language case where an iOS repo also has a Cloudflare Worker subdirectory and the recent fix is in the JS half.

When the language is something other than Swift, filter the catalog at Step 2C to only show patterns relevant to that language. Catalog patterns gain a required `applicable_languages` field in their YAML front-matter.

### Files

| File | Action | Notes |
|---|---|---|
| `scripts/preflight.sh` | Edit (currently does not exist on disk; create it per SKILL.md:26) | Add the language-detection block. Output the detected language as a `LANGUAGE` variable that downstream scripts read |
| `scripts/run-scan.py` | Edit (currently does not exist on disk; create it per SKILL.md:114) | Read `LANGUAGE` from the preflight output. Default scope and AST-grep ruleset accordingly |
| `references/pattern-schema.md` | Edit | Add `applicable_languages` field with allowed values: `swift`, `javascript`, `typescript`, `python`, `rust`, `go` |
| `patterns/index.yaml` | Edit | Add `applicable_languages` entry to each catalog pattern |
| `SKILL.md` | Edit | Update line 117 to remove the Swift-specific glob default; replace with "scope defaults to the language detected at preflight, configurable via the pattern's `scope` field" |

### Reuse

`SKILL.md:124-126` already declares multiplatform handling for `#if os(...)` blocks. The same scope-respecting logic generalizes to language detection: scan only the files that match the detected language, ignore the rest. No new helpers needed; this is one decision moved earlier in the flow.

## Improvement 2: Generalization step in Step 2B

### Problem

`SKILL.md:86-101` (`Step 2B: Infer from recent fix`) parses a diff into removed lines (anti-pattern) and added lines (correct pattern), then constructs a candidate AST query from the removed code. A candidate built from removed text matches THAT text — not the broader bug class.

Concrete example from 2026-04-29: the fix changed `{ assertedValue }` to `{ assertedValue: assertedValuation.value }` at one callsite. The actual bug class is "callsite using shorthand that resolves to a free identifier in caller scope but matches a destructure parameter in the callee." A diff-derived pattern would scan for the literal `{ assertedValue }` token, missing `{ otherName }` instances of the same class.

The user has no way today to express "scan for the class, not just this textual instance" without falling back to Step 2A (user-described pattern) and writing the abstraction by hand.

### Change

After `infer-pattern-from-diff.sh` returns a `validated` candidate, present THREE options via AskUserQuestion before scanning:

```json
{
  "question": "Match the specific text or the broader bug class?",
  "header": "Pattern scope",
  "options": [
    {
      "label": "Specific text",
      "description": "Scan for {{ literal_pattern }} (current behavior; safest)"
    },
    {
      "label": "Bug class (generalized)",
      "description": "Scan for the underlying class: {{ inferred_class_summary }} (broader, may have more false positives)"
    },
    {
      "label": "I'll describe both",
      "description": "Run two scans and merge results"
    }
  ],
  "multiSelect": false
}
```

The skill must propose a generalization. Naive implementation: extract the diff's structural pattern (e.g., "shorthand property in object literal at function callsite") and present it as the class. For JavaScript specifically, lean on existing tooling:

- **JS/TS:** when the bug class involves undefined identifiers, shell out to ESLint with `no-undef` enabled (`npx eslint --no-eslintrc --rule '{"no-undef": "error"}' <scope>`). ESLint's scope analysis is more precise than any AST query bug-echo could write from scratch.
- **Swift:** SwiftLint custom rules already exist for many bug classes; the catalog can reference them by ID.
- **Python:** Pyflakes / Ruff equivalents.

When no ecosystem tool fits, fall back to the AST query approach with a wider regex.

### Files

| File | Action | Notes |
|---|---|---|
| `scripts/infer-pattern-from-diff.sh` | Edit | Add a generalization-suggestion step after the candidate validates. Output two patterns: the specific one and a class summary |
| `references/pattern-schema.md` | Edit | Document the new "class" mode and how to write a class-shaped catalog entry |
| `references/ast-grep-quickstart.md` | Edit | Add a section comparing specific-pattern vs class-pattern AST queries with examples |

### Reuse

The existing self-validation step (`SKILL.md:93-100`) is the load-bearing piece for this improvement. A generalized pattern can be presented to the user only AFTER the specific candidate validates against the pre-fix file — that proves we understood the diff before extrapolating from it. Do not skip the validation gate when generalizing; if anything, generalization should require a SECOND validation step that confirms the broader class also matches the pre-fix code.

## Improvement 3: Reframe triggers + author the empty README

### Problem

`SKILL.md:3` lists triggers: `"run bug-echo", "echo this fix", "scan for similar bugs", "find other instances", "after-fix scan"`. All of these frame bug-echo as a **scanning verb**. Sessions reach for bug-echo when the user types "scan" or "find" — but a hotfix session's mental state is **closure**, not search. The hotfix verbs ("just shipped a fix," "rolled back, then re-deployed," "before declaring this done") never fire bug-echo's triggers, so the skill is silently absent from the workflows where it is most valuable.

`bug-echo-README.md` is empty (0 bytes on disk as of 2026-04-29). New users have no entry point that explains the skill's value proposition, when to use it, and how it differs from radar-suite or Axiom auditors.

### Change

**Triggers expansion in SKILL.md:3:**

Add closure-framed verbs to the triggers list:
- "after committing a hotfix"
- "after a production rollback"
- "before declaring a fix complete"
- "before merging a bug fix"
- "scan after this fix"

Update the description's first sentence from "After fixing a bug, find and rate other instances..." to "Closure protocol after a bug fix: confirm no other instances of the same pattern exist before declaring the fix complete." This is a positioning shift, not a capability change. The skill does what it always did; it presents itself as the natural next step after a hotfix lands rather than as a standalone scanning tool.

**README authoring:**

Write `bug-echo-README.md` from scratch. Sections (in this order, weighted by what a new user actually needs):

1. **What bug-echo does (one paragraph)** — closure protocol after a bug fix. Frames the value prop in two sentences.
2. **When to invoke it** — three concrete scenarios with examples (hotfix landed, PR review, monthly hygiene scan). Show the trigger phrase that fires each.
3. **Three modes** — table comparing user-described, infer-from-fix, catalog. When to pick each.
4. **What you get back** — sample output excerpt showing the rating table and the fix-by-fix walkthrough.
5. **What bug-echo is NOT** — explicit disclaimers. Not a linter (run before edit). Not a security scanner. Not a code-review replacement. The post-fix narrowing is the differentiator.
6. **Comparison to adjacent skills** — radar-suite (broad audit, scans for everything), Axiom auditors (iOS-specific patterns), bug-echo (post-fix narrow scan). Three-line table.
7. **Installation and dependencies** — AST-grep optional but recommended (`brew install ast-grep`). ESLint / Ruff / SwiftLint optional per-language.
8. **Examples** — three short worked examples, one per mode. Each shows the invocation, the prompts, the output.

### Files

| File | Action | Notes |
|---|---|---|
| `SKILL.md` | Edit line 3 (triggers) and the description's framing | Keep the body of SKILL.md unchanged; this is a positioning edit |
| `bug-echo-README.md` | Write (currently empty) | New authoring per the section list above |

### Reuse

The README's "Three modes" section can lift verbatim from SKILL.md's Steps 2A / 2B / 2C. The "What you get back" section can lift from SKILL.md's Step 5 + the Issue Rating Table format. Do not duplicate content; link to SKILL.md for the deep details and use the README for orientation.

## Out of scope (explicitly deferred from this plan)

- **Catalog expansion.** Adding new catalog patterns is independent work and depends on Improvement 1 landing first (since catalog entries gain `applicable_languages`).
- **CI integration.** Running bug-echo in a CI pipeline is a worthwhile follow-up but requires headless invocation paths the skill does not currently expose.
- **Multi-repo scanning.** bug-echo today scans one working tree. Cross-repo patterns (e.g., the same bug class in stuffolio-app and stuffolio-strategy) are not addressed here.
- **Integration with safe-refactor.** SKILL.md:149 mentions a JSON sidecar for downstream tools. Wiring that into safe-refactor or another skill is a separate plan.

## Verification

After all three improvements land, the same 2026-04-29 Stuffolio Phase 5c session would:

1. **Improvement 1:** Detect `wrangler.toml` at the worker subdirectory; default scope to JS. Catalog filtered to JS-applicable patterns.
2. **Improvement 2:** After `infer-pattern-from-diff.sh` validates the `{ assertedValue }` removal pattern, prompt: "Match this literal token or the broader 'undefined shorthand identifier' class?" If the user picks the class, shell out to ESLint with `no-undef` for the scan.
3. **Improvement 3:** The session's "I just shipped a hotfix; production was rolled back and re-deployed" mental state matches one of the new triggers, fires bug-echo automatically, and the skill produces a clean "zero other instances" report that closes the loop on the hotfix.

End-to-end test: replay commit `45f90604` against the post-improvement bug-echo. Expected outputs:
- Preflight detects JS via `wrangler.toml` ✓
- Step 2B parses the diff, validates the pattern against the pre-fix file ✓
- Generalization step offers the bug class; user picks it ✓
- ESLint scan runs over `cloudflare-worker/src/**/*.js` ✓
- Report produced at `.agents/research/2026-04-29-bug-echo-asserted-value.md` with zero BUG findings, classified as a successful run per `SKILL.md:189` ✓

## Source signal

- 2026-04-29 Stuffolio Phase 5c production deploy session. Hotfix commit `45f90604` shipped at 17:38 PDT. bug-echo was the natural closure tool but was not invoked.
- The session retrospective at session end identified the three gaps above as the cause.
- Plan authored same day; deferred to a future session because the Stuffolio session was at its time budget.
