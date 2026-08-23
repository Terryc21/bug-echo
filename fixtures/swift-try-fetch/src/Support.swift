import Foundation

/// FIXTURE FILE — supporting types so the fixture reads as a coherent project.
/// Nothing here is a scan target.

enum FetchError: Error {
    case storeUnavailable(underlying: Error)
}

protocol Logging {
    func error(_ message: String)
}

struct ItemDescriptor {
    let name: String
    static let all = ItemDescriptor(name: "all")
    static let visible = ItemDescriptor(name: "visible")
    static let archived = ItemDescriptor(name: "archived")
    static let recent = ItemDescriptor(name: "recent")
}

struct DataContext {
    static func inMemory() -> DataContext { DataContext() }

    func fetch(_ descriptor: ItemDescriptor) throws -> [Item] {
        []
    }
}

/// EXPECT: OK — `try?` on a DIFFERENT operation (file read, not a store
/// fetch). Present so an over-broad pattern (bare `try?` rather than
/// `try? ...fetch`) is visibly wrong: a scan that flags this line has
/// generalized past the seeded fix.
enum ThumbnailLoader {
    static func cachedThumbnail(at url: URL) -> Data? {
        try? Data(contentsOf: url)
    }
}
