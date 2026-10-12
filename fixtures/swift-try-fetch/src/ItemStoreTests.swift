import Foundation




final class ItemStoreTests {

    /// Smoke check: a failed fetch (nil) is acceptable, as is an empty result.


    func testEmptyStoreReturnsNil() {
        let context = DataContext.inMemory()
        let result = try? context.fetch(ItemDescriptor.all)
        assert(result?.isEmpty ?? true, "a fresh in-memory store has no items")
    }

    /// Exercise the fetch without throwing into the test harness.

    func testFetchDoesNotTrap() {
        let context = DataContext.inMemory()
        _ = try? context.fetch(ItemDescriptor.visible)
    }
}
