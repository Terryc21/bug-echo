import Foundation




struct Item {
    let id: String
    let title: String
}

final class ItemStore {
    private let context: DataContext

    init(context: DataContext) {
        self.context = context
    }

    /// Load all items; callers present an empty result as "no items".


    func loadAll() -> [Item] {
        let items = try? context.fetch(ItemDescriptor.all)
        return items ?? []
    }

    func count() -> Int {
        loadAll().count
    }
}
