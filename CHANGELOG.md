# Changelog

All notable changes to bug-echo. Version numbers match the `metadata.version` field in
`skills/bug-echo/SKILL.md` and the `version` field in `.claude-plugin/plugin.json`.

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
