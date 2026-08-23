# bug-echo Report: success reported without checking whether anything happened (CANON example)

> [!IMPORTANT]
> **Written against v1.4.2. Report shape and step numbers current as of that release.**

> [!NOTE]
> This is a **real run** (Stuffolio, 2026-08-23, inferred-from-diff mode) trimmed to
> illustrate one v1.4.0 feature: `OK (CANON)`. The full sweep produced eight findings across
> two shapes; only the family that demonstrates CANON is reproduced here. Findings are real,
> file:line citations are real, and the reference implementation quoted below is production
> code that predates the feature.

**Date:** 2026-08-23
**Pattern source:** inferred from diff (`ed50eaad`)
**Scan tool:** Grep over `Sources/**/*.swift`
**Recon scout:** 8 candidates (bucket: 6+ full)
**Pattern validated:** yes — matched the pre-fix file at `WarrantyFormView+Helpers.swift`

---

## Why this example exists

Most bug-echo runs classify every non-buggy match as plain `OK` and move on. Sometimes one of
those OK sites is more than "not a bug": it is **the shape the BUG findings should be made to
look like**. The codebase already solved the problem, in one place, and the other copies never
got updated.

When that happens, the most useful fact the sweep produces is not the list of bugs — it is
*the answer is already here, at this line*. v1.4.0 added `OK (CANON)` so a report can say so.

🛑 **Most sweeps have no CANON site and that is normal.** A young repo, a first sweep against
a uniformly-broken pattern, or a genuinely novel bug has no correct instance to point at. See
"When there is no CANON site" at the bottom.

---

## Pattern

**Anti-pattern:** a success signal (toast, haptic, status latch) fires based on whether
*input was available*, not on whether the operation *actually did anything*. A series of
conditional writes — each `if let x = ..., !x.isEmpty` — can collectively write nothing, and
the success message fires regardless.

**Correct pattern:** count what actually landed; report against the count.

**Search scope:** `Sources/**/*.swift`

---

## Summary

- BUG findings: 5
- WATCH findings: 0
- OK findings: 2 — **both CANON**
- REVIEW findings: 0

**Reference implementation:** `Sources/Features/ItemManagement/Views/AddItemSheetWrapper+OCR.swift:305` — this codebase already solves this pattern here. The findings below should converge on it rather than each inventing a fix.

---

## OK (CANON) — the reference implementation

`Sources/Features/ItemManagement/Views/AddItemSheetWrapper+OCR.swift:305`

```swift
private func announceFieldsApplied(_ fields: [String]) {
    guard !fields.isEmpty else {
        ToastManager.shared.info("Nothing new to fill from this scan")
        return
    }
    let list = fields.joined(separator: ", ")
    ToastManager.shared.success("Filled: \(list)")
}
```

**Why CANON, not just OK:** the caller accumulates an `applied: [String]` array as it writes
each field, then routes through this function. The empty case is not merely *not-a-false-
success* — it produces a distinct, honest message naming what happened. Every BUG finding
below is the same function shape missing exactly this accumulator.

A second CANON site, same shape: `Sources/ViewModels/AddItemViewModel.swift:225`
(`applyAIAnalysisResult`) uses a `fieldsApplied` counter and carries a comment describing this
exact defect class. Two correct copies, five drifted ones.

---

## BUG Findings — Issue Rating Table

| # | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | `applyReceiptResult` fires `HapticManager.success()` + "Receipt data applied" unconditionally after conditional writes; an all-nil OCR result reports success having written nothing | 🟡 HIGH | ⚪ Low | 🟡 High | 🟠 Excellent | ⚪ 1 file | Small | Open |
| 2 | `applyLabelResult` — same shape; three `if let ..., !x.isEmpty` writes, unconditional "Label data applied" | 🟡 HIGH | ⚪ Low | 🟡 High | 🟠 Excellent | ⚪ 1 file | Small | Open |
| 3 | `applyVoiceResult` — seven writes, each additionally gated on the target field being empty, so a voice result repeating already-filled fields writes nothing and still claims success | 🟡 HIGH | ⚪ Low | 🟡 High | 🟠 Excellent | ⚪ 1 file | Small | Open |
| 4 | `EditItemViewModel.applyVoiceResult` — third copy of the same function, same unconditional toast | 🟡 HIGH | ⚪ Low | 🟡 High | 🟠 Excellent | ⚪ 1 file | Small | Open |
| 5 | `AddItemSheetWrapper+Voice.applyVoiceResult` — fourth copy; haptic-only (no toast), so lower severity but identical shape | 🟢 MEDIUM | ⚪ Low | 🟢 Medium | 🟢 Good | ⚪ 1 file | Small | Open |

---

## Detailed findings

**1. `applyReceiptResult` reports success after writing nothing**

`Sources/ViewModels/AddItemViewModel.swift:131`

```swift
    formViewModel.core.purchasePrice = cleanPrice
}

HapticManager.shared.success()
ToastManager.shared.success("Receipt data applied")
```

**Why this is a bug:** every write above sits inside `if let store = ..., !store.isEmpty` /
`if let dateString = ...` (which additionally needs `parseDate` to succeed) / `if let priceStr
= ...`. An `OCRReceiptResult` with all-nil fields, or a `purchaseDate` string the parser
rejects, writes nothing — and still fires both the haptic and the toast.

**Suggested fix:** mirror `AddItemSheetWrapper+OCR.swift:305`. Accumulate the names of fields
actually written into an `applied: [String]`, then route through an `announceFieldsApplied`-
shaped function so the empty case produces "Nothing new to fill from this scan" instead of a
false success. **Do not design a new approach here** — the reference already settles the
wording and the shape.

*(Findings 2-5 identical in structure; each cites the same reference.)*

---

## What CANON changed about this report

Without the CANON label, the two correct sites would have been listed as bare `OK` — "correct
usage, no action needed" — and the five BUG findings would each have carried an independently
invented "Suggested fix." That is how the codebase reached five drifted copies of something
two siblings already got right.

With it:

- **Confidence rises to `verified`.** The remedy is not proposed, it is already running in
  production two files away.
- **Risk-of-Fixing and Fix Effort drop.** The fix is a copy, not a design. There is no product
  judgment left — even the toast wording is settled.
- **The five fixes converge.** Each cites the same line, so they land as one shape rather than
  five near-misses.

---

## When there is no CANON site

If no OK match is unmistakably the same shape solving the same problem, tag nothing. The
report renders exactly as it did before v1.4.0: `Suggested fix` is written from scratch, and
no "Reference implementation" line appears.

🛑 **Never invent a CANON site to satisfy the rule.** Pointing five findings at an "answer"
that is not actually the answer is worse than pointing them at nothing — they will all
converge on the wrong shape, and the report's authority makes that harder to unwind than five
independent guesses.

---

## Provenance note

The `2026-05-03-bug-echo-deep-viewbuilder-crash.md` report in this directory was already doing
this by hand, months before v1.4.0 existed. Its cross-cutting observations say:

> "The three-group split in `EnhancedItemDetailView+Sections.swift` at lines 928-1022 is the
> canonical fix in this codebase. Any future fix should reference that pattern explicitly so
> future maintainers see the precedent."

That is a CANON finding written in prose because the report had no field for it. v1.4.0
ratified existing practice rather than inventing a capability.
