# bug-echo 1.8.0 validation — October 12, 2026

The same shared skill was exercised through the real Codex and Claude Code CLIs on isolated fixture repositories. These are static code-analysis scans, not builds or runtime tests of an application.

## Live scan results

| Runtime | Scenario | Result | Verdict checks | Source / HEAD / index |
|---|---|---|---|---|
| codex | Swift: committed fix | PASS | 6/6 accepted · 0 note(s) · 0 failure(s) | Unchanged |
| codex | Swift: unstaged fix with unrelated staged and unstaged changes | PASS | 6/6 accepted · 0 note(s) · 0 failure(s) | Unchanged |
| codex | TypeScript: described async-forEach pattern | PASS | 2/2 accepted · 0 note(s) · 0 failure(s) | Unchanged |
| claude | Swift: committed fix | PASS | 6/6 accepted · 1 note(s) · 0 failure(s) | Unchanged |
| claude | Swift: unstaged fix with unrelated staged and unstaged changes | PASS | 6/6 accepted · 0 note(s) · 0 failure(s) | Unchanged |
| claude | TypeScript: described async-forEach pattern | PASS | 2/2 accepted · 0 note(s) · 0 failure(s) | Unchanged |

The Swift scans found both intended sibling bugs and distinguished intentional test calls and the best-effort cache. The TypeScript scans found the premature-completion bug and accepted intentional background telemetry. Both unstaged scans used the index as their old-side baseline. Reports included ratings, user impact, and correct reference implementations.

Both runtimes loaded version 1.8.0 from the candidate skill directory. Transcript review found no reads of the answer keys. Expected verdict labels were removed from the fixture source comments; behavioral contracts were retained. The scan prompt requested report-only work and no source edits or commits.

## Harness repairs and review

- Repaired a scorer that associated Markdown table citations with the preceding row, and that mistook historical baseline citations for live findings.
- Kept BUG-versus-OK mismatches and wrong reference sites as failures. An explicit REVIEW for a site with a clear expected verdict also fails.
- Accepted either the fixed seed or the Result-returning sibling as a CANON reference. They are both correct; the former preserves the seed fix's API. Merely calling both ordinary OK still fails the reference check.
- Restored the smoke test's explicit acceptance of fetch errors after removing its answer labels. This retained its original intended behavior without giving the evaluator the verdict.
- Clarified the shared report contract after earlier Claude runs paraphrased the CANON label. The final scans used the same unchanged skill files hashed below.
- Final grading was applied to the original saved reports without rewriting their contents. Six scorer unit tests, including ten positive/negative end-to-end controls, passed.
- Codex skill validation, both Claude plugin manifest validations, bundled Markdown links, version alignment, and git whitespace checks passed.

## Reproduce

```bash
python3 -m unittest discover -s fixtures -p test_score.py
python3 fixtures/cross_runtime.py --output /absolute/path/to/new-results
```

Requires signed-in CLIs and consumes their normal account usage. CLI versions recorded for these runs:

```text
codex-cli 0.160.0
2.1.285 (Claude Code)
```

## Tested skill identity

- `skills/bug-echo/SKILL.md` SHA-256: `e972566ec05dd064d5298b577bfc2a5a94ea62bfb9f8ce2b75f95ddfa6bf5167`
- `skills/bug-echo/WORKFLOW.md` SHA-256: `dda454e87ce0e42424ba4e14fe287d87cb580218a30e0efbb813f8bf308a155e`

## Limits

This checks small Swift and TypeScript fixtures with explicit invocation. It does not establish results for all languages, automatic skill selection, the >500-file batching branch, AST-grep, guided fixes/commits, or every Codex/Claude release and model. LLM wording and judgment can vary between runs; the fixture tolerance rules are explicit.
