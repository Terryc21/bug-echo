# Trigger evals

Two files, 24 cases, 14 expected-trigger / 10 expected-not.

| File | Contents | Purpose |
|---|---|---|
| `trigger-eval.json` | `query` + `should_trigger` + `note` | **The source.** Edit this one. |
| `trigger-eval-clean.json` | `query` + `should_trigger` only | Generated. Feed this to a grader so the `note` rationale can't leak the expected answer. |

## 🛑 Never hand-edit `trigger-eval-clean.json`

It is derived. Add or change cases in `trigger-eval.json`, then regenerate:

```bash
python3 -c "
import json
src = json.load(open('evals/trigger-eval.json'))
clean = [{'query': c['query'], 'should_trigger': c['should_trigger']} for c in src]
with open('evals/trigger-eval-clean.json','w') as f:
    json.dump(clean, f, indent=2, ensure_ascii=True); f.write('\n')
"
```

Both files were hand-maintained through v1.4.0 — two copies of the same 20 cases with nothing
detecting divergence. A case added to one and not the other would have silently changed what
the grader measured.

## What these test, and what they do NOT

**Tested:** activation only. Does the skill's `description` string fire on this phrasing?

**Not tested:** classification correctness (BUG / WATCH / OK / REVIEW), `OK (CANON)`
selection, recon-scout bucket choice, report shape, inferred-vs-described mode selection, or
any behavior gated on scale (the ≥6 already-swept exclusion, the ≥25 tighten offer, the
>500-file batched path).

That gap is deliberate for now — those need a fixture repo, not a query list — but it means a
green eval run says the skill *starts*, never that it is *right*.

## Coverage notes

- All five trigger phrases in the `description` string are covered verbatim: `run bug-echo`,
  `echo this fix`, `scan for similar bugs`, `find other instances`, `after-fix scan`. Three of
  those five were untested before v1.4.1.
- Nine of the ten negatives are labeled NEAR-MISS: they share surface vocabulary with a real
  invocation (a fixed bug, a code sweep, a file scan) but ask for something else. The strongest
  is the last case — it names a fixed bug *and* a sweep intent, but asks for a file deletion.
- Two cases probe a genuinely subtle boundary: a refactor with no bug (expected **true** — a
  shape was replaced) versus a forward-looking audit with no bug (expected **false** — nothing
  was fixed, that's bug-prospector's job).
