import XCTest

/// cut / delete / pasteOver are built-in kinds (no script, no keystroke): they must decode from the
/// config, be understood by this build, and always write back in place (`outputMode == .replace`),
/// whatever `output` the file says. Copy stays a plain clipboard action.
final class NativeEditKindsTests: XCTestCase {

    private func decode(_ kind: String, output: String? = nil) throws -> PopBarActionConfig {
        let out = output.map { ", \"output\": \"\($0)\"" } ?? ""
        let json = "{\"id\": \"a1\", \"title\": \"T\", \"iconSymbol\": \"x\", \"kind\": \"\(kind)\"\(out)}"
        return try JSONDecoder().decode(PopBarActionConfig.self, from: Data(json.utf8))
    }

    func testThreeKindsDecodeAndAreSupported() throws {
        for (raw, kind) in [("cut", PopBarActionConfig.Kind.cut), ("delete", .delete), ("pasteOver", .pasteOver)] {
            let a = try decode(raw)
            XCTAssertEqual(a.kind, kind)
            XCTAssertFalse(a.isUnsupported, raw)
        }
    }

    func testTheyAlwaysReplaceInPlace() throws {
        for raw in ["cut", "delete", "pasteOver"] {
            XCTAssertEqual(try decode(raw).outputMode, .replace, raw)
            XCTAssertEqual(try decode(raw, output: "panel").outputMode, .replace, raw)
        }
        XCTAssertEqual(try decode("copy").outputMode, .panel)
    }
}
