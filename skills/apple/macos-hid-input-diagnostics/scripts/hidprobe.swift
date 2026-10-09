// hidprobe.swift — measure whether a HID device actually emits pointer/button reports to
// macOS, so that "the cursor does not move" can be attributed to the device or to the host
// stack instead of guessed at.
//
// Build:  swiftc -O hidprobe.swift -o hidprobe
// Run:    ./hidprobe [seconds] [vid] [pid]
//           ./hidprobe 20                  # defaults: 20 s, Logitech 0x046d:0xb027
//           ./hidprobe 20 0x05ac 0x0343    # example: Apple internal trackpad
//
// The process needs Input Monitoring permission (System Settings > Privacy & Security >
// Input Monitoring) or it receives nothing at all — zero events including button presses
// means permission, not a dead device.
//
// Output: per-2-s aggregate lines (raw motion arrives ~125 Hz, per-event printing buries the
// signal) and a final verdict. Tell the user "click once, then move/spin the input" before
// starting it.
import Foundation
import IOKit.hid

func hexArg(_ s: String, _ fallback: Int) -> Int {
    let body = s.lowercased().hasPrefix("0x") ? String(s.dropFirst(2)) : s
    return Int(body, radix: 16) ?? fallback
}

final class Stats {
    var btn = 0                 // usage page 9 (Button)
    var x = 0, y = 0            // usage page 1, usage 0x30 / 0x31
    var dxy = 0                 // sum |dX| + |dY|
    var wheel = 0               // usage page 1, usage 0x38
    var other = 0
    var buttonsSeen: Set<Int> = []
    var lastXY = "none"
}

let args = CommandLine.arguments
let seconds = args.count > 1 ? (Double(args[1]) ?? 20) : 20
let vid = args.count > 2 ? hexArg(args[2], 0x046d) : 0x046d
let pid = args.count > 3 ? hexArg(args[3], 0xb027) : 0xb027

let s = Stats()
let ctx = Unmanaged.passUnretained(s).toOpaque()

let mgr = IOHIDManagerCreate(kCFAllocatorDefault, IOOptionBits(kIOHIDOptionsTypeNone))
IOHIDManagerSetDeviceMatching(mgr, [kIOHIDVendorIDKey as String: vid,
                                   kIOHIDProductIDKey as String: pid] as CFDictionary)

let cb: IOHIDValueCallback = { context, _, _, value in
    guard let context = context else { return }
    let st = Unmanaged<Stats>.fromOpaque(context).takeUnretainedValue()
    let el = IOHIDValueGetElement(value)
    let up = IOHIDElementGetUsagePage(el)
    let u = IOHIDElementGetUsage(el)
    let v = IOHIDValueGetIntegerValue(value)
    if up == 9 {
        if v != 0 {
            st.btn += 1
            st.buttonsSeen.insert(Int(u))
            print("  [BUTTON] usage=\(u) pressed")
        }
    } else if up == 1 && (u == 0x30 || u == 0x31) {
        if u == 0x30 { st.x += 1 } else { st.y += 1 }
        st.dxy += abs(Int(v))
        st.lastXY = "dX=\(u == 0x30 ? Int(v) : 0) dY=\(u == 0x31 ? Int(v) : 0)"
    } else if up == 1 && u == 0x38 {
        st.wheel += 1
        print("  [WHEEL] \(v)")
    } else {
        st.other += 1
    }
}

IOHIDManagerRegisterInputValueCallback(mgr, cb, ctx)
IOHIDManagerScheduleWithRunLoop(mgr, CFRunLoopGetCurrent(), CFRunLoopMode.defaultMode.rawValue)
let openResult = IOHIDManagerOpen(mgr, IOOptionBits(kIOHIDOptionsTypeNone))
print("IOHIDManagerOpen = \(openResult)  (0 = ok, -536870174 = not permitted)")
print("matching VID 0x\(String(vid, radix: 16)) PID 0x\(String(pid, radix: 16))")

var count = 0
if let devs = IOHIDManagerCopyDevices(mgr) as? Set<IOHIDDevice> {
    count = devs.count
    for d in devs {
        let p = IOHIDDeviceGetProperty(d, kIOHIDProductKey as CFString) ?? "?" as CFString
        let t = IOHIDDeviceGetProperty(d, kIOHIDTransportKey as CFString) ?? "?" as CFString
        let n = IOHIDDeviceGetProperty(d, kIOHIDSerialNumberKey as CFString) ?? "?" as CFString
        print("device: \(p)  transport=\(t)  serial=\(n)")
    }
}
print("matched HID devices: \(count)")
print(">>> listening \(Int(seconds))s — click a button once, then move / spin the input.")

let start = Date()
let end = start.addingTimeInterval(seconds)
var lastPrint = start
while Date() < end {
    RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.05))
    if Date().timeIntervalSince(lastPrint) >= 2.0 {
        lastPrint = Date()
        print(String(format: "  t=%4.1fs buttons=%d%@ | X/Y reports=%d sum|dX|+|dY|=%d | wheel=%d | %@",
                     Date().timeIntervalSince(start), s.btn, s.buttonsSeen.sorted().description,
                     s.x + s.y, s.dxy, s.wheel, s.lastXY))
    }
}
print("---- RESULT ----")
print("button events: \(s.btn) (usages \(s.buttonsSeen.sorted()))")
print("X/Y motion reports: \(s.x + s.y)   sum|dX|+|dY| = \(s.dxy)")
print("wheel reports: \(s.wheel)   other elements: \(s.other)")
if s.btn == 0 && s.x + s.y == 0 && s.wheel == 0 {
    print("VERDICT: nothing received -> the device was not touched, or this process lacks Input")
    print("         Monitoring permission (then even buttons show nothing). Fix permission first.")
} else if s.x + s.y == 0 {
    print("VERDICT: button/wheel reports arrive but ZERO pointer motion -> the device-side sensor")
    print("         path is dead (ball seated wrong, debris on the lens/bearings, or dead sensor).")
} else {
    print("VERDICT: the device DOES send pointer deltas -> hardware is fine; the cursor is lost")
    print("         downstream (pointer parameters or a third-party mouse utility).")
}
