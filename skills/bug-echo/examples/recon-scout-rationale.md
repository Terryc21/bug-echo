# Recon scout rationale (Step 2.5)

The v1.2.0 release added a `Step 2.5: Recon scout` between pattern validation and the full scan. This doc records the evidence that motivated it, so future contributors can decide whether to extend, narrow, or remove the step based on real-run data rather than speculation.

## The question

Should bug-echo always run the full `Scan → Classify → Rate → Write` ceremony, or should it match report shape to actual signal?

## The data

Reviewed 18 bug-echo runs against a 600-file production Swift codebase (Stuffolio, builds 28-35) between 2026-05-03 and 2026-06-04. Each run produced a `.agents/research/YYYY-MM-DD-bug-echo-<slug>.md` report. Counted:

- Number of candidate sites the validated pattern matched (pre-classification).
- Number of confirmed BUG findings (post-classification).
- Report length in lines.
- Whether the report's findings drove a follow-up commit.

## What the data showed

**Candidate counts and BUG yields, sorted by yield:**

| Run | Candidates | Confirmed BUGs | Report lines |
|---|---|---|---|
| protection-class-mismatch | 8 | **0** | 79 |
| try-fetch-rollback | 4 | **0** | 102 |
| deep-viewbuilder-crash | 4 | **0** | 245 |
| nested-navstack-macos-detail-pane | 14 | 1 | 88 |
| swiftui-typecheck-complexity | 601 (broad) | 1 | 105 |
| 7-pattern-sweep | varied | 1 | 80 |
| labeledurl-drift-class-followup | 16 | 2 | 215 |
| (11 more runs) | ... | 3-66 | 88-261 |

**The crux:**

- **3 runs (17%)** found zero bugs after a full report. The structure carried more weight than the findings did.
- **4 more runs (22%)** found 1-3 bugs. The full report's OK/REVIEW/WATCH sections, exception lists, and detailed scaffolding overshot the actual scope.
- **The remaining 11 runs (61%)** found 4+ bugs where the full report's structure pulled its weight.

That's a 39% mismatch between report shape and finding density — high enough that matching shape to signal was worth a structural change.

## The design

The recon scout buckets candidate counts into three response shapes:

| Bucket | Report shape | Why |
|---|---|---|
| **0** | One-line note, no file written | The pattern was already localized to the just-fixed site. The user needs to know this happened, but a 79-line file documenting "no bugs found" is over-spend. |
| **1-5** | Inline rated table, no file written | The findings are easy to act on in conversation. A `.agents/research/` file adds disk artifact + lookup cost without adding context the user can't already see in the message. |
| **6+** | Full `.agents/research/` write | Structured exception lists, OK/REVIEW/WATCH sections, and detail blocks pay for themselves at this density. |

## What this is NOT

- **NOT a performance optimization.** The full ceremony isn't slow — it's *over-shaped*. The win is matching output to actual signal, not saving wall-clock.
- **NOT a quality reduction.** The same classification rules apply. A 1-bug finding in the inline mode gets the same rating-table treatment as a 1-bug finding inside a 6+ report.
- **NOT a heuristic for which patterns are "important".** The bucket reflects the codebase state at scan time, not the pattern's general severity. A 0-bucket run on the same pattern in a different codebase could be a 30-bucket run.

## Override conditions

The skill honors three explicit overrides where the bucket is wrong:

1. The user asked for a written report (`/bug-echo write-report` or similar).
2. The pattern is being tracked across multiple releases (sweep-style, multi-pass cleanup). The next run benefits from referencing this one.
3. A 1-5 bucket contains a release-blocking finding. The structured report shape is appropriate even for one bug if it's load-bearing.

These overrides are noted in the SKILL.md Step 2.5 specification.

## What we'd want to measure next

To validate this change after a v1.2 adoption period:

- Does the 0-bucket rate stay around 17%, or do users start running bug-echo on patterns they wouldn't have before (because the cost is now lower)?
- Do users running 1-5 bucket follow-ups in conversation report better fix outcomes than the same pattern in a written report would have produced?
- Does the 6+ bucket continue to use the full ceremony, or does the smaller threshold cause feature drift where written reports get reserved for 20+ findings only?

The retrospective above is N=18 on one codebase. It's a strong signal for an MVP change, not a robust pattern study. Reconsider if real-world adoption data diverges.
