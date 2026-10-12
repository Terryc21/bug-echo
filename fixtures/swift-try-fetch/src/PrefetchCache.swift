import Foundation









final class PrefetchCache {
    private let context: DataContext
    private var warmed: [Item] = []

    init(context: DataContext) {
        self.context = context
    }

    /// Best-effort cache warm; callers always perform the authoritative
    /// ItemStore.loadAll() independently. A failed warm-up costs latency;
    /// these cached values must not determine whether the store is empty.


    func warm() {
        warmed = (try? context.fetch(ItemDescriptor.recent)) ?? []
    }

    func warmedCount() -> Int { warmed.count }
}
