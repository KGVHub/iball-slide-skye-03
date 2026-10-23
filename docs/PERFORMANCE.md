# LineageOS 15.1 performance

Measurements here use the iBall Slide Skye 03 (SC7731E, four Cortex-A7 cores,
1 GB RAM) with the stock Android 8.1 vendor and kernel #13. Tests are repeated
after each proposed tuning change; a change is kept only when the same workload
improves without breaking hardware.

## Method

- Build one change at a time with `-j1` and package/preflight before testing.
- Reboot, wait at least two minutes, and use the launcher as the starting point.
- Boot: clear logcat, time `adb reboot` to `sys.boot_completed=1`, and retain
  `boot_progress_*` event timestamps.
- Launch: `am force-stop`, return home, wait two seconds, then `am start -W`.
  Run three times per app and compare median `TotalTime`.
- Launcher: reset Trebuchet gfxinfo, run ten left/right swipe pairs at 250 ms per
  swipe, wait two seconds, then read `dumpsys gfxinfo`.
- Memory pressure: force-stop the five targets, launch Settings, Camera, FM
  Radio, Gallery and Jelly in that order, returning home between launches, then
  check memory and whether every process survived.
- Screen-off drain: disconnect USB, note charge counter/level, leave the tablet
  untouched with the screen off for a real hour, and record the ending values.
  Do not extrapolate a short sample.

## Baseline — 2026-10-23

This is LineageOS 15.1 without performance tuning. The cosmetic cleanup from
commit `1561599` was debug-pushed first; it suppresses harmless audit noise and
prevents the incompatible vendor ModemNotifier from starting, but changes no
CPU, VM, I/O, graphics, heap or dexopt tuning. A clean image was built and
preflighted but was not flashed.

### Summary

| Variant | Boot complete | Free RAM idle | Free RAM after 5 apps | Apps surviving | Settings | Camera | FM Radio | Gallery | Launcher jank |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 43.251 s | 427,092 KiB | 369,556 KiB | 5/5 | 1,187 ms | 1,677 ms | 1,120 ms | 1,062 ms | 118/480 (24.58%) |

Launch columns are median `TotalTime` from three force-stopped runs.

### Boot

One host-observed reboot sample reached `sys.boot_completed=1` in 43.251 s.
Event-log timestamps are milliseconds since kernel boot:

| Event | Time |
| --- | ---: |
| `boot_progress_start` | 6.034 s |
| `boot_progress_preload_start` | 7.134 s |
| `boot_progress_preload_end` | 9.443 s |
| `boot_progress_system_run` | 10.954 s |
| `boot_progress_pms_start` | 13.052 s |
| `boot_progress_pms_system_scan_start` | 14.233 s |
| `boot_progress_pms_data_scan_start` | 15.201 s |
| `boot_progress_pms_scan_end` | 15.209 s |
| `boot_progress_pms_ready` | 15.930 s |
| `boot_progress_ams_ready` | 22.402 s |
| `boot_progress_enable_screen` | 25.698 s |

### App launch raw values

| App and component | Run 1 | Run 2 | Run 3 | Median |
| --- | ---: | ---: | ---: | ---: |
| Settings `com.android.settings/.Settings` | 1,257 ms | 1,187 ms | 1,130 ms | 1,187 ms |
| Camera `com.android.camera2/com.android.camera.CameraLauncher` | 1,841 ms | 1,568 ms | 1,677 ms | 1,677 ms |
| FM Radio `com.android.fmradio/.FmMainActivity` | 1,152 ms | 1,094 ms | 1,120 ms | 1,120 ms |
| Gallery `com.android.gallery3d/.app.GalleryActivity` | 1,204 ms | 1,062 ms | 1,033 ms | 1,062 ms |

### Launcher rendering

The valid fixed 20-swipe Trebuchet workload rendered 480 frames, of which 118
were janky (24.58%). Frame-time percentiles were 10 ms p50, 22 ms p90, 30 ms
p95, and 48 ms p99. Gfxinfo attributed 12 frames to a slow UI thread and 108 to
slow draw-command issue. An earlier 36/39 result was discarded because the
launcher view reported `visibility=8`; it did not measure visible scrolling.
ADB injection contributes fixed input overhead, so comparisons must use this
exact workload; the absolute percentage is not a general UI score.

Live GPU sampling during this workload showed the `simple_ondemand` governor
repeatedly falling to 153.6 MHz between gesture bursts, although it could reach
600 MHz. Temporary diagnostic floors, restored to automatic mode immediately
after each run, strongly implicated ramp latency:

| Temporary GPU floor | Janky frames | p50 | p90 | p95 | p99 | Missed vsync |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Automatic (153.6–600 MHz) | 118/480 (24.58%) | 10 ms | 22 ms | 30 ms | 48 ms | 8 |
| 600 MHz | 46/485 (9.48%) | 10 ms | 16 ms | 20 ms | 26 ms | 0 |
| 384 MHz | 31/488 (6.35%) | 9 ms | 15 ms | 18 ms | 27 ms | 0 |

Two lower `gpu_upthreshold` experiments were less effective than the floor. A
threshold of 40 produced 61/453 janky frames (13.47%), while 20 produced 80/476
(16.81%); both were restored to the stock value of 80 after testing.

### Memory

Settled idle at 244.79 s uptime:

- Total RAM 926,312 KiB; Android `dumpsys meminfo` Free RAM 427,092 KiB.
- `/proc/meminfo` MemAvailable 526,232 KiB and MemFree 148,040 KiB.
- Used RAM 437,615 KiB; Lost RAM 61,601 KiB.
- 16 cached processes; ModemNotifier process absent.
- zram0: 800 MiB, lz4 selected, priority -1, no swap used.

After the five-app workload, all 5/5 target processes survived. Android Free RAM
was 369,556 KiB, MemAvailable 443,064 KiB, Used RAM 472,734 KiB, Lost RAM
112,586 KiB, and 42,460 KiB of swap was used (12,432 KiB physical zram).

### Runtime and storage state

- `ro.config.low_ram=true`.
- ART heap: 8 MiB start, 128 MiB growth limit, 256 MiB maximum, 512 KiB
  minimum free, 8 MiB maximum free, target utilization 0.75.
- No build-time dexpreopt. Runtime filters: boot `verify`, first boot/install/
  shared `quicken`, background dexopt `speed-profile`.
- CPU governor `interactive`; available governors are `sprdemand`, `userspace`,
  `interactive`, and `performance`; frequency range 768 MHz–1.3 GHz.
- eMMC scheduler CFQ selected (`noop` also available); read-ahead 128 KiB.

In a 60.18-second screen-off residency sample, CPU0 spent 59.43 s (98.75%) at
768 MHz, 0.65 s at 1.3 GHz, and 0.10 s at intermediate frequencies. CPUs 0–1
were online. This is a frequency-residency check, not a power-drain result.

### Pending baseline item

Screen-off battery drop per hour is not yet measured. The tablet was USB-powered
at 100% (charge counter 2,846,000) during automated testing, which invalidates a
drain measurement. Run the one-hour unplugged test before accepting a power-
sensitive tuning change.

## Change log

| Change | Boot | Idle free RAM | 5-app free RAM | Launch medians | Launcher jank | Result |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| Baseline | 43.251 s | 427,092 KiB | 369,556 KiB | 1187 / 1677 / 1120 / 1062 ms | 24.58% | Reference |
| GPU minimum 384 MHz | Not retested | Not retested | Not retested | Not retested | 7.77% | Keep |
| Simple Trebuchet drawer transition | Not retested | Not retested | Not retested | Not retested | 29.29% vertical | Keep |

### GPU minimum 384 MHz — 2026-10-23

`kgv-perf.rc` sets the Mali devfreq minimum to 384 MHz after
`sys.boot_completed`. This keeps the existing `simple_ondemand` governor and
Mali demand power policy; the maximum remains 600 MHz. The rule survived a
reboot and the same visible 20-swipe workload rendered 489 frames with 38 janky
(7.77%), versus 118/480 (24.58%) before the change. That is a 68.4% relative
reduction. Percentiles changed from 10/22/30/48 ms to 10/15/19/25 ms at
p50/p90/p95/p99, and missed vsyncs fell from 8 to 0.

The Android battery service reports a fixed 20.0 degrees C and is not a valid
thermal source on this device. TWRP 3.7.0_9-KGV exposes the underlying thermal
zones: before the sustained test, CPU was 38.989 degrees C and board was 37.100
degrees C. After four consecutive 20-swipe rounds and the immediate recovery
reboot, CPU was 39.888 degrees C (+0.899) and board was 37.700 degrees C
(+0.600). No launcher restart or crash was observed. The charger thermal zone
returns `EINVAL`.

This short connected test finds no immediate thermal regression, but does not
establish battery neutrality. USB power also woke the panel during the attempted
screen-off sample. The pending one-hour unplugged baseline and an equivalent
post-change run are required before release v1.2.

### Simple Trebuchet drawer transition — 2026-10-23

The horizontal workspace test did not cover the vertical workspace/app-drawer
gesture. With the 384 MHz GPU floor already active, ten drawer open/close pairs
rendered 713 frames with 497 janky (69.71%), p50/p90/p95/p99 of
20/40/53/81 ms, and 56 missed vsyncs. Five isolated, fully settled samples also
showed that both opening and closing were affected, rather than overlapping
animations causing the result.

Lowering interactive `go_hispeed_load` from 99 to 85 and disabling only the
drawer gradient did not produce a stable improvement; both experiments were
reverted. The kept change uses Trebuchet's opaque drawer and, during the gesture,
translates a temporary hardware-cached drawer layer instead of redrawing and
blending the gradient, workspace, hotseat and drawer content every frame.

The identical ten-pair workload after this change rendered 652 frames with 191
janky (29.29%), p50/p90/p95/p99 of 13/28/36/46 ms, and 8 missed vsyncs. Relative
jank fell 58.0%; slow draw-command frames fell from 408 to 140. A subsequent
horizontal regression run measured 7.47% jank and zero missed vsyncs, consistent
with the 7.77% post-GPU-floor result. The drawer is now opaque rather than
wallpaper-tinted. No launcher crash was present after the settled test.

## Dexpreopt — 2026-10-23 (kept)

Change: precompile the framework and every app (`WITH_DEXPREOPT=true`, and
`WITH_DEXPREOPT_BOOT_IMG_AND_SYSTEM_SERVER_ONLY=false`, because userdebug
otherwise preopts only the boot image and system server). Go defaults kept:
profile-based boot image, system_server `speed-profile`, shared APKs
`quicken`. 85 of 100 apps got odex/vdex; the other 15 have no dex (themes,
accents, CTS shims, the DreamFMRadio config dir). System content 459 MB to
575 MB of the 1279 MB payload limit. Built at `-j1` with no OOM kills.
Flashed as a full system image (sha256 `1a9b2233...`), user data kept;
first boot 42 s.

Measured with `tools/scripts/perf_bench.sh` (this document's method: median
of three force-stopped `am start -W`, ten left/right home-screen swipe pairs
at 250 ms) after two minutes idle; boot timed from `adb reboot`.

| Metric | Baseline | Dexpreopt | Change |
| --- | ---: | ---: | ---: |
| Boot to `sys.boot_completed` | 43.251 s | 33.396 s | -23% |
| `boot_progress_ams_ready` | 22.402 s | 15.343 s | -32% |
| `boot_progress_enable_screen` | 25.698 s | 17.992 s | -30% |
| Settings launch | 1,187 ms | 843 ms | -29% |
| Camera launch | 1,677 ms | 1,394 ms | -17% |
| FM Radio launch | 1,120 ms | 715 ms | -36% |
| Gallery launch | 1,062 ms | 869 ms | -18% |
| Free RAM idle | 427,092 KiB | 426,543 KiB | same |
| Launcher swipes | 7.47% janky (after GPU floor) | 98/1413 (6.94%), p50/p90/p95/p99 10/15/19/26 ms | same or better |

The launcher figure uses this script's swipe coordinates (520<->80 px at
y=500); compare future runs with the same script. Hardware rechecked after
the flash: touch, WiFi, GPU, FM device, log HAL; no services restarting, no
crashes, only the known harmless service-lookup denials.

## Kernel Turbo round 1: -O2 and Cortex-A7 tuning — 2026-10-23 (kept)

Kernel #13 -> #14 (kernel-blu: build with -O2 instead of -Os, -mtune=cortex-a7
for ARCH_SPRD). Same LineageOS ramdisk, DT and system (dexpreopt build).
Boot image `out/boot-KGV-Pro-X-turbo1.img` (sha256 `0ba9ddcd...`).

| Metric | Dexpreopt, kernel #13 | Turbo 1, kernel #14 | Change |
| --- | ---: | ---: | ---: |
| Boot to `sys.boot_completed` | 33.396 s | 33.441 s | same |
| `boot_progress_ams_ready` | 15.343 s | 14.778 s | -4% |
| `boot_progress_enable_screen` | 17.992 s | 17.094 s | -5% |
| Settings launch | 843 ms | 768 ms | -9% |
| Camera launch | 1,394 ms | 1,338 ms | -4% |
| FM Radio launch | 715 ms | 695 ms | -3% |
| Gallery launch | 869 ms | 671 ms | -23% |
| Launcher swipes janky | 6.94% | 5.46% (p99 26 ms) | better |
| Idle free RAM, 2 min after boot | 427,092 KiB (baseline) | 423,689 KiB | same (kernel +1 MB) |

Free RAM measured right after the benchmark (377 MB) is not comparable with
the idle figure; measure idle RAM before launching apps. Hardware rechecked:
touch, GPU, FM, BT TTY, WiFi with internet, no services restarting, no
crashes, taint 4096.

## Kernel Turbo round 2: HZ=300 — 2026-10-23 (rejected)

Kernel #15 = round 1 + `CONFIG_HZ=300`, with the four driver modules rebuilt
against it (HZ is compiled into modules). Two benchmark runs averaged:
Settings 817 ms, Camera 1,253 ms, FM Radio 684 ms, Gallery 678 ms, launcher
6.4% janky. Against round 1 (768/1,338/695/671 ms, 5.46%) this is within
run-to-run noise for launches and slightly worse for the launcher, while
tripling timer interrupts. Rejected; HZ stays 100.

## Kernel Turbo round 2b: -O2 driver modules — 2026-10-23 (kept)

Kernel #16 = round 1 exactly (`HZ=100`, -O2, -mtune=cortex-a7) with the Mali,
WiFi, BT and FM modules rebuilt against it, so they also build with -O2 (round
1 still loaded the older -Os modules). Built with
`tools/scripts/build_modules.sh` (reproducible byte for byte); ramdisk
differs from the LineageOS boot image only in those four files. Boot image
`out/boot-KGV-Pro-X-turbo2b.img` (sha256 `06fa9d23...`).

| Metric | Round 1 (#14, -Os modules) | Round 2b (#16, -O2 modules), 2-run avg | Change |
| --- | ---: | ---: | ---: |
| Boot to `sys.boot_completed` | 33.441 s | 32.697 s | -2% |
| Settings launch | 768 ms | 816 ms | noise |
| Camera launch | 1,338 ms | 1,146 ms | -14% |
| FM Radio launch | 695 ms | 639 ms | -8% |
| Gallery launch | 671 ms | 617 ms | -8% |
| Launcher swipes janky | 5.46% | 5.53% (runs 6.38%, 4.68%) | same |
| Idle free RAM, 2 min after boot | 423,689 KiB | 443,664 KiB | same or better |

Hardware: GPU, FM, BT TTY present, WiFi associates and passes traffic
(the network's ISP DNS servers were not answering during the test; IP
traffic to 8.8.8.8 worked), no crashes, taint 4096. Single runs vary by up
to ~10% on this tablet: compare averages of at least two runs.

### Since the start of the performance pass

| Metric | Baseline | Now (dexpreopt + Turbo 2b) |
| --- | ---: | ---: |
| Boot | 43.251 s | 32.697 s (-24%) |
| Settings | 1,187 ms | 816 ms (-31%) |
| Camera | 1,677 ms | 1,146 ms (-32%) |
| FM Radio | 1,120 ms | 639 ms (-43%) |
| Gallery | 1,062 ms | 617 ms (-42%) |
| Launcher jank (this script's workload) | 6.94% after dexpreopt | 5.53% |

## Round 3: eMMC I/O scheduler and read-ahead — 2026-10-23 (no change)

Tested live (root, no flash) with cold launches (page cache dropped before
each launch), medians of three, two rounds per setting. Totals of the four
launches: cfq/128 KB 3,888 ms, noop/128 KB 3,800 ms (-2.3%), noop/512 KB
3,809 ms (-2.0%). Within run-to-run noise; cfq/128 KB kept.

## Round 4: keep all CPU cores online — 2026-10-23 (kept, power cost pending)

Spreadtrum hotplug (`/sys/devices/system/cpu/cpuhotplug`) allowed one online
core (`cluster0_core_min_limit=1`) and brings cores back only after 80-90%
load for a sampling window. Tested live, two `perf_bench.sh` runs each,
kernel #16:

| Min online cores | Settings | Camera | FM Radio | Gallery | Launcher jank | p99 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 (default) | 907 ms | 1,252 ms | 647 ms | 602 ms | 6.5% | 25.5 ms |
| 2 | 826 ms | 1,139 ms | 650 ms | 639 ms | 5.5% | 23 ms |
| 4 | 832 ms | 1,127 ms | 612 ms | 607 ms | 4.0% | 21 ms |

Kept 4 in `kgv-perf.rc` (applied after boot, no denials). Idle power with
four cores online is NOT measured yet (battery was full and charging stopped,
so charge current could not be used); the one-hour unplugged screen-off test
must compare 1 and 4 before release. Reverting is one line.

## Round 5: interactive go_hispeed_load with all cores online — 2026-10-23 (no change)

Live A/B, two `perf_bench.sh` runs each. 99 (default): Settings 866 ms,
Camera 1,156 ms, FM 611 ms, Gallery 619 ms, launcher 3.7% janky. 85: 799,
1,141, 600, 614 ms, 3.5%. The spread between two runs at 99 (Settings
927/805 ms, jank 4.84/2.56%) exceeds the difference, as Codex found before
the hotplug change. Default kept. With all cores online the launcher now
measures 2.6-4.8% janky (baseline 24.58% on Codex's original workload).
