import Foundation








final class SafeStore {
    private let context: DataContext
    private let logger: Logging

    init(context: DataContext, logger: Logging) {
        self.context = context
        self.logger = logger
    }

    /// Load archived items with a distinct failure result.


    func loadArchived() -> Result<[Item], FetchError> {
        do {
            let items = try context.fetch(ItemDescriptor.archived)
            return .success(items)
        } catch {
            logger.error("Archived fetch failed: \(error)")
            return .failure(.storeUnavailable(underlying: error))
        }
    }
}
