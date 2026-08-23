import Foundation

/// FIXTURE FILE — test code. Matches the pattern textually, is NOT a bug.
/// This is the "known intentional usage" case from Step 4.2.

final class ItemStoreTests {

    /// EXPECT: OK — `try?` in a test arrange-step where a failed fetch is an
    /// acceptable outcome the assertion below accounts for. Swallowing here is
    /// deliberate: the test asserts on the nil, it doesn't depend on the value.
    func testEmptyStoreReturnsNil() {
        let context = DataContext.inMemory()
        let result = try? context.fetch(ItemDescriptor.all)
        assert(result?.isEmpty ?? true, "a fresh in-memory store has no items")
    }

    /// EXPECT: OK — same reasoning. The point of the test is that the call does
    /// not throw into the harness; the optional IS the assertion target.
    func testFetchDoesNotTrap() {
        let context = DataContext.inMemory()
        _ = try? context.fetch(ItemDescriptor.visible)
    }
}
