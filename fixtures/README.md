# Fixtures — QA for bug-echo itself

The `evals/` directory tests whether the skill **activates**. This directory tests whether it
is **right**.

A fixture is a small fake project where every answer is known in advance. Run bug-echo against
it, compare the verdicts to the answer key, and you learn whether the skill's judgment still
works. It is a calibration weight, not a warm-up lap: you reach for it when you have changed
bug-echo, not when you are using it.

**Users never touch this.** It ships in the repo the way a test suite ships with a library.

## When to run it

| Situation | Run the fixture? |
|---|---|
| You edited Step 4's classification rules | **Yes** — this is the moment it exists for |
| You changed the sub-agent contract or merge logic | **Yes** |
| You added a classification (like v1.4.0's CANON) | **Yes** |
| A real run returned a surprising result and you want to know if the skill is misbehaving | **Yes**, diagnostically |
| You are using bug-echo on real code | No. It is not in that path. |

## Running it

```bash
bash fixtures/setup.sh                  # builds /tmp/bug-echo-fixture-swift-try-fetch
cd /tmp/bug-echo-fixture-swift-try-fetch
# run bug-echo here in inferred mode; save or paste its report to a file
python3 <repo>/fixtures/score.py report.md swift-try-fetch
```

`setup.sh` creates the scratch repo **outside** this one, so a fixture run can never dirty
bug-echo's own tree — which matters, because bug-echo's Pre-flight step refuses to scan a dirty
repo. It also refuses to delete a destination that isn't marked as its own scratch dir.

## Why the fake git history

bug-echo's primary mode infers the pattern from a real diff (`git log -p -1`) and self-validates
it against the pre-fix file (`git show HEAD~1:...`). Neither works on a bare directory. So
`setup.sh` commits the fixture with `SettingsStore.swift` **buggy**, fixes only that file, and
commits again. HEAD is then a genuine fix commit and HEAD~1 a genuine baseline.

This is the part a JSON case list cannot fake, and the reason a fixture is a directory of files
plus a script rather than another eval file.

## Scoring: verdicts only, never prose

bug-echo is LLM-driven — two runs produce different wording. `score.py` compares **only** the
BUG / WATCH / OK / CANON label attached to each `file:line`, and ignores everything else.

The tolerance rule lives in each fixture's `answer-key.json`, not in the script:

| Disagreement | Result | Why |
|---|---|---|
| BUG ↔ OK | **FAIL** | A real miss in either direction |
| anything ↔ CANON | **FAIL** | A wrong reference points every other finding at the wrong answer |
| BUG ↔ WATCH, WATCH ↔ OK | **note** | Honest judgment boundary. Failing here yields a flaky suite, and a flaky suite gets ignored — worse than no suite. |

## What the fixture proves, and what it does not

✅ Classification on Swift, for one pattern, at 6 sites.
✅ Inferred mode end-to-end: diff parsing, self-validation, exclusion of the just-fixed site.
✅ That an over-broad pattern gets caught (`Support.swift` is a deliberate decoy — a `try?` on
a file read, not a store fetch; flagging it means the pattern generalized past the seed).

❌ **Any other language.** `score.py` prints its own scope on every run for exactly this reason:
a green result must not be read as "classification works" when it means "classification works
on Swift."
❌ The >500-file batched path, the ≥25 tighten offer, and the ≥6 already-swept exclusion. Those
need fixtures far larger than this one and are gated behaviors that degrade to the common path.

## Harness self-test

The scorer's own behavior was verified in both directions before it was trusted:

| Control | Expected | Result |
|---|---|---|
| Correct report | PASS 6/6 | ✅ |
| Everything scored OK | FAIL — 3 strict misses | ✅ |
| WATCH site scored BUG | PASS — allowed by `also_accept` | ✅ |
| Decoy flagged as BUG | FAIL — `must_not_flag` | ✅ |

⚠️ The positive control **failed on its first run** and caught a real parser bug: the
`**Reference implementation:**` line usually sits directly beneath a `## BUG Findings` heading,
so a naive backward scan scored the CANON site as a BUG. The parser now checks that marker
first. A harness that had only ever been tested against a passing report would have shipped
that.

## First real run — 2026-08-23

Run against a fresh fixture by an agent given the Step 4 rules verbatim and **no access to the
answer key**, to keep the judgment independent of the person who wrote the expectations.

**Result: PASS, 6/6 exact, 0 failures.**

| Site | Expected | Got |
|---|---|---|
| `ItemStore.swift:22` | BUG | BUG |
| `CardView.swift:19` | BUG | BUG |
| `SafeStore.swift:24` | CANON | CANON (cited `:22`) |
| `ItemStoreTests.swift:13` | OK | OK |
| `ItemStoreTests.swift:21` | OK | OK |
| `PrefetchCache.swift:25` | WATCH | WATCH |

Three things the run established that no amount of reading could:

1. **v1.4.0's CANON feature works.** It had been written, reviewed, and never executed. The run
   found the reference implementation, tagged it `OK (CANON)`, emitted the
   `**Reference implementation:**` line, and cited it in both BUG rows' Suggested fix — the
   whole chain, unprompted.
2. **The scope note earned its place.** The narrow `try? ... .fetch` pattern could not match
   `SafeStore`, which uses `do/try/catch`. The run found it by reading and said so explicitly.
   Without that note the CANON site would have been invisible to a correctly-narrow pattern.
3. **The decoy held.** `Support.swift:36` was not flagged, and the run volunteered why —
   flagging it would mean the pattern had generalized past the seed.

⚠️ **The run also exposed a harness defect.** It cited the CANON site at `:22` (the function
signature) where the key says `:24` (the fetch call). Both are defensible — for a CANON site,
"the shape to converge on" is arguably the whole function. The scorer had been matching lines
exactly, so it reported a correct identification as MISSING. Fixed with a ±3-line tolerance
that records the variance as a note. The negative controls were re-run afterward to confirm the
tolerance did not weaken real detection.

That is twice now the fixture has found a bug in its own harness rather than in the skill —
first the `**Reference implementation:**` parser bug, now the line-matching brittleness. Both
were found only by running it, which is the argument for running it.

## Adding a fixture

1. `fixtures/<name>/src/` — the fake project. Include at least one deliberate BUG, one genuine
   OK that matches the pattern textually, and a decoy that a too-broad pattern would catch.
2. `fixtures/<name>/answer-key.json` — verdicts with a `because` citing the SKILL.md rule each
   depends on, so a rules change can be grepped back to the expectations it affects.
3. `bash fixtures/setup.sh <name>` — the script needs a seed file it knows how to fix; adjust
   the heredoc if your fixture's seed differs.

🛑 **Verify the line numbers against the built fixture, not against the source you wrote.**
This fixture's first answer key had two wrong line numbers (`CardView.swift` and the decoy),
found only by grepping the materialized repo. Wrong line numbers produce spurious MISSING
failures that look like real regressions.
