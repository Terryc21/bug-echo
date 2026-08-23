import Foundation

/// FIXTURE FILE — not shipped, not compiled by any product target.
/// Contains a deliberate BUG at line 20 (see fixtures/swift-try-fetch/answer-key.json).

struct Item {
    let id: String
    let title: String
}

final class ItemStore {
    private let context: DataContext

    init(context: DataContext) {
        self.context = context
    }

    /// EXPECT: BUG — `try?` discards the fetch error, so a failed load is
    /// indistinguishable from an empty store. The caller renders "no items"
    /// on what may have been a decode failure or a corrupt store.
    func loadAll() -> [Item] {
        let items = try? context.fetch(ItemDescriptor.all)
        return items ?? []
    }

    func count() -> Int {
        loadAll().count
    }
}
