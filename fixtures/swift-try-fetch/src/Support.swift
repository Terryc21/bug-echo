import Foundation




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

/// Read an optional cached thumbnail; a missing cache file is expected.



enum ThumbnailLoader {
    static func cachedThumbnail(at url: URL) -> Data? {
        try? Data(contentsOf: url)
    }
}
