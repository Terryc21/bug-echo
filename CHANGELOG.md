# Changelog

All notable changes to bug-echo. Version numbers match the `metadata.version` field in
`skills/bug-echo/SKILL.md` and the `version` field in `.claude-plugin/plugin.json`.

## v1.5.1 (2026-08-23)

First real fixture run. **PASS, 6/6 exact, 0 failures** — and CANON is no longer unverified.

- **v1.4.0's CANON feature is confirmed working.** It shipped built, reviewed, and never
  executed. Run by an agent given the Step 4 rules verbatim and no access to the answer key, it
  found the reference implementation, tagged it `OK (CANON)`, emitted the
  `**Reference implementation:**` line, and cited it in both BUG rows' Suggested fix — the
  whole chain, unprompted. That moves the feature from *code-verified* to *actually works*.
- **`score.py` gains a ±3-line tolerance**, recorded as a note rather than silently allowed.
  The run cited the CANON site at its function signature (`:22`) where the key names the fetch
  call (`:24`). Both are defensible — for a CANON site the "shape to converge on" is arguably
  the whole function — but exact-line matching reported a correct identification as MISSING.
  Negative controls were re-run after the change to confirm detection did not weaken.

Second harness defect the fixture has caught in two runs (the first was the
`**Reference implementation:**` parser bug in v1.5.0). Both were found only by running it.

## v1.5.0 (2026-08-23)

First test of whether bug-echo's **judgment** is correct, rather than whether it activates.

- **`fixtures/swift-try-fetch/`** — a small fake Swift project where every answer is known in
  advance: two real BUGs, two genuine OKs that match the pattern textually, one CANON site, one
  deliberate gray-zone WATCH, and a decoy (`try?` on a file read, not a store fetch) that an
  over-broad pattern would wrongly flag.
- **`fixtures/setup.sh`** — materializes the fixture as a throwaway git repo with real history:
  commits the seed file buggy, fixes it, commits again. bug-echo's primary mode reads
  `git log -p -1` and self-validates against `git show HEAD~1:...`, so a fixture without
  commits cannot exercise it. Builds outside this repo so a run can never dirty bug-echo's own
  tree, and refuses to delete a destination it did not create.
- **`fixtures/score.py`** — compares verdicts only, never prose, because an LLM-driven skill
  produces different wording every run. The tolerance rule lives in each answer key: BUG↔OK and
  anything↔CANON always fail; BUG↔WATCH and WATCH↔OK are notes. A flaky suite gets ignored,
  which is worse than no suite.
- **Every run prints its own scope** — "verified on SWIFT only (6 sites, 1 fixture)". A green
  result must not be read as "classification works" when it means "classification works on
  Swift." Same discipline as the `evals/README.md` scope statement and the examples' version
  stamps.

Harness verified in both directions before being trusted: a correct report passes 6/6; an
all-OK report fails on three strict misses; a WATCH scored BUG passes as a judgment call; the
decoy flagged as BUG fails. ⚠️ The positive control **failed on its first run** and caught a
real parser bug — `**Reference implementation:**` usually sits directly under a `## BUG
Findings` heading, so a backward scan scored the CANON site as BUG. A harness tested only
against passing input would have shipped that.

Two wrong line numbers in the first answer key were found the same way, by grepping the
materialized fixture rather than the source as written. `fixtures/README.md` carries that as a
standing warning for anyone adding a fixture.

**Not covered:** any language but Swift, and the three scale-gated paths (>500 files, ≥25
tighten offer, ≥6 already-swept exclusion). Those need fixtures far larger than this one.

## v1.4.3 (2026-08-23)

Examples-hygiene pass. No behavior change.

- **Every example now states which release it was written against**, in an `[!IMPORTANT]`
  header naming what changed since and what still holds. The two reports are v1.2.0-era; the
  hardening rationale is v1.3.x. Silent staleness becomes visible staleness — a reader can
  tell at a glance whether a step number or report shape predates their installed version.
- **`recon-scout-rationale.md` gets the strongest note**: it is not merely dated, it is an
  actively *incomplete* description of Step 2.5, which gained two sub-steps in v1.3.0 that the
  doc never mentions. Its header now points at the hardening doc and `SKILL.md`.
- **`describe-mode-await-in-forEach.md`:** added the missing `WATCH findings: 0` line so both
  examples show the same four-bucket vocabulary; marked the two invented incident claims as
  illustrative (the file is flagged synthetic at the top, but those read as fact mid-document);
  corrected `ast-grep --help scan` → `ast-grep scan --help`, replaced the `--pattern` form with
  `ast-grep run`, and removed a `| xargs grep -l` pipeline that could not work as written
  (`ast-grep` prints match output, not a file list).
- **`large-codebase-hardening-rationale.md`:** "four changes" → "five", in both the prose and
  the section heading. The table always had five rows.
- **README:** the vocabulary section and TL;DR both said `BUG / OK / REVIEW`, omitting WATCH —
  the same defect as the describe-mode example, in the more-read file. Found by auditing the
  README rather than assuming it was current.

Closes findings #3, #4, #7, #8 from the `/skill-reviewer` pass, plus the README instance
that pass did not cover.

## v1.4.2 (2026-08-23)

Documentation and eval coverage for v1.4.0's CANON feature, which shipped with neither.

- **New example: `examples/canon-reference-implementation.md`.** A real run (Stuffolio,
  2026-08-23) where two correct siblings existed and five copies had drifted. Shows the
  `OK (CANON)` classification, the `**Reference implementation:**` line, and a BUG finding
  whose Suggested fix cites the reference instead of inventing one. Includes the
  no-CANON-site case, since that is the normal outcome.
- **Four eval cases added** (20 → 24). Three cover trigger phrases that were declared in the
  `description` string but never tested — `run bug-echo`, `find other instances`,
  `after-fix scan`. All five declared triggers are now covered verbatim. The fourth is a
  CANON-shaped invocation.
- **`trigger-eval-clean.json` is now generated, not hand-maintained.** Both files carried the
  same 20 cases by hand with nothing detecting divergence. New `evals/README.md` documents the
  one-line regeneration command and states plainly what the evals do NOT test — classification,
  CANON selection, bucket choice, report shape, or any scale-gated behavior.

The provenance note in the new example is worth keeping: the
`2026-05-03-bug-echo-deep-viewbuilder-crash.md` report was already writing CANON findings in
prose ("the canonical fix in this codebase. Any future fix should reference that pattern
explicitly") months before the feature existed. v1.4.0 ratified practice rather than inventing
a capability.

Found by the same `/skill-reviewer` pass as v1.4.1 (findings #2, #5, #6).

## v1.4.1 (2026-08-23)

Corrects a factual error in the Step 2.5 evidence. No behavior change.

- **`deep-viewbuilder-crash` recorded 0 confirmed BUGs; the actual value is 1.** The run's
  own report in the same directory states `BUG findings: 1` and carries a rated 🟡 HIGH row
  for `RMARow.body`, fixed the same day. The likely cause is that the run's other three hits
  were WATCH and the tabulation collapsed "mostly WATCH" to zero — but the column counts
  confirmed BUGs post-classification, and that value is 1.
- **Two derived percentages move; the headline does not.** The zero-bug bucket goes 3 runs
  (17%) → 2 runs (11%), and the 1-3 bucket goes 4 (22%) → 5 (28%). The **39% shape/signal
  mismatch that justifies Step 2.5 is unchanged** — 7 of 18 runs either way, because the
  corrected row was already on the mismatch side of the line, just in the adjacent bucket.
- **The stale split had propagated into `SKILL.md:218`** ("3 found zero real bugs and another
  4 found 1-3"), which is loaded on every run. Corrected there too. The 39% figures in
  `README.md` and this changelog were already right and are untouched.
- The `(11 more runs)` BUG-yield range read `3-66`, which overlapped the "4+ bugs" partition
  it belongs to. Corrected to `4-66`.

Found by a `/skill-reviewer` pass. The correction is annotated inline in
`recon-scout-rationale.md` rather than silently applied, so a reader can see what the number
was and why it changed.

## v1.4.0 (2026-08-23)

Adds one sub-label so a sweep can report that the fix already exists somewhere in the
codebase. Behavior change, hence the minor bump — v1.3.4 was documentation-only.

- **`OK (CANON)` sub-label in Step 4.** An OK site can now be marked as the *reference
  implementation*: correct, and the shape the BUG findings in the same sweep should
  converge on. It is a sub-label of OK, not a fifth classification — the verdict taxonomy
  the sub-agent contract depends on (`BUG | WATCH | OK | REVIEW`) is unchanged, as is the
  dedup/reconciliation logic.
- **BUG rows cite the reference when one exists.** `Suggested fix` points at `file:line`
  rather than describing a fix from scratch, and the finding rates as propagation rather
  than design (`verified` confidence; Risk-of-Fixing and Fix Effort measured against
  copying the reference).
- **`canon` flag added to the sub-agent return contract, plus a merge step that propagates
  it.** A sub-agent sees only its own batch, so the batch holding the reference is usually
  not the batch holding the findings that should cite it. Without the propagation step the
  citation would silently fail on exactly the >500-file sweeps where re-deriving a solution
  costs the most.
- **Inline mode never omits a CANON site**, despite its general "skip the OK section" rule —
  a reference implementation is the answer to every row in the table, not noise.

🛑 **Most sweeps will have no CANON site, and the skill says so explicitly.** A young repo, a
first sweep against a uniformly-broken pattern, or a novel bug has no correct instance to
point at; in that case every addition above is a no-op and the report is byte-identical to
what v1.3.4 produced. The rule warns against inventing a reference to satisfy it, since
pointing findings at a wrong "answer" is worse than having none.

**Origin:** a Stuffolio sweep found five near-duplicate functions reporting success after
conditional writes that could collectively write nothing — while two siblings in the same
codebase already implemented the correct counting fix, one of them carrying a comment
describing that exact defect. The sweep classified both correct sites as bare `OK`, so the
most useful fact it produced — *the answer is already here* — was discarded before the
report was written.

## v1.3.4 (2026-08-06)

Documentation-only pass. No behavior change — every step, threshold, and output format is
identical to v1.3.3.

- **Release notes moved out of `SKILL.md` into this file.** Five release sections (v1.3.0 through v1.3.3, plus v1.2.0) were being loaded into the model's context on every single run, describing version history to the one reader who cannot act on it. Removing them leaves `SKILL.md` addressed entirely to the agent executing the workflow.
- **`Deferred to v1.4+` section removed; its four cross-references inlined.** The section described features that do not exist, and four places in the body pointed at it. Each pointer now states the operative rule directly — don't read prior reports as evidence, there is no catalog mode, there is no suppression file, don't emit a JSON sidecar — so the constraint is legible where it applies.
- **Two all-caps directives replaced with their reasoning.** `YOU MUST EXECUTE THIS WORKFLOW` and "findings missing any of the six dimensions are invalid" now explain *why* — that a description of the workflow leaves the user where they started, and that a finding missing Risk of Not Fixing or Blast Radius silently drops out of triage.
- **Scale invariants moved to the README.** The four-point contract was addressed to future contributors, not to the running agent. `SKILL.md` keeps a compact `Scale gates` section naming the three thresholds (≥6, ≥25, >500 files) and why a small repo should never feel them.
- **`Target` column documented as a deliberate omission.** The Issue Rating Table has nine columns where some conventions carry ten; the skill now says why (every finding prints its own `file:line` directly beneath the table) rather than leaving a silent mismatch.
- **`SKILL.md` frontmatter version corrected to match the manifest.** v1.3.3 bumped `plugin.json` to 1.3.3 but left the frontmatter reading `1.3.2` — the same class of drift v1.3.3 fixed, one level down.

`SKILL.md`: 587 → 541 lines.

## v1.3.3 (2026-08-06)

Release-metadata fix. No behavior change — the skill's logic is identical to v1.3.2.

- **`plugin.json` version corrected: `1.1.1` → `1.3.3`.** The manifest was never bumped across the v1.2.0, v1.3.0, v1.3.1, or v1.3.2 releases — it still read `1.1.1` at the very commit tagged `v1.3.2`. Consequences: the marketplace installed to a `bug-echo/1.1.1` path while serving v1.3.2 behavior, and any tool that reads the manifest (`claude plugin validate`, an update checker, a marketplace listing) reported a version four releases stale, so there was no reliable way to tell whether an install was current. Found 2026-08-06 while auditing the skill after two production runs. Shipped as a new patch release rather than re-pointing the `v1.3.2` tag, since that tag is already published and rewriting it would break anyone pinned to it.

## v1.3.2 (2026-07-21)

Correctness guard against a self-referential inference loop. Universal (not size-gated) and inert unless it applies.

- **Guard against inferring from bug-echo's own fix commit (Step 2B):** when the diff source falls back to the most recent commit (`git log -p -1`) and that commit's subject starts with `bug-echo:` (the prefix Step 6 uses for applied-fix commits), Step 2B no longer infers a pattern from it — doing so would just re-derive the pattern those fixes already resolved. It now falls back to Step 2A (described mode) with a short explanation and a pointer to name a different fix. Applies only to the most-recent-commit source; staged and unstaged diffs are genuine new work and are never blocked.

## v1.3.1 (2026-07-21)

Spec hardening for the large-codebase scan path. No new user-facing capability — this defines behavior that the `Over 500 files` branch already invoked but left under-specified, which is why it's a patch bump rather than a minor. The sub-500-file common path is untouched (see § Scale invariants).

- **Sub-agent aggregation contract (new Step 3.5):** the `Over 500 files` branch of Step 3 previously said only "aggregate results in the main agent." Step 3.5 now specifies exactly what each sub-agent receives (validated pattern verbatim, its file batch, the Step 4 classification rules copied verbatim so every batch judges against identical criteria), what it returns (a structured `{file, line, snippet, classification, rationale}` list, not prose), and how the main agent merges: deduplicate on the `(file, line)` key, then spot-check for near-identical code shapes that got different verdicts across batches and re-classify those authoritatively. Prevents cross-batch duplicates and inconsistent classifications on runs that split into multiple sub-agents. Applies only in the >500-file branch.
- **Doc fix:** corrected four stale `§ Deferred to v1.3+` cross-references (they pointed at a section retitled to v1.4+ in the v1.3.0 release, leaving the anchors dangling).

## v1.3.0 (2026-07-21)

Large-codebase hardening. All three additions are threshold-gated branches; the sub-500-file common path is unchanged from v1.2.0. See the new § Scale invariants (Pre-flight) for the guarantee. Rationale and traced examples for the whole v1.3.x hardening arc (through 1.3.2): [large-codebase-hardening-rationale.md](examples/large-codebase-hardening-rationale.md).

- **Already-swept exclusion (Step 2.5):** on a large codebase swept across multiple sessions, sites fixed-and-committed in a prior bug-echo run no longer resurface as fresh candidates. Gated to fire only at ≥6 candidates *and* when the repo has prior `bug-echo:` commits; below the gate it is a single empty `git log` call. Cross-references git commit history (ground truth of what was fixed), capped at the 50 most recent `bug-echo:` commits so cost is bounded by commit count, not calendar time. Re-reads live source before excluding, so a reintroduced pattern is still caught — git only says *where to look*, never "already fixed."
- **High-count tighten offer (Step 2.5):** when a validated pattern returns ≥25 candidates (an absolute threshold, not relative to repo size), offers to tighten the pattern before classifying, rather than grinding through hundreds of mostly-OK sites. Directly addresses the "heavily overloaded with false positives" limit. Below 25, never shown.
- **Scale invariants (Pre-flight):** a standing contract that large-codebase logic must stay threshold-gated and the small-codebase path must remain untouched, so future edits can't quietly tax the common case.

## v1.2.0 (2026-06-06)

- **Recon scout (Step 2.5):** new pre-flight count between pattern validation and full scan. Buckets candidate count into 0 / 1-5 / 6+ and matches report shape to actual signal. Catches the case where the original fix was already localized (one-line note in conversation, no `.agents/research/` write) and the case where there are 1-5 sibling instances (lightweight inline report). Reserves the full file-write ceremony for 6+ candidates where the structured report carries its weight. Origin: 18-run retrospective on a 600-file Swift codebase showed ~39% of runs would benefit from a lighter-weight report shape. See [recon-scout-rationale.md](examples/recon-scout-rationale.md) for the full evidence.
- **Conditions form in Step 2A:** suggested form for describing multi-condition pattern shapes (e.g., "Identifiable struct + ephemeral constructor + ForEach consumer"). Optional; free-form prose still works. Helps users articulate patterns that only fire when 2-3 conditions hold together — the most common shape for false-positive-prone bugs.
