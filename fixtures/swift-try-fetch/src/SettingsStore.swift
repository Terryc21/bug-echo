import Foundation

/// FIXTURE FILE — THE SEED.
///
/// This file is committed in its BUGGY state, then fixed in a second commit.
/// That second commit is the diff bug-echo infers the pattern from
/// (Step 2B: `git log -p -1`). Do not classify this site — the harness
/// excludes it, because the fix is already applied at HEAD.

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
