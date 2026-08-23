import Foundation

/// FIXTURE FILE — deliberate BUG at line 21, same shape as ItemStore.loadAll().
/// This is the sibling instance bug-echo is supposed to find.

final class CardViewModel {
    private let context: DataContext

    var visibleCards: [Item] = []

    init(context: DataContext) {
        self.context = context
    }

    /// EXPECT: BUG — identical shape to the seeded fix. A failed fetch silently
    /// renders an empty card list, and the user is never told the load failed.
    /// This is the copy that survived when the original was fixed.
    func refresh() {
        let cards = try? context.fetch(ItemDescriptor.visible)
        visibleCards = cards ?? []
    }
}
