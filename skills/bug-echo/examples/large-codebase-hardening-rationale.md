# Large-codebase hardening rationale (v1.3.x)

> [!IMPORTANT]
> **Written against v1.3.0–1.3.2 and current for that arc.** The five thresholds below (≥6,
> ≥25, >500 files, 50-commit cap) are unchanged as of v1.4.x. v1.4.0 added one thing this doc
> predates: the `OK (CANON)` classification, which extends the Step 3.5 sub-agent contract
> with a `canon` field and a cross-batch propagation step. See
> [CHANGELOG.md](../../../CHANGELOG.md) and `SKILL.md` § Step 3.5.

The v1.3.0–1.3.2 releases added five changes aimed at one problem: bug-echo runs on codebases far larger than the one it was first tuned against, and a few of its steps behaved badly at that scale. This doc records why each change exists and — just as important — what constrains it, so future contributors extend the large-codebase path without taxing the small one.

Companion doc: [recon-scout-rationale.md](recon-scout-rationale.md) covers the v1.2.0 Step 2.5 recon scout, which this arc builds on.

## The question

bug-echo was tuned against a ~600-file Swift codebase. On a 500K+ LOC project (5,000+ files), which steps degrade, and can they be fixed without changing how the skill runs on a 20-file package?

The answer had to satisfy one hard constraint: **the common path must not get slower or more talkative.** Most codebases are small. A change that helps a 5,000-file repo but adds a prompt or a git call to a 20-file repo is a net loss. That constraint produced the § Scale invariants section in SKILL.md and shaped every feature below.

## The five changes

| Change | Version | Problem it solves | How it's bounded |
|---|---|---|---|
| Already-swept exclusion (Step 2.5) | 1.3.0 | Multi-pass sweeps re-surface sites you already fixed in a prior run | Gated: ≥6 candidates AND prior `bug-echo:` commits exist. Below the gate, one empty `git log` call. |
| High-count tighten offer (Step 2.5) | 1.3.0 | An over-broad pattern routes hundreds of mostly-OK sites into classification | Gated: ≥25 candidates (absolute, not a fraction of files) |
| Scale invariants (Pre-flight) | 1.3.0 | Future edits could quietly tax the common path | A standing contract, not runtime logic |
| Sub-agent aggregation contract (Step 3.5) | 1.3.1 | The >500-file batched scan merged sub-agent results with no defined rules | Applies only in the >500-file branch |
| Self-referential-commit guard (Step 2B) | 1.3.2 | Re-running bug-echo after its own fix commit infers from that commit | Universal but inert unless HEAD is a `bug-echo:` commit |

## Why these thresholds, specifically

**Already-swept exclusion — why ≥6, and why git history not prior reports.** The gate is ≥6 because below that the recon scout already routes to the lightweight `none`/`inline` path, where re-work is cheap and the extra git walk isn't worth it. The exclusion reads git *commit* history (the ground-truth record of what was actually fixed) rather than prior `.agents/research/` reports, because the Freshness rule forbids prior reports as a finding source. The 50-commit cap on the history walk bounds cost by commit count, not calendar time — a project that has used bug-echo for a year but only 30 times pays for 30 commits, not 365 days. And the exclusion re-reads live source before dropping a candidate: git only says *where a file was touched*, never "this line is still fixed." A pattern reintroduced after a prior sweep is still caught.

**High-count tighten offer — why 25, why absolute.** The number the user is being saved from is *classification cost*, and classification cost scales with match count, not repo size. Classifying 30 sites is the same work whether the repo has 40 files or 5,000. So the threshold is an absolute match count (25), not a fraction of files. A 40-file project where a pattern legitimately appears 30 times gets the same offer as a 5,000-file one — correctly, because the cost being avoided is identical. Below 25, the offer never shows; interrupting the user is the worse trade when classification is cheap.

**Self-referential guard — why universal, not gated.** Unlike the two count-gated features, this one applies to every codebase. It costs a single `git log -1 --format=%s` and is a no-op unless HEAD's subject starts with `bug-echo:`. There's no scale dimension to the bug it prevents: the degenerate loop (infer a pattern from the fixes that already resolved that pattern) is equally wrong on a 20-file repo. So it's universal but self-limiting — the check is free and silent unless it fires.

## The two guards, traced

For the two features with visible runtime behavior, here's what a user actually sees.

### Already-swept exclusion (Step 2.5)

Second pass at a pattern on a large codebase, a week after the first sweep:

```
/bug-echo "force-unwrapped @EnvironmentObject access in a view body"
```

```
Recon scout: 9 raw matches for the pattern across Sources/**/*.swift.
Checking git history for prior bug-echo sweeps of this shape...
  - 3 of the 9 sit in files touched by prior `bug-echo:` commits.
    Re-read each against live source: all 3 still fixed. Excluding.
  - 6 fresh candidates remain.

6 fresh → full report mode. Proceeding to scan + classify.
(9 raw matches, 3 already swept in prior bug-echo commits, 6 fresh.)
```

The reconciliation line is the point: the user sees *why* 9 became 6, and trusts that the 3 excluded sites were re-verified against current source, not dropped on faith. On a first-ever run, or a small repo with no `bug-echo:` commits, none of this appears — the gate is closed and the scout behaves exactly as it did in v1.2.

### Self-referential-commit guard (Step 2B)

User runs bug-echo, applies fixes, commits via the Step 6 flow, then runs bug-echo again immediately:

```
/bug-echo
```

```
No staged or unstaged changes. Falling back to the most recent commit.
Most recent commit subject: "bug-echo: applied 3 fixes from
force-unwrap-envobject report"

That's a bug-echo fix commit — inferring from it would just re-derive the
pattern it already fixed. Switching to described mode.

What pattern should I scan for? (Or point me at a different fix, e.g. HEAD~1.)
```

Without the guard, Step 2B would parse bug-echo's own diff, construct a pattern from the lines it just fixed, self-validate it against the pre-fix file (which still has the bug, so validation *passes*), and produce a scan that re-finds nothing new — a confusing, wasted run that looks like it worked. The guard turns that into a one-line redirect.

## What this is NOT

- **NOT a rewrite of the scan engine.** Every change is an additive branch or a guard. The core infer → validate → scan → classify → report loop is unchanged. A small codebase runs the exact v1.2 path plus, at most, one empty `git log` call.
- **NOT a general performance pass.** These target correctness and over-spend at scale (re-surfaced sites, un-merged batches, degenerate inference), not wall-clock. bug-echo was never slow; it was under-specified in a few places that only bite large repos.
- **NOT size-detection heuristics baked into the default.** Nothing here inspects repo size to change default behavior. Features enter by explicit threshold (candidate count, file count) or by a specific condition (HEAD is a bug-echo commit). See § Scale invariants for the contract that keeps it that way.

## What we'd want to measure next

These changes shipped without the kind of retrospective that motivated the recon scout (that had N=18 real runs; these are reasoned from the same codebase's behavior, not a fresh study). Worth measuring after an adoption period:

- **Already-swept exclusion:** what fraction of large-codebase runs actually hit the ≥6 gate *and* find prior `bug-echo:` commits? If it's rare, the feature is dead weight; if common, the reconciliation-line UX matters and should be refined.
- **High-count tighten offer:** when offered, how often do users pick "Tighten first" vs. "Classify all"? A high "Classify all" rate would suggest 25 is too low a threshold for real patterns.
- **Aggregation contract:** on real >500-file runs, how many cross-batch reconciliations occur per run? Zero would mean the spot-check is theoretical; a steady nonzero count would justify the contract's existence with data.
- **Self-referential guard:** how often does it actually fire? If never, it's cheap insurance; if occasionally, it confirms the double-run pattern is real user behavior worth guarding.

The invariants in SKILL.md are the durable part of this arc. The specific thresholds (6, 25, 50) are the tunable part — reconsider them if adoption data diverges, but never at the cost of the small-codebase path.
