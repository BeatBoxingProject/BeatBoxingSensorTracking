#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AD HAT Diagnostic and Communication Test Program
Waveshare High-Precision AD HAT (ADS1263)

Usage:
    python core/ad_hat/main.py                    # Interactive / default scan
    python core/ad_hat/main.py --mode scan        # Single-ended channel scan
    python core/ad_hat/main.py --mode diff        # Differential pair scan
    python core/ad_hat/main.py --mode rate        # Sampling rate benchmark
    python core/ad_hat/main.py --mode piezo       # Piezo sensor test
    python core/ad_hat/main.py --mode loadcell    # Load cell test
"""
import os
import sys
import time
import argparse

# Ensure both repo root and local directory are on sys.path for direct execution
_current_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(_current_dir))
for _p in (_repo_root, _current_dir):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from core.ad_hat.device import ADHat
    from core.ad_hat.sensors import PiezoSensor, LoadCell
    from core.ad_hat.config import HAS_HARDWARE
except ImportError:
    try:
        from .device import ADHat
        from .sensors import PiezoSensor, LoadCell
        from .config import HAS_HARDWARE
    except (ImportError, ValueError):
        from device import ADHat
        from sensors import PiezoSensor, LoadCell
        from config import HAS_HARDWARE


def run_single_ended_scan(hat: ADHat, channels=None):
    """Continuously prints voltages for single-ended channels (AIN0-AIN9)."""
    if channels is None:
        channels = [0, 1, 2, 3, 4]

    print(f"\n--- Running Single-Ended Scan on Channels {channels} ---")
    print("Press Ctrl+C to stop.\n")
    hat.set_mode(hat.MODE_SINGLE_ENDED)

    while True:
        line_parts = []
        for ch in channels:
            v = hat.read_voltage(ch)
            line_parts.append(f"IN{ch}: {v:+.4f}V")
        print(" | ".join(line_parts), end="\r")
        time.sleep(0.05)


def run_differential_scan(hat: ADHat, pairs=None):
    """Continuously prints voltages for differential pairs (0 to 4)."""
    if pairs is None:
        pairs = [0, 1, 2]

    pair_names = {
        0: "AIN0-AIN1",
        1: "AIN2-AIN3",
        2: "AIN4-AIN5",
        3: "AIN6-AIN7",
        4: "AIN8-AIN9"
    }

    print(f"\n--- Running Differential Scan on Pairs {pairs} ---")
    print("Press Ctrl+C to stop.\n")
    hat.set_mode(hat.MODE_DIFFERENTIAL)

    while True:
        line_parts = []
        for p in pairs:
            v = hat.read_diff_voltage(p)
            name = pair_names.get(p, f"P{p}")
            line_parts.append(f"{name}: {v:+.6f}V")
        print(" | ".join(line_parts), end="\r")
        time.sleep(0.05)


def run_rate_benchmark(hat: ADHat, samples: int = 1000, channel: int = 0):
    """Benchmarks sampling throughput on a single channel."""
    print(f"\n--- Benchmarking Rate on Channel {channel} ({samples} samples) ---")
    hat.set_mode(hat.MODE_SINGLE_ENDED)

    # Warm up
    hat.read_raw(channel)

    start = time.time()
    for _ in range(samples):
        hat.read_raw(channel)
    elapsed = time.time() - start

    rate = samples / elapsed if elapsed > 0 else 0
    print(f"Elapsed: {elapsed:.3f} s")
    print(f"Throughput: {rate:.1f} samples/second (Hz)")


def run_piezo_test(hat: ADHat, channel: int = 0, threshold: float = 0.5):
    """Runs a test using the PiezoSensor abstraction."""
    print(f"\n--- Piezo Sensor Test on Channel {channel} (Threshold: {threshold}V) ---")
    print("Strike or tap the piezo to observe voltage spikes. Press Ctrl+C to stop.\n")

    piezo = PiezoSensor(hat=hat, channel=channel, threshold_volts=threshold)
    baseline = piezo.calibrate_baseline(samples=10)
    print(f"Calibrated baseline: {baseline:.4f}V\n")

    while True:
        voltage = piezo.read_voltage()
        delta = piezo.read_value()
        impact = piezo.detect_impact()
        status = "[IMPACT DETECTED!]" if impact else "                  "
        print(f"Voltage: {voltage:+.4f}V | Delta: {delta:+.4f}V  {status}", end="\r")
        time.sleep(0.02)


def run_load_cell_test(hat: ADHat, diff_channel: int = 0, gain: str = 'ADS1263_GAIN_64'):
    """Runs a test using the LoadCell abstraction."""
    print(f"\n--- Load Cell Test on Diff Channel {diff_channel} (Gain: {gain}) ---")
    print("Press Ctrl+C to stop.\n")

    load_cell = LoadCell(hat=hat, diff_channel=diff_channel, gain=gain)
    load_cell.configure_hardware()

    print("Zeroing (tare) load cell in 1 second... ensure no load is applied.")
    time.sleep(1)
    tare_val = load_cell.tare(samples=15)
    print(f"Tare complete. Offset voltage: {tare_val:+.6f}V\n")

    while True:
        v = load_cell.read_voltage()
        net = load_cell.read_value()
        print(f"Diff V: {v:+.6f}V | Net Output: {net:+.6f}", end="\r")
        time.sleep(0.05)


def main():
    parser = argparse.ArgumentParser(description="Waveshare AD HAT (ADS1263) Test & Diagnostic Suite")
    parser.add_argument(
        "--mode",
        choices=["scan", "diff", "rate", "piezo", "loadcell"],
        default="scan",
        help="Test mode to execute (default: scan)"
    )
    parser.add_argument("--channel", type=int, default=0, help="Channel index (0-9)")
    parser.add_argument("--diff-channel", type=int, default=0, help="Differential pair index (0-4)")
    parser.add_argument("--rate", default="ADS1263_400SPS", help="Sampling rate key (e.g. ADS1263_400SPS)")
    parser.add_argument("--gain", default="ADS1263_GAIN_1", help="PGA Gain key (e.g. ADS1263_GAIN_1)")
    parser.add_argument("--ref", type=float, default=5.08, help="Reference voltage (default: 5.08V)")
    parser.add_argument("--threshold", type=float, default=0.5, help="Piezo trigger threshold in Volts")
    args = parser.parse_args()

    print("=" * 60)
    print(" Waveshare High-Precision AD HAT Diagnostic Utility")
    print("=" * 60)
    if not HAS_HARDWARE:
        print("[!] NOTICE: Hardware SPI/GPIO not detected. Running with mock interface.")
    else:
        print("[+] Hardware SPI/GPIO detected.")

    hat = ADHat(ref_voltage=args.ref, rate=args.rate, gain=args.gain)

    try:
        print("[*] Initializing AD HAT...")
        if not hat.open():
            print("[X] Failed to initialize AD HAT. Check SPI connection and wiring.")
            sys.exit(1)
        print("[+] AD HAT initialized successfully.\n")

        if args.mode == "scan":
            run_single_ended_scan(hat, channels=[0, 1, 2, 3, 4])
        elif args.mode == "diff":
            run_differential_scan(hat, pairs=[0, 1, 2])
        elif args.mode == "rate":
            run_rate_benchmark(hat, samples=1000, channel=args.channel)
        elif args.mode == "piezo":
            run_piezo_test(hat, channel=args.channel, threshold=args.threshold)
        elif args.mode == "loadcell":
            run_load_cell_test(hat, diff_channel=args.diff_channel, gain='ADS1263_GAIN_64')

    except KeyboardInterrupt:
        print("\n\n[*] Stopped by user (Ctrl+C).")
    finally:
        hat.close()
        print("[*] AD HAT safely shut down.")


if __name__ == "__main__":
    main()
