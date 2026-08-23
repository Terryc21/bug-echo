import Foundation

/// FIXTURE FILE — the deliberate GRAY-ZONE case.
///
/// This site is why the harness is lenient on WATCH. A defensible reviewer
/// could call it BUG (the error is still discarded) or WATCH (there is an
/// architectural defense: the result is a non-authoritative cache warm, and a
/// real fetch happens later on the same data). Either verdict passes.
/// BUG↔OK on this site would still fail — it is not a clean OK.

final class PrefetchCache {
    private let context: DataContext
    private var warmed: [Item] = []

    init(context: DataContext) {
        self.context = context
    }

    /// EXPECT: WATCH (BUG also accepted — see the file header).
    /// Best-effort cache warm. A failure here costs a slower first render, not
    /// a wrong one: `ItemStore.loadAll()` is still the authoritative read and
    /// runs regardless. The pattern is the same shape as the BUG sites, but the
    /// consequence of swallowing is bounded — which is the WATCH definition.
    func warm() {
        warmed = (try? context.fetch(ItemDescriptor.recent)) ?? []
    }

    func warmedCount() -> Int { warmed.count }
}
