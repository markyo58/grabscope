import XCTest

final class MiddleClickPolicyTests: XCTestCase {
    func testSelectionOpensTheRing() {
        XCTAssertEqual(MiddleClickPolicy.route(selection: "word", enabled: true), .ring)
    }
    func testNoSelectionPassesTheClickOn() {
        for s in [nil, "", "  \n\t"] { XCTAssertEqual(MiddleClickPolicy.route(selection: s, enabled: true), .pass) }
    }
    func testSettingOffAlwaysPasses() {
        XCTAssertEqual(MiddleClickPolicy.route(selection: "word", enabled: false), .pass)
    }
}
