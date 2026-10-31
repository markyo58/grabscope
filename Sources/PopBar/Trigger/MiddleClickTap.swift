import AppKit
import ApplicationServices

/// Middle click with text selected opens the ring at the centre of the display under the pointer
/// (Mark 2026-10-31). A head-inserted CGEventTap decides in one native AX read, no process spawned:
/// selection → swallow down+up and open the ring; none → the event goes on untouched.
final class MiddleClickTap {
    private static let log = FileLog("PopBar.MiddleClick")
    /// Hard cap on the AX read: a stuck app must never hold the mouse.
    private static let axTimeout: Float = 0.03

    private var tap: CFMachPort?
    private var source: CFRunLoopSource?
    private var swallowing = false
    private var readMillis: [Double] = []
    /// Called on main with the display centre in Cocoa screen coordinates.
    var onRing: ((CGPoint) -> Void)?

    var isRunning: Bool { tap != nil }

    func start() {
        guard tap == nil else { return }
        let types: [CGEventType] = [.otherMouseDown, .otherMouseUp, .otherMouseDragged]
        let mask = types.reduce(CGEventMask(0)) { $0 | (CGEventMask(1) << $1.rawValue) }
        guard let port = CGEvent.tapCreate(
            tap: .cgSessionEventTap, place: .headInsertEventTap, options: .defaultTap, eventsOfInterest: mask,
            callback: { _, type, event, refcon in
                guard let refcon else { return Unmanaged.passUnretained(event) }
                let me = Unmanaged<MiddleClickTap>.fromOpaque(refcon).takeUnretainedValue()
                return me.handle(type: type, event: event)
            },
            userInfo: Unmanaged.passUnretained(self).toOpaque()) else {
            Self.log.warn("event tap not created — Input Monitoring may be needed")
            return
        }
        tap = port
        source = CFMachPortCreateRunLoopSource(nil, port, 0)
        CFRunLoopAddSource(CFRunLoopGetMain(), source, .commonModes)
        CGEvent.tapEnable(tap: port, enable: true)
        Self.log.info("middle-click tap on")
    }

    func stop() {
        if let source { CFRunLoopRemoveSource(CFRunLoopGetMain(), source, .commonModes) }
        if let tap { CFMachPortInvalidate(tap) }
        tap = nil; source = nil; swallowing = false
    }

    private func handle(type: CGEventType, event: CGEvent) -> Unmanaged<CGEvent>? {
        let pass = Unmanaged.passUnretained(event)
        if type == .tapDisabledByTimeout || type == .tapDisabledByUserInput {
            if let tap { CGEvent.tapEnable(tap: tap, enable: true) }
            return pass
        }
        guard event.getIntegerValueField(.mouseEventButtonNumber) == 2 else { return pass }
        switch type {
        case .otherMouseDown:
            let t0 = CFAbsoluteTimeGetCurrent()
            let selection = Self.selectedText()
            let ms = (CFAbsoluteTimeGetCurrent() - t0) * 1000
            readMillis.append(ms)
            let route = MiddleClickPolicy.route(selection: selection, enabled: PopBarPreferences.middleClickWhenSelected)
            let (n, med, mx) = (readMillis.count, median(readMillis), readMillis.max() ?? 0)
            let verdict = route == .ring ? "ring" : "pass"
            Self.log.debug(String(format: "middle down: AX read %.1f ms (n=%d, median %.1f, max %.1f) → %@", ms, n, med, mx, verdict))
            guard route == .ring else { return pass }
            swallowing = true
            let centre = Self.displayCentre(under: NSEvent.mouseLocation)
            DispatchQueue.main.async { [weak self] in self?.onRing?(centre) }
            return nil
        case .otherMouseUp, .otherMouseDragged:
            if swallowing {
                if type == .otherMouseUp { swallowing = false }
                return nil
            }
            return pass
        default:
            return pass
        }
    }

    private func median(_ xs: [Double]) -> Double {
        let s = xs.sorted(); return s.isEmpty ? 0 : s[s.count / 2]
    }

    /// The focused element's selected text, read natively with a hard time cap. nil = none or unreadable.
    private static func selectedText() -> String? {
        guard let element = AXSelectionProbe.focusedElement() else { return nil }
        AXUIElementSetMessagingTimeout(element, axTimeout)
        var value: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, kAXSelectedTextAttribute as CFString, &value) == .success else { return nil }
        return value as? String
    }

    private static func displayCentre(under point: CGPoint) -> CGPoint {
        let screen = NSScreen.screens.first { $0.frame.contains(point) } ?? NSScreen.main
        let f = screen?.frame ?? .zero
        return CGPoint(x: f.midX, y: f.midY)
    }
}
