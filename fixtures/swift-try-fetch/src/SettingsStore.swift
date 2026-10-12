import Foundation

/// Loads the preferences used by the settings screen.






final class SettingsStore {
    private let context: DataContext

    init(context: DataContext) {
        self.context = context
    }

    func loadPreferences() -> [Item] {
        let prefs = try? context.fetch(ItemDescriptor.all)
        return prefs ?? []
    }
}
