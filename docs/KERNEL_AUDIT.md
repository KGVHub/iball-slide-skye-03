# KGV-Pro-X audit — 2026-10-22

Running on the Slide Skye 03: Linux 4.4.83-KGV-Pro-X #11, normal camera
image. Android completes boot; SELinux is enforcing. `/proc/kgv_klog` is
absent in production. Original partition backups are preserved.

## Verified

| Area | Evidence | Limit |
| --- | --- | --- |
| Boot | Android boot completed; remained available during audit | Short session, not a long stress test |
| GPU/display | SurfaceFlinger identifies Mali-T820/r21p0 OpenGL ES 3.2 | GPU boost ioctl remains unported |
| Wi-Fi | Connected; three ICMP packets to 1.1.1.1, zero loss | Throughput/roaming not tested |
| Touch | cst2xx input device present; earlier physical accuracy test passed | No new multitouch test |
| Accelerometer | Continuous nonzero sensor events; earlier rotation test passed | Existing offset not calibrated |
| Camera | Both previews respond to lit scene on debug variant; both normal-kernel streams and JPEG saves pass | Optical/color/exposure quality not calibrated |
| Bluetooth | Settings toggle reached ON; restored previous off state | Pairing/audio not tested |
| Charging | USB powered, battery service reports charging | Charge current not measured externally |
| Screen sleep/wake | Screen sleep/wake returned to Android with uptime preserved | USB power means this does not prove deep suspend |
| Modules | All four rebuilt module CRCs match the normal kernel | `/proc/modules` is denied to shell by stock SELinux |

## Open issues and incomplete checks

**Boot ramdisk bring-up dependency:** normal camera image still loads GPU and
BT/FM modules only on `init.svc.adbd=running`. This is confirmed directly from
its ramdisk and was a rescue measure during driver bring-up. Those actions
cannot run without adbd entering that state; disconnected USB and disabled
ADB behavior have not been tested. A daily-use candidate restores the original
`post-fs` GPU and `boot` BT/FM events. `out/boot-KGV-Pro-X-daily.img` uses the
exact tested kernel/module bytes, changes only the two init script bodies
(preserving archive metadata), and passes AVB signature/hash verification.
It is **not flashed or hardware-validated yet**; user confirmation is pending.
Reproduce with tools/scripts/make_daily_ramdisk.py. This candidate does not
address the timer warning below.

1. **CPU hotplug/timer warning:** current `/proc/sys/kernel/tainted` is 4608
   (warning bit 9 plus out-of-tree-module bit 12). Saved debug #8 log records
   `tick_handle_oneshot_broadcast` at kernel/time/tick-broadcast.c:642 during FIXED in 181c4dac (backport of upstream 1b72d4323798); verified on device, tainted stays 4096.
   CPU1 offline. Its broadcast mask contains an offline CPU. System continued
   running; this is not proof of long-term stability. The normal kernel's
   restricted log interface prevents identifying its warning independently.
   An upstream report describes a similar race, but no fix has been applied
   on that basis alone. https://lists.openwall.net/linux-kernel/2019/03/21/456
2. **GPU boost:** stock KBASE_IOCTL_SET_BOOST behavior not ported; devfreq works.
3. **Sensor compatibility:** `/sys/class/sprd-tpd` is absent. Proximity is
   advertised by the stock HAL but has not been functionally validated. The
   LITEON node in stock DT is disabled; do not invent a sensor driver.
4. Audio playback/recording, FM reception (headphones required), GPS fixes,
   cellular calls/data, Bluetooth pairing/audio, external SD, OTG and deep
   suspend remain unverified in this audit. Earlier BT firmware/discovery tests
   passed and `/dev/ttyBT0` and `/dev/fm` exist.
5. Initial raw backup work observed inconsistent long continuous eMMC reads,
   while verified 16 MiB reads were stable. This predates this audit; preserve
   the verified raw backup and investigate before any large ROM flash.
6. Kernel 4.4.83 has not received a full security/backport audit.

The crash log buffer was empty when sampled. Existing Dropbox last-kmsg
records include old bring-up boots and must not be attributed to the current
kernel without checking their embedded date/version. No new flashing was
performed for this audit.

## ROM-relevant correction

Earlier notes called this non-Treble. Measured properties report
`ro.treble.enabled=true`, vendor policy version is 27.0, and vendor has HIDL
services plus split SELinux policy. Kernel enables 32-bit Binder and Android
uses zygote32. The initial Lineage 15.1 build therefore targets an ARM32,
32-bit-Binder, A-only, non-system-as-root **system image** while retaining the
working boot and stock vendor. Treble properties alone do not prove a generic
image will boot; vendor/system ABI and policy compatibility still need tests.

Detailed local logs (not committed because they contain device/network data)
are `work/kernel_audit_*`, `work/klog_camabi_final_debug.txt` and
`work/dumpsys_camabi_normal_{front,rear}.txt`.

Bluetooth shell toggle attempts produced SecurityException crashes in the shell
`svc` command because UID 2000 lacks BLUETOOTH_ADMIN; these are not kernel or
system_server crashes. The Settings UI toggle succeeded afterward.

Stock init also contains 8-core cpuset writes. Measured possible/present CPUs
are 0-3, and live top-app/foreground/boost masks are already 0-3; background is
0 and system-background 0-2. No cpuset change was made in this audit.
