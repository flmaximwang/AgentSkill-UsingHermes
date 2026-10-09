---
name: macos-hid-input-diagnostics
description: Use when a macOS input device misbehaves.
version: 1.1.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [macos, hid, iokit, hardware, troubleshooting, logitech]
    related_skills: [macos-package-management, macos-computer-use]
---

# macOS HID input diagnostics

## When to Use

- A pointer or keyboard only partly works ("buttons work but the cursor does not move").
- A wireless mouse/keyboard/trackball is connected with battery but unresponsive.
- You are about to blame a vendor daemon (Logi Options+, Karabiner, BetterTouchTool) for
  "hijacking" input.
- You need to know whether a device or the host stack is at fault, with evidence rather than
  plausibility.

## Core rule: a working button proves the whole software stack

macOS moves a pointer through this chain, and one HID report traverses all of it:

```
physical device --BLE--> /usr/sbin/BTLEServer --> IOHIDUserDevice --> AppleUserHIDEventDriver
        (dext) --> IOHIDSystem / WindowServer --> cursor
```

A button press that reaches WindowServer therefore proves the connection, the host stack,
and the vendor software are all alive. Consequences:

- **Some functions work, one does not** => the fault is upstream of the report: ball/optical
  sensor, encoder wheel, switch, or the device's own firmware. Do NOT open with driver
  reinstalls or permission resets; they cannot produce this shape of failure.
- **Nothing at all works** => connection, pairing, or a TCC permission is the place to look.

## Procedure

1. **Health checklist, read-only.** Run and decode against
   `references/macos-hid-input-path.md`:
   - `system_profiler SPBluetoothDataType` — connected? battery? firmware? Minor Type?
   - `hidutil list | grep -i <vendor>` — enumerated? which UsagePage/Usage, which driver class?
   - `ioreg -c IOHIDSystem -w0 | grep -i HIDParam` — `HIDPointerAcceleration`,
     `HIDMouseAcceleration`, `MouseButtonMode`
   - `defaults read -g com.apple.mouse.scaling`
2. **Attribute every HID device to the process that published it**, before naming a culprit.
   Dump `ioreg -w0 -l` and, inside the device's subtree, read the `IOUserClientCreator` on its
   `IOHIDResourceDeviceUserClient` parent. On Apple Silicon a BLE HID device is published by
   `BTLEServer` (an Apple system binary) — that is the normal path, not a third-party virtual
   clone. Vendor utilities appear as `IOHIDLibUserClient` / `IOHIDParamUserClient` children
   and typically open without seizing (`ClientSeized=No`), so their presence is not proof of
   interception.
3. **Measure, never infer.** Compile and run `scripts/hidprobe.swift` (~20 s) while the user
   clicks once, then moves/spins the input. It prints per-2-s totals for buttons / X-Y deltas
   / wheel plus a verdict:
   - buttons (+wheel) but **0 X/Y deltas** => device-side sensor fault.
   - X/Y deltas arriving => hardware is fine; look downstream (pointer parameters, a
     third-party mouse utility).
   - **zero events for everything, including buttons** => the probe process lacks Input
     Monitoring permission. Grant it to the terminal app and re-run; this is not a dead
     device.
   - "the left click needs several presses": use the raw probe's click-counting phase with
     the **wheel as a link control in the same run**. Wheel delivered 1:1 while click
     down-events are missing => switch/contact trouble; both lossy => link or supply.
   For a dispute over "did the device send anything at all", switch to
   `scripts/hid_report_probe.swift` (raw input-report bytes, rebinds across device instances).
4. **Only then remediate**: device-side cleaning (`references/macos-hid-input-path.md`),
   quit the third-party pointer utility, or reinstall the vendor driver.
5. **For vendor-configuration claims** ("pointer speed is set to 0"): read the vendor's config
   store, do not assume. Logi Options+ keeps everything in a sqlite BLOB
   (`~/Library/Application Support/LogiOptionsPlus/settings.db`, tables `data`/`snapshots`
   only) — dump the blob and parse the JSON; recipe in the references file.

## Isolating the vendor software stack (cheap -> decisive)

Run these in order; each step removes a layer, so silence after a step indicts only what is
left. A BLE HID device needs no vendor daemon on macOS, so step 1 costs nothing:

1. **Quit the vendor app AND unload its launchd agent, then re-measure.** Quitting the app is
   not enough: the agent is what holds the vendor's GATT sessions to the device.
   `launchctl bootout gui/$(id -u)/<Label>` — the Label lives in the plist and often differs
   from the plist's filename — then `pkill -f <agent binary>` if it lingers (agents with
   `KeepAlive { SuccessfulExit = false }` only return on relaunch once booted out). Root-owned
   updater/crashpad helpers cannot be signalled as the user and do not sit in the pointer path.
2. **Re-pair** (forget the device, put it back in pairing mode, re-add). This renegotiates the
   BLE connection parameters, so it is both a test and a plausible fix for tardy input.
3. **Switch the device to the vendor's USB receiver** — bypasses BTLEServer and the whole
   Bluetooth stack, separating "host BLE path" from "device".
4. **Pair it to a second host** (another Mac, a phone). Failing there too => the device itself.

Treat a broken vendor configuration (an unresolved assignment, an empty slider value) as a
*clue* until step 1 has been done: a per-device config gap cannot zero out reports that the
kernel already received at the device layer.

## Pitfalls

- **A probe binds to a device INSTANCE, and instances die.** BTLEServer destroys and recreates
  its `IOHIDUserDevice` on every BLE reconnect; a probe still holding the old instance receives
  nothing more and reports 0 events, which reads exactly like a dead device. Register
  `IOHIDManagerRegisterDeviceMatchingCallback` / `DeviceRemovalCallback`, rebind on add, count
  reports per instance, and void every measurement window in which the instance disappeared.
- **"0 reports" means different things at different layers.**
  `IOHIDDeviceRegisterInputValueCallback` deduplicates: an unchanged report is not delivered,
  so a value-layer zero cannot separate "sent nothing" from "sent identical zeros".
  `IOHIDDeviceRegisterInputReportCallback` gets the raw bytes — use it before claiming the
  device is silent. An idle device legitimately sends nothing; establish that baseline first.
- **Self-test the decoder with synthetic report vectors before trusting the probe, and make the
  printed verdict a function of the numbers printed.** A probe that counted reports while
  ignoring magnitude once announced "hardware is fine" beside `sum|dX|+|dY| = 0`.
- **Read the whole log line before attributing it to a device.** `cut -c1-150` can slice off the
  `pid`/`vid` field — that is how a "the other, working device shows it too" control claim gets
  manufactured and then retracted. Repeated warnings also cluster around connection setup:
  check their position relative to connect/disconnect before calling them chronic.
- **Log evidence can be manufactured by the user's own hands.** A disconnect/reconnect storm and
  a latency warning look identical whether the device failed or the user power-cycled it and
  pressed the pairing button. Timestamp device add/remove events from the probe in the same run
  as the scripted actions, and label log-only evidence a clue rather than a finding.
- **Two `hidutil list` rows with the same VID/PID/serial are normally ONE physical device**:
  the `IOHIDUserDevice` plus the `AppleUserHIDEventService` dext layered on top of it. Walk the
  ioreg ancestor chain before reporting a competing virtual clone — otherwise you publish a
  confident wrong cause and have to retract it.
- `ioreg -r -c <class>` prints nodes in registration order and relationship is only visible
  through indentation; `grep -A/-B` on it silently crosses device boundaries. Dump the whole
  `ioreg -w0 -l` to a file and parse the tree.
- `IOHIDManagerOpen` / `IOHIDDeviceOpen` returning `0` does not mean reports will be
  delivered: value delivery can still be TCC-gated. A silent probe after no user interaction
  is not evidence of anything.
- Registry IDs are re-issued between `ioreg` runs — compare ancestry, never ids from two
  separate invocations.
- `hidutil list` mixes 200+ rows of Apple SMC/SPU endpoints with real devices; filter by
  VendorID/ProductID instead of reading the table.
- Do not conclude "hardware" from an inference chain alone when a physical check is available
  (does the ball spin freely? does the wheel respond?) — those two answers separate mechanical
  jam from a blind sensor in seconds.

## Reporting to this user

- One-sentence conclusion first, then a table of `命令 / 结果` backing every claim. Label
  anything unmeasured as a hypothesis plus the test that would settle it.
- When a hypothesis you raised is disproved by an output, say so explicitly and name the
  output; never quietly drop it.
- If he explains an observation by his own hands-on debugging, downgrade that evidence on the
  spot and name the measurement that would re-earn it; do not defend the finding.
- Hand over commands with expected output for him to run himself; do not execute mutating
  steps (kill/quit/uninstall/pkill) on his machine.
- Keep original English device and software names inside Chinese prose.
- Close the round with: what he wants / what you did / effect of each finding / what is left.

## Files

- `references/macos-hid-input-path.md` — decoded command outputs, HID device attribution,
  Logi Options+ config forensics and HID++ cache decoding, host-side BLE HID log evidence,
  device-side remediation.
- `scripts/hidprobe.swift` — IOHID value probe; build with `swiftc -O hidprobe.swift -o hidprobe`.
- `scripts/hid_report_probe.swift` — raw input-report probe: decoder self-test, device-instance
  tracking with rebinding, ball / click / wheel phases; build with
  `swiftc -O hid_report_probe.swift -o hid_report_probe`.
