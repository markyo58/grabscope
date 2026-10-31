import Foundation

/// What a middle click does while GrabScope is running. Pure, so it is tested without a mouse.
/// Selected text (as the focused element reports it) + the setting on → open the ring and swallow the
/// click. Anything else → let the click through untouched (the radial menu of other apps keeps working).
enum MiddleClickPolicy {
    enum Route: Equatable { case ring, pass }

    static func route(selection: String?, enabled: Bool) -> Route {
        guard enabled, let selection,
              !selection.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return .pass }
        return .ring
    }
}
