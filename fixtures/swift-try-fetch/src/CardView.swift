import Foundation




final class CardViewModel {
    private let context: DataContext

    var visibleCards: [Item] = []

    init(context: DataContext) {
        self.context = context
    }

    /// Refresh the cards displayed on screen.


    func refresh() {
        let cards = try? context.fetch(ItemDescriptor.visible)
        visibleCards = cards ?? []
    }
}
