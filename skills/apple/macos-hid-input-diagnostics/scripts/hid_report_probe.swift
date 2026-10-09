// hid_report_probe.swift — RAW HID input-report probe for macOS.
// Reads report-level bytes (IOHIDDeviceRegisterInputReportCallback), i.e. below the value /
// event layer, and tracks device instances so a reconnected device cannot silently turn the
// probe deaf.
//
// Build:  swiftc -O hid_report_probe.swift -o hid_report_probe
// Run:    ./hid_report_probe                      # Logitech 0x046d/0xb027, 12s/20s/10s
//         ./hid_report_probe 0x046d 0xb027 20    # vid pid (hex), same seconds for each phase
//
// Phases, in order: BALL (spin/move only) -> CLICK (N slow clicks, no motion) ->
// WHEEL (as the LINK CONTROL: wheel deltas must arrive 1:1).
// READ THE DECODER ASSUMPTION: decodeReport2 assumes the standard Logitech mouse report on
// report ID 2 (16 button bits | X:12 | Y:12 | wheel:8 | pan:8). For any other device, first
// read its HID report descriptor (ioreg -w0 -l, the IOHIDUserDeviceReportDescriptor property)
// and adjust the offsets; the self-test only proves the decoder matches this layout.

import Foundation
import IOKit.hid

func hexArg(_ s: String) -> Int { Int(s.hasPrefix("0x") ? String(s.dropFirst(2)) : s, radix: 16) ?? 0 }
let argv = CommandLine.arguments
let VID = argv.count > 1 ? hexArg(argv[1]) : 0x046d
let PID = argv.count > 2 ? hexArg(argv[2]) : 0xb027
let all = argv.count > 3 ? (Int(argv[3]) ?? 0) : 0
let ballSecs  = all > 0 ? all : 12
let clickSecs = all > 0 ? all : 20
let wheelSecs = all > 0 ? all : 10

// ---------- decoder (report ID 2) ----------
func decodeReport2(_ b: [UInt8]) -> (btn: UInt16, x: Int, y: Int, wheel: Int, pan: Int) {
    func byte(_ i: Int) -> UInt8 { i < b.count ? b[i] : 0 }
    let btn = UInt16(byte(0)) | (UInt16(byte(1)) << 8)
    var x = Int(byte(2)) | (Int(byte(3) & 0x0F) << 8)
    var y = Int(byte(3) >> 4) | (Int(byte(4)) << 4)
    if x >= 0x800 { x -= 0x1000 }        // 12-bit two's complement
    if y >= 0x800 { y -= 0x1000 }
    return (btn, x, y, Int(Int8(bitPattern: byte(5))), Int(Int8(bitPattern: byte(6))))
}

func selftest() {
    let v1: [UInt8] = [0x01,0x00, 0x05, 0xD0, 0xFF, 0x01, 0x00]   // btn=1 x=+5 y=-3 wheel=+1 pan=0
    let v2: [UInt8] = [0x00,0x00, 0xFF, 0x1F, 0x00, 0x00, 0x00]   // x=-1 y=+1
    let d1 = decodeReport2(v1), d2 = decodeReport2(v2)
    let ok1 = (d1.btn == 1 && d1.x == 5 && d1.y == -3 && d1.wheel == 1 && d1.pan == 0)
    let ok2 = (d2.x == -1 && d2.y == 1)
    print("SELFTEST decodeReport2: v1=\(ok1 ? "OK" : "FAIL")  v2=\(ok2 ? "OK" : "FAIL")")
    if !(ok1 && ok2) { exit(2) }   // a probe with an unverified decoder must not be trusted
}
selftest()

// ---------- state ----------
final class Mon {
    let started = Date()
    var reports = 0, motion = 0, sumXY = 0, wheelSum = 0, bounces = 0
    var perInstance: [String: Int] = [:]
    var live: [IOHIDDevice] = []
    var timeline: [String] = []
    var presses: [String] = []
    var downCount = 0, lastDownT = -1.0
    var phaseT0 = Date()
    var currentInst = "?"
    var instSeq = 0
    func stamp() -> String { String(format: "%7.2fs", Date().timeIntervalSince(started)) }
    func addDevice(_ d: IOHIDDevice) {
        instSeq += 1
        var buf = [UInt8](repeating: 0, count: 256)
        IOHIDDeviceRegisterInputReportCallback(d, &buf, buf.count, reportCB,
            Unmanaged.passUnretained(self).toOpaque())
        let o = IOHIDDeviceOpen(d, IOOptionBits(kIOHIDOptionsTypeNone))
        currentInst = "inst#\(instSeq)"
        live.append(d)
        print("  \(stamp())  + instance \(currentInst) appeared   open=\(o)   [live=\(live.count)]")
    }
    func removeDevice(_ d: IOHIDDevice) {
        live.removeAll { $0 === d }
        print("  \(stamp())  - instance disappeared                    [live=\(live.count)]")
    }
    func phaseStart() {
        phaseT0 = Date(); reports = 0; motion = 0; sumXY = 0; wheelSum = 0
        presses = []; downCount = 0; lastDownT = -1
    }
    func handle(_ id: UInt32, _ bytes: [UInt8]) {
        reports += 1
        perInstance[currentInst, default: 0] += 1
        guard id == 2 else { return }
        let d = decodeReport2(bytes)
        if d.x != 0 || d.y != 0 { motion += 1; sumXY += abs(d.x) + abs(d.y) }
        wheelSum += d.wheel
        let now = Date().timeIntervalSince(phaseT0)
        let down = (d.btn & 0x0001) != 0
        if down && (lastDownT < 0 || now > lastDownT + 0.060) {
            downCount += 1; lastDownT = now
            presses.append(String(format: "   #%d press t=%.2fs inst=%@", downCount, now, currentInst))
        } else if down { bounces += 1 }      // re-press within 60 ms = contact bounce
    }
}
let M = Mon()

func reportCB(context: UnsafeMutableRawPointer?, result: IOReturn, sender: UnsafeMutableRawPointer?,
              type: IOHIDReportType, reportID: UInt32, report: UnsafeMutablePointer<UInt8>, reportLength: CFIndex) {
    guard let c = context else { return }
    Unmanaged<Mon>.fromOpaque(c).takeUnretainedValue()
        .handle(reportID, Array(UnsafeBufferPointer(start: report, count: reportLength)))
}
func matchCB(context: UnsafeMutableRawPointer?, result: IOReturn, sender: UnsafeMutableRawPointer?, device: IOHIDDevice) {
    guard let c = context else { return }
    Unmanaged<Mon>.fromOpaque(c).takeUnretainedValue().addDevice(device)
}
func removeCB(context: UnsafeMutableRawPointer?, result: IOReturn, sender: UnsafeMutableRawPointer?, device: IOHIDDevice) {
    guard let c = context else { return }
    Unmanaged<Mon>.fromOpaque(c).takeUnretainedValue().removeDevice(device)
}

let ctx = Unmanaged.passUnretained(M).toOpaque()
let mgr = IOHIDManagerCreate(kCFAllocatorDefault, IOOptionBits(kIOHIDOptionsTypeNone))
IOHIDManagerSetDeviceMatching(mgr, [kIOHIDVendorIDKey: VID, kIOHIDProductIDKey: PID] as CFDictionary)
IOHIDManagerRegisterDeviceMatchingCallback(mgr, matchCB, ctx)
IOHIDManagerRegisterDeviceRemovalCallback(mgr, removeCB, ctx)
let mo = IOHIDManagerOpen(mgr, IOOptionBits(kIOHIDOptionsTypeNone))
print("IOHIDManagerOpen = \(mo)   (0 = ok, -536870174 = Input Monitoring not granted)")
guard mo == 0, let set = IOHIDManagerCopyDevices(mgr) as? Set<IOHIDDevice> else { print("manager open failed"); exit(1) }
for d in set { M.addDevice(d) }

func run(_ title: String, _ secs: Int, _ prompt: String, watchClick: Bool) {
    print("\n=== PHASE: \(title) — \(secs)s ===")
    print("    \(prompt)")
    M.phaseStart()
    for i in 0..<secs {
        CFRunLoopRunInMode(.defaultMode, 1.0, false)
        print(watchClick
            ? "      t=\(i+1)s presses=\(M.downCount) reports=\(M.reports) inst=\(M.currentInst)"
            : "      t=\(i+1)s reports=\(M.reports) motion=\(M.motion) wheel=\(M.wheelSum) inst=\(M.currentInst)")
    }
    print("    result: reports=\(M.reports)  motion-bearing=\(M.motion)  sum|dx|+|dy|=\(M.sumXY)  wheel=\(M.wheelSum)  presses=\(M.downCount)  bounces=\(M.bounces)")
    if M.reports == 0 {
        print("    !! reports=0 — check the timeline above: if an instance disappeared during this")
        print("       phase, the probe was deaf and the window is VOID; otherwise the device was silent.")
    }
    if watchClick && !M.presses.isEmpty { print("  presses:\n" + M.presses.joined(separator: "\n")) }
}

run("BALL ONLY", ballSecs, ">>> move/spin the pointer input only; do not touch buttons, wheel, or the device body", watchClick: false)
run("CLICK x10", clickSecs, ">>> click the primary button exactly 10 times, ~1.5 s apart; no motion", watchClick: true)
run("WHEEL ONLY", wheelSecs, ">>> wheel up and down 10 notches each (link control); no motion, no clicks", watchClick: false)

print("\n=== device-instance timeline (link stability from the probe's view) ===")
print(M.timeline.isEmpty ? "   (no add/remove events: one instance throughout)" : M.timeline.joined(separator: "\n"))
print("\n=== reports per instance ===")
for (k, v) in M.perInstance.sorted(by: { $0.key < $1.key }) { print("   \(k): \(v)") }
print("""

=== how to read it ===
  ball motion-bearing=0 and no instance disappeared  => the device generated no motion reports
  ball reports=0 and an instance disappeared          => probe deaf, VOID, re-run
  clicks < 10 while wheel is 1:1                      => switch/contact fault, not the link
  clicks < 10 and wheel also short                    => link or power. New battery first, then
                                                         re-pair, then the vendor's USB receiver,
                                                         then a second host (device vs host split).
  bounces > 0                                         => dirty/worn switch contacts
""")
