# macOS HID input path — decoded outputs and recipes

## 1. Health checklist: command -> healthy reading -> what a deviation means

### `system_profiler SPBluetoothDataType`
Healthy: the device under `Connected:` with `Battery Level`, `Minor Type: Mouse` (or
`Keyboard`), `Services: ... < BLE >`. Not under `Connected:` => link-layer problem, stop and
fix pairing first; nothing downstream can be diagnosed.

### `hidutil list`
Columns: `VendorID ProductID LocationID UsagePage Usage RegistryID Transport Class Product
UserClass Built-In`. Healthy for a mouse: a row with `UsagePage 1` / `Usage 2` (Generic
Desktop / Mouse), `Transport = Bluetooth Low Energy`, class `AppleUserHIDEventService` with
UserClass `AppleUserHIDEventDriver`. A device property `RequiresTCCAuthorization = 1` means
reading its reports needs Input Monitoring permission for the reading process.

### `ioreg -c IOHIDSystem -w0` -> `HIDParameters`
Defaults seen on a healthy install: `HIDPointerAcceleration = 45056`,
`HIDMouseAcceleration = 196608`, `HIDScrollAcceleration = 20480`, `MouseButtonMode = OneButton`,
`HIDUseLinearScalingMouseAcceleration = 0`. A near-zero scaling factor here (or in
`com.apple.mouse.scaling`, normally `3`) is a genuine software cause of "no pointer movement".

### `systemextensionsctl list`
Shows which dext/system extensions are actually loaded; unrelated extensions (e.g. a
virtual-camera extension) are noise, not suspects.

## 2. Attaching a HID device to the process that published it

```
ioreg -w0 -l > /tmp/ioreg.txt     # full dump; -r -c <class> loses the tree
```

Find the device by a property line (`"Product" = "<name>"`), then read the node headers above
it by indentation. The pattern for a published (not kernel-native) device:

```
IOResources > IOHIDResource
  > IOHIDResourceDeviceUserClient        <-- "IOUserClientCreator" = "pid N, BTLEServer"
    > IOHIDUserDevice ("<product>")       DeviceAddress / kBTHardwareRevisionKey / ModelNumber
      > IOHIDInterface
        > AppleUserHIDEventDriver  (class AppleUserHIDEventService)
          > IOHIDLibUserClient            <-- "IOUserClientCreator" = "pid N, WindowServer"
```

- `BTLEServer` = `/usr/sbin/BTLEServer`, Apple's own Bluetooth LE HID service on Apple
  Silicon. A BLE mouse/keyboard appearing as an `IOHIDUserDevice` created by it is NORMAL.
- Vendor daemons show up as `IOHIDLibUserClient` (device read) and `IOHIDParamUserClient` on
  `IOHIDSystem` (they write HID parameters, e.g. pointer acceleration). Their client's
  `DebugState` carries `ClientSeized=No` / `ClientOpened=Yes` — an open without seize does not
  divert the pointer.

## 3. Measuring real reports — `scripts/hidprobe.swift`

```
swiftc -O hidprobe.swift -o hidprobe
./hidprobe 20                  # 20 seconds, defaults to a Logitech VID/PID
./hidprobe 20 0x05ac 0x0343    # example: Apple internal trackpad
```

Interpretation:

| Observation | Meaning |
|---|---|
| buttons and wheel events, `X/Y reports = 0` | device sends reports but no motion: ball / optical sensor path is dead |
| `X/Y reports` in the hundreds, large `sum|dX|+|dY|` | device is fine; the loss is downstream (host parameters or a third-party pointer utility) |
| absolutely nothing, even for a button click | Input Monitoring permission missing for the terminal app — not a dead device |

Per-2-s aggregate lines are deliberate: raw motion arrives at ~125 Hz and per-event printing
buries the signal.

## 4. Logi Options+ configuration forensics

`~/Library/Application Support/LogiOptionsPlus/settings.db` is sqlite with only `data` and
`snapshots` tables; the real config is one JSON BLOB in `data.file`, so a `SELECT` on the
schema finds nothing useful. Extract the blob:

```sql
SELECT writefile('/tmp/logi.json', file) FROM data WHERE _id = 1;
```

Then parse the JSON and search for the device's `slotPrefix` (from the top-level
`ever_connected_devices`, which maps `deviceModel` / `slotPrefix` / `udid` / `deviceType`) and
for overrides such as `mouseSettings.pointerSpeed.active` (empty `{}` = no override). Slots are
named `<slotPrefix>_c<NN>` plus `<slotPrefix>_mouse_settings`; the same card id is shared by
every device in a profile, so comparing a known-good device's slot against the suspect device's
slot localises an unresolved value (one device populated, the other `{}`). Such a gap is a
clue, not a functional fault: it is not in the report path, so it cannot zero out reports the
kernel already received at the device layer — prove it by quitting the whole vendor stack
(SKILL.md, "Isolating the vendor software stack") and re-measuring.
App-level (root-owned) files live in
`/Library/Application Support/Logitech.localized/LogiOptionsPlus/`; per-user settings live in
the user path above. Options+ applies pointer tuning through `IOHIDParamUserClient` on
`IOHIDSystem`, so the result shows up in `HIDParameters`.

## 5. Device-side remediation for a trackball with a silent sensor

Vendor/iFixit-documented for the Logitech ERGO thumb-trackball family (M570 / MX Ergo /
M575); the documented failure class is debris in the sensor chamber, presenting as ball
hesitation, cursor jitter, or no motion at all:

1. Power off (bottom switch).
2. Eject the ball through the underside **trackball eject hole** (manual item 17).
3. Wash the ball with mild soap and water, then dry it fully. Solvent/alcohol leaves a glossy
   surface that the optical sensor tracks poorly.
4. Inspect the empty chamber: **three small bearing balls** plus the IR sensor window. Hair
   wrapped around the bearings jams the ball; dust on the window blinds the sensor. Clean dry
   (cotton bud / air blower), never scratch.
5. Reseat the ball and press it fully into its seat before testing.
6. Still silent => suspect the sensor board/ribbon or claim warranty; cross-test on another
   computer, or with a Unifying/Logi Bolt receiver instead of BLE, to separate device from host.

These are manufacturer-documented remediations to try, not a verified diagnosis for any
particular unit — say so when handing them over.

## 6. Host-side BLE HID log evidence

```
log show --last 45m --style compact --predicate 'process == "BTLEServer"'
log show --last 45m --style compact --predicate 'eventMessage CONTAINS "HID lag"'
```

- `Peripheral "<private>" is now connected` / `Detected mouse LE HID` /
  `[com.apple.iohid:userdevice] <id>: Start: <IOHIDUserDeviceRef ... stats:0,0,N>` — one `Start`
  per HID device instance BTLEServer publishes. `Unable to create queue analytics` is harmless
  noise. `Destroy:` (logged twice, `ref:1/2` and `ref:0/0`, for its two clients) ends that
  instance. **Count Start/Destroy pairs to measure link stability from the host's view**, and
  note the instance id (e.g. `0x10000115c`) so you can tell whether a probe is still bound to a
  live instance.
- Disconnect reasons — the distinction that matters:
  - `Error Domain=CBErrorDomain Code=7 "The specified device has disconnected from us."` — the
    peripheral ended the link. Power-cycling the device or switching its channel produces
    exactly this, so on its own it proves nothing.
  - `Error Domain=CBErrorDomain Code=6 "The connection has timed out unexpectedly."` — a
    timeout rather than a device-initiated teardown; not explained by power-cycling.
  - `is disconnected: (null) N seconds ago, is reconnecting: 1` — the number is how long the
    connection had lasted. Sub-second values mean connect-then-die; a burst of identical lines
    inside one millisecond is a single cleanup storm, not N independent events.
- `HID Latency Statistics events indicated HID lag issue is detected on connection handle 0x...,
  vid = 1133 (0x046d), pid = ...` — the line names the device. Never truncate below the `pid`
  field. Warnings within seconds of a connect are connection-setup artifacts; only a warning in
  the middle of a long-lived connection indicates chronic latency.

## 7. Logi Options+ extras: HID++ cache, launchd labels

- `~/Library/Application Support/logioptionsplus/devio_cache/<PIDhex>_<hash>.xml` — cached
  HID++ request/response pairs: what the vendor software actually read from the device. Each
  `<command cmd="..." rsp="..."/>` maps a command to the device's answer; the lookup form
  `cmd="10FF000A<featureId>"` puts the feature index in the first response byte (`00` =
  unsupported). Decoding that table gives the device's supported feature set — the way to check
  whether a software switch that could suppress an input even exists at all (a plain BLE mouse
  exposes only: feature set, FW version, device name, reset, battery, LED, control table,
  adjustable DPI — none of them able to gate motion output). The same file yields device name,
  firmware version (e.g. `MPM26.00_0009`), PID, and DPI state (`ADJUSTABLE_DPI` read/write,
  error byte `00` = OK). A healthy control plane with no motion output localises the fault to
  the sensor→report path.
- `devio_cache/paired.xml` — path/pid/name/serial for every paired device; `ble_pids.xml` —
  adapter address -> PID map.
- Stopping the whole stack: `/Library/LaunchAgents/com.logi.optionsplus.plist` declares
  `Label = com.logi.cp-dev-mgr` (Label ≠ filename), `KeepAlive { SuccessfulExit = false }`,
  `RunAtLoad`. So `launchctl bootout gui/$(id -u)/com.logi.cp-dev-mgr`, then
  `pkill -f logioptionsplus` / `pkill -f LogiPluginService`. Root-owned
  `logioptionsplus_updater` and `logi_crashpad_handler` survive a user pkill ("Operation not
  permitted") and do not touch the input path. Restore with `open -a logioptionsplus`; the job
  reloads at next login.
- `sentry_db_logioptionsplus_{agent,updater}/<uuid>.run/` collects crash-report payloads — a
  fresh `.run` directory timestamps a crash or teardown of that component.
