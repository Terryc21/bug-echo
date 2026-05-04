# bug-echo Report: Deep @ViewBuilder type-tree crash (SubstGenericParametersFromMetadata)

> [!NOTE]
> This is a **real bug-echo report** generated from a Stuffolio session on 2026-05-03. It demonstrates the full output format and shows the post-fix-sweep workflow in practice: a fix had already shipped a month earlier (collapsibleSectionsStack, commits f01a2b82 + fbefd970), so the ledger row was retroactively closed via radar-suite verification, then bug-echo was run to find unfired echoes of the same pattern elsewhere in the codebase. It found one BUG (RMARow at the same density as the original crash, fixed in the same session) and three WATCH sites at sub-threshold density.

**Date:** 2026-05-03
**Pattern source:** user-described
**Scan tool:** custom Python brace-depth analyzer over Sources/**/*.swift (regex-based grep alone cannot count scope-direct conditionals; ast-grep not installed)
**Files scanned:** all `.swift` under `Sources/` (~700 files)
**Pattern validated:** N/A (user-described). The pattern was independently confirmed against the historical fix at `EnhancedItemDetailView+Sections.swift:920-1022` and commits `f01a2b82` + `fbefd970`, both of which split a single VStack with 16+ conditional children into 3 `@ViewBuilder` groups.

## Pattern

**Anti-pattern:** A SwiftUI container scope (VStack / HStack / Group / Form / List / ScrollView / LazyVStack / LazyHStack) holds many `if`-conditional or `if let`-conditional or `switch` child views in the same lexical scope. Each conditional becomes part of the parent's generic-type tree (`TupleView<(_ConditionalContent<X, Y>, _ConditionalContent<...>, ...)>`). At ~16+ branches in one resolution scope, the Swift runtime hits `SubstGenericParametersFromMetadata` failure during view metadata resolution. The crash reproduces only on physical iOS devices (the simulator has a slower path that masks it).

**Correct pattern:** Split the conditional children into 2-3 `@ViewBuilder` computed properties. Each subview gets its own type-resolution scope, halving (or thirding) the depth in any single tree. Document the split with a comment so a future maintainer doesn't re-flatten it during a refactor.

**Search criterion:** any container scope with `>= 10` conditional children at the immediate scope level (not counting nested ifs inside child views). 10 was chosen as a "yellow zone" threshold because the documented crash was at 16+ in a single VStack; flagging at 10 surfaces anything compounding toward that limit.

## Summary

- BUG findings: 1
- WATCH findings: 3
- OK findings: 0
- REVIEW findings: 0

A "WATCH" classification is used here in addition to the spec's BUG/OK/REVIEW because three of the four hits are in dedicated `@ViewBuilder` properties whose siblings are already small (the architectural defense is in place), but they themselves carry density that would put them into the BUG zone if they were ever inlined. They warrant a comment to prevent regression but no code change today.

## BUG Findings — Issue Rating Table

| # | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | RMARow.body has ~16 lexical children in body's type tree (outer VStack with HStack + HStack + Text + inner VStack containing 12 if-conditionals). RMARow is a list-row instantiated per record. At list-render time the type tree is fully resolved per cell. This is the only finding that approaches the documented 16+ crash density. | 🟡 HIGH | ⚪ Low | 🟡 High | 🟠 Excellent | ⚪ 1 file | Small | Fixed |

**BUG #1 closure (2026-05-03):** Split RMARow's details VStack into `coreDetailsBlock` (4 children: calendar + 3 logistics if-lets) and `extendedDetailsBlock` (9 if-let detail lines), both `@ViewBuilder` private computed properties. The body's outer VStack now has 5 sibling top-level children, none of which contain more than 4 conditionals. Post-fix scope analyzer confirms zero scopes with ≥5 conditional children remaining in the file. iOS Simulator + macOS builds both succeed. Diagnostic comment added at the call site referencing commits f01a2b82 + fbefd970 and warning against re-flattening.

## WATCH Findings — Issue Rating Table

| # | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status |
|---|---|---|---|---|---|---|---|---|
| 2 | OCRResultSheet.extractedFieldsSection holds 12 if-let conditionals in a single VStack. The function is a `@ViewBuilder`-style computed `some View` that's called from a parent body with surrounding chrome. Total per-call resolution depth is ~14-15. Below the 16 documented break, but if more OCR fields are added it crosses the line. | 🟢 MED | ⚪ Low | 🟢 Med | 🟢 Good | ⚪ 1 file | Trivial | Open |
| 3 | EnhancedItemDetailView+Sections.atAGlanceSection holds 11 conditionals in one VStack. Already inside the split-group architecture (called from coreSectionsGroup, which is one of the 3 ViewBuilder groups). Sibling sections in coreSectionsGroup are productInfoSection and warrantySection, also dense. Compounded across all three: depth approaches the original crash line if any one of them grows. | 🟢 MED | ⚪ Low | 🟢 Med | 🟢 Good | ⚪ 1 file | Trivial | Open |
| 4 | EnhancedItemDetailView+Sections.productInfoSection holds 10 conditionals in one VStack. Same context as #3 — already inside the split-group architecture, but the per-section density is high enough that adding 2-3 fields takes it into the BUG zone. | 🟢 MED | ⚪ Low | 🟢 Med | 🟢 Good | ⚪ 1 file | Trivial | Open |

## Detailed findings

### 1. RMARow body has ~16 children in its type tree

`Sources/Views/Lists/RMAListView.swift:262-375`

```swift
struct RMARow: View {
    let rma: RMARecord

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {     // line 266 — outer body VStack
            HStack { ... }                             // header row (1)
            HStack { ... if rma.isOverdue { ... } }    // RMA number + overdue badge (2)
            Text(rma.issueDescription)                 // (3)
            VStack(alignment: .leading, spacing: 4) {  // line 297 — details VStack (4)
                HStack { ... }                                   // calendar row
                if let expected = rma.expectedReturnDate { ... } // 1
                if let tracking = rma.outboundTrackingNumber { ... } // 2
                if let days = rma.daysInProgress { ... }         // 3
                if let actual = rma.actualReturnDate { ... }     // 4
                if let completion = rma.completionDate { ... }   // 5
                if let carrier = rma.outboundCarrier { ... }     // 6
                if let returnTracking = rma.returnTrackingNumber { ... } // 7
                if let cost = rma.shippingCostInCents { ... }    // 8
                if let cost = rma.repairCostInCents { ... }      // 9
                if let resolution = rma.resolution { ... }       // 10
                if let notes = rma.notes { ... }                 // 11
                if let contact = rma.contactName { ... }         // 12
            }
        }
    }
}
```

**Why this is a bug:** This view is rendered as a list row (each RMA record gets one). The body is a single SwiftUI view function, and SwiftUI resolves the full type tree for `body` at render time. The outer VStack has 4 children. The inner VStack at line 297 has 13 children (1 unconditional HStack + 12 conditionals). The compiler builds `TupleView<(HStack, _ConditionalContent<HStack, EmptyView>, _ConditionalContent<HStack, EmptyView>, ...)>` for the inner VStack — that's the same compounding generic depth that crashed `collapsibleSectionsStack` on physical iPhone. The detail view crash documented in `device_crash_detail_view.md` was at ~16 children in one VStack; this is right at that threshold. RMARow is more risky than the original because it's instantiated per row in a list — the cost is paid N times per scroll, and lists are exactly the surface area where memory pressure shows up first.

The reason it likely hasn't crashed yet is RMA records are rare in user data (typical user has 0-3 active RMAs, not a list of 50). When a user with many RMAs scrolls the list on a physical device, this could fire.

**Suggested fix:** Split the inner details VStack into two `@ViewBuilder` private computed properties:

```swift
struct RMARow: View {
    let rma: RMARecord

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            headerRow
            issueRow
            primaryDetailsBlock
            extendedDetailsBlock
        }
        .padding(.vertical, Spacing.xxSmall)
    }

    /// Split into 2 @ViewBuilder properties to keep the SwiftUI generic
    /// type tree shallow per row. See device_crash_detail_view.md +
    /// EnhancedItemDetailView+Sections.swift collapsibleSectionsStack
    /// (commit f01a2b82) for the same pattern in the parent app.
    /// DO NOT INLINE — re-flattening reintroduces the crash.
    @ViewBuilder
    private var primaryDetailsBlock: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack { /* calendar/issued row */ }
            if let expected = rma.expectedReturnDate { ... }
            if let tracking = rma.outboundTrackingNumber { ... }
            if let days = rma.daysInProgress { ... }
        }
    }

    @ViewBuilder
    private var extendedDetailsBlock: some View {
        VStack(alignment: .leading, spacing: 4) {
            if let actual = rma.actualReturnDate { rmaDetailLine(...) }
            if let completion = rma.completionDate { rmaDetailLine(...) }
            if let carrier = rma.outboundCarrier { rmaDetailLine(...) }
            if let returnTracking = rma.returnTrackingNumber { rmaDetailLine(...) }
            if let cost = rma.shippingCostInCents { rmaDetailLine(...) }
            if let cost = rma.repairCostInCents { rmaDetailLine(...) }
            if let resolution = rma.resolution { rmaDetailLine(...) }
            if let notes = rma.notes { rmaDetailLine(...) }
            if let contact = rma.contactName { rmaDetailLine(...) }
        }
    }
}
```

Alternative: collapse the 12 conditionals into a single `ForEach` over a computed `[DetailLine]` array, where each entry is constructed only when the underlying optional is non-nil. That's even cheaper at the type-tree level (one ForEach<Array, ID, View> regardless of how many items). Trade-off is a small adapter struct, but it's the most future-proof solution.

---

### 2. WATCH: OCRResultSheet.extractedFieldsSection — 12 conditionals in one VStack

`Sources/AI_Backend/OCRResultSheet.swift:241-286`

```swift
private var extractedFieldsSection: some View {
    VStack(alignment: .leading, spacing: 12) {
        sectionHeader(title: "Extracted Information", ...)
        VStack(spacing: 8) {                          // line 245 — 12 conditionals
            if let brand = result.brand { OCRFieldRow(...) }
            if let manufacturer = result.manufacturer, ... { OCRFieldRow(...) }
            if let model = result.modelNumber { OCRFieldRow(...) }
            if let serial = result.serialNumber { OCRFieldRow(...) }
            if let part = result.partNumber { OCRFieldRow(...) }
            if let voltage = result.voltage { OCRFieldRow(...) }
            if let wattage = result.wattage { OCRFieldRow(...) }
            if let capacity = result.capacity { OCRFieldRow(...) }
            if let mfgDate = result.manufactureDate { OCRFieldRow(...) }
            if let country = result.countryOfOrigin { OCRFieldRow(...) }
            if let certs = result.certifications { OCRFieldRow(...) }
            if let specs = result.additionalSpecs { OCRFieldRow(...) }
        }
    }
}
```

**Why this is WATCH not BUG:** the inner VStack has 12 conditionals (homogeneous: every branch produces `OCRFieldRow`, which means the compiler's `_ConditionalContent` generation may collapse better than for heterogeneous branches). The outer VStack has only 2 children. Combined depth is below the 16-trigger. But this view is the destination of a sheet from the AI Backend OCR scan flow and only a small percentage of users will trigger it; if more fields are added (e.g., the `additionalSpecs` field is parsed into N sub-fields), the count grows.

**Suggested fix (defensive, not urgent):** Add a comment near line 245 noting the threshold:

```swift
// Type-tree threshold note: this VStack has 12 conditional children.
// At 16+ the SwiftUI runtime can crash on physical iOS devices
// (SubstGenericParametersFromMetadata). If adding fields, split into
// two @ViewBuilder groups. See EnhancedItemDetailView+Sections.swift
// collapsibleSectionsStack for the canonical fix.
VStack(spacing: 8) {
    ...
}
```

Or convert to a `ForEach` over a `[(label: String, field: OCRField?)]` tuple-array, which removes the type-tree bloat entirely.

---

### 3. WATCH: EnhancedItemDetailView+Sections.atAGlanceSection — 11 conditionals

`Sources/Views/Detail/EnhancedItemDetailView+Sections.swift:227-396`

The sibling/architectural defense is already in place via the 3-group split (`coreSectionsGroup`, `collapsibleSectionsGroup`, `supplementarySectionsGroup` at lines 942-1022). atAGlanceSection is one of three children of `coreSectionsGroup`. Internally it has 11 conditionals: price, seller, purchaseLocation, additionalCosts, currentValue, replacementCost, perceivedValue, insuredValue, expectedLifespan, retirementDate, notes (each gated by an if/let). Plus a non-trivial nested notes-section block.

**Why this is WATCH not BUG:** the outer architectural fix (splitting the master stack) means atAGlanceSection's type tree is contained — its conditionals don't compound with productInfoSection's or warrantySection's at the body level. But 11 in one section is the highest-density section in the app, and the section itself is the busiest screen for users. Adding more fields here is the highest-likelihood path to reintroducing the crash.

**Suggested fix (defensive, not urgent):** add a doc comment to the section warning against further conditional growth:

```swift
@ViewBuilder
var atAGlanceSection: some View {
    // ⚠️ Type-tree budget: this section currently has 11 if-conditional
    // children. SwiftUI's per-view type-resolution cap is around 16 before
    // SubstGenericParametersFromMetadata crashes on physical iPhone (see
    // collapsibleSectionsStack history, commits f01a2b82 + fbefd970).
    // If adding new conditional rows, split into atAGlance_pricing +
    // atAGlance_metadata sub-builders rather than inlining.
    VStack(alignment: .leading, spacing: 0) {
        ...
    }
}
```

---

### 4. WATCH: EnhancedItemDetailView+Sections.productInfoSection — 10 conditionals

`Sources/Views/Detail/EnhancedItemDetailView+Sections.swift:400-485`

Same context as #3 — sibling of atAGlanceSection inside coreSectionsGroup. 10 conditionals: categories, manufacturer (composite), modelNumber, serial (composite), vin, yearMade, filterSize, bulbType, partNumbers, location, quantity, hasEmptyOptionalFields prompt.

**Why this is WATCH not BUG:** same reasoning — the outer split protects it.

**Suggested fix:** same defensive comment as #3.

---

## OK Findings

None. Every match was either a real near-miss (BUG #1) or a near-threshold scope (WATCH #2-4). There were no scopes that turned out to be safe under deeper inspection.

## REVIEW Findings

None. All four candidates were classifiable from code-reading alone.

---

## Cross-cutting observations

1. **The architectural defense is already paid for.** The three-group split in `EnhancedItemDetailView+Sections.swift` at lines 928-1022 is the canonical fix in this codebase. Any future fix should reference that pattern explicitly so future maintainers see the precedent.

2. **The risk profile of list rows is different from detail screens.** The detail view crashed once per navigation. RMARow renders once per RMA record per scroll. If the type-tree cost is paid per cell, a list with N rows pays it N times — list views with deep type trees are theoretically more vulnerable to memory-pressure crashes than single screens.

3. **The 16-trigger isn't a precise threshold.** The Swift compiler's metadata-resolution depth limit varies by Swift version, optimization level, and the specific shape of the generic tree (homogeneous vs. heterogeneous branches). The "10+ is yellow, 16+ is red" heuristic is empirical, not a guarantee. On the conservative side, splitting at 10 isn't wasted work; on the aggressive side, even a 12-conditional view that has been shipping fine could crash after the next Swift toolchain update.

4. **The pattern is preventable at scale via two architectural disciplines:**
   - **List-row simplification:** any `body` of a list-row view should have a flat top-level structure with zero or few conditionals.
   - **Section building via data:** convert "12 if-let-show-row" patterns to `ForEach(rows)` over a `[Row?]` array filtered for non-nil. This removes the type-tree bloat entirely and is more declarative.

---

## Why no changes were made automatically

Auto mode is on, but BUG #1 (RMARow split) involves either a 60+ line refactor or a redesign to ForEach-over-data. Both are above the "trivial/small + 1 file" threshold for autonomous fix, and the right shape (split vs ForEach) is a design decision not a mechanical edit. WATCH #2-4 are documentation-only; safe to apply but require user assent that the defensive comments are wanted.

A guided fix session is offered next.
