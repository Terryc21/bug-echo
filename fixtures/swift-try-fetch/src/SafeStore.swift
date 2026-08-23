import Foundation

/// FIXTURE FILE — this is the CANON site.
///
/// Same fetch, same failure mode, already handled correctly. It is not merely
/// "not a bug": it is the shape the BUG findings in ItemStore.swift and
/// CardView.swift should be made to look like. A sweep that classifies this as
/// a bare OK has discarded the most useful thing it found.

final class SafeStore {
    private let context: DataContext
    private let logger: Logging

    init(context: DataContext, logger: Logging) {
        self.context = context
        self.logger = logger
    }

    /// EXPECT: CANON — the fetch error is caught, logged, and distinguished
    /// from an empty result. The caller can tell "load failed" apart from
    /// "nothing stored", which is exactly what the `try?` sites cannot do.
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
