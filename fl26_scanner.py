"""
FL26 Memory Scanner v4 — raw bytes, no struct dependency.
Handles all Windows versions by using a raw buffer.
REQUIREMENTS: pip install pymem
RUN AS ADMINISTRATOR.
"""
import sys
import time
import struct
import ctypes

try:
    import pymem
except ImportError:
    print("Run: pip install pymem")
    sys.exit(1)

kernel32 = ctypes.windll.kernel32
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFO = 0x0400
MEM_COMMIT = 0x1000


def scan(pm, target):
    """Scan all readable memory for a u32 value."""
    results = []
    packed = struct.pack("<I", target)

    pid = pm.process_id
    handle = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFO, False, pid)
    if not handle:
        err = kernel32.GetLastError()
        print(f"  OpenProcess FAILED (error {err})")
        print("  Run as Administrator!")
        return []

    # Use a raw 64-byte buffer — works regardless of Windows version
    # The actual MEMORY_BASIC_INFORMATION is 48 or 56 bytes depending on build
    buf = (ctypes.c_char * 64)()
    address = 0
    regions = 0
    total_bytes = 0

    while address < 0x7FFFFFFFFFFF:
        ret = kernel32.VirtualQueryEx(handle, ctypes.c_void_p(address), buf, 64)
        if ret == 0:
            # Failed — try advancing
            address += 0x1000
            continue

        # Parse raw bytes manually
        # Layout (64-bit, no PartitionId): BaseAddress(8) AllocBase(8) AllocProtect(4) RegionSize(8) State(4) Protect(4) Type(4) = 40 bytes
        # Layout (with PartitionId): same + PartitionId(2) = 42 bytes, padded to 48
        # ret tells us the actual size used
        if ret >= 40:
            raw = buf.raw[:ret]
            base = struct.unpack_from("<Q", raw, 0)[0]   # BaseAddress
            size = struct.unpack_from("<Q", raw, 16)[0]   # RegionSize (offset 16 if no PartitionId)

            # If size is absurd, try with PartitionId layout (offset 18→24 for RegionSize)
            if size == 0 or size > 0x7FFFFFFFFFFF:
                if ret >= 48:
                    size = struct.unpack_from("<Q", raw, 24)[0]  # RegionSize with PartitionId
                if size == 0 or size > 0x7FFFFFFFFFFF:
                    address += 0x1000
                    continue

            state = struct.unpack_from("<I", raw, 24 if ret >= 48 else 24)[0]
            # Actually state is at offset 24 (no partition) or 32 (with partition)
            # Let's read both and pick the sensible one
            state_a = struct.unpack_from("<I", raw, 24)[0] if len(raw) >= 28 else 0
            state_b = struct.unpack_from("<I", raw, 32)[0] if len(raw) >= 36 else 0
            prot_a = struct.unpack_from("<I", raw, 28)[0] if len(raw) >= 32 else 0
            prot_b = struct.unpack_from("<I", raw, 36)[0] if len(raw) >= 40 else 0

            # Use whichever state = MEM_COMMIT (0x1000)
            use_b_layout = (state_b == MEM_COMMIT and prot_b in (0x02, 0x04, 0x20, 0x40))
            state = state_b if use_b_layout else state_a
            prot = prot_b if use_b_layout else prot_a

            # Recalculate region size based on layout
            if use_b_layout:
                size = struct.unpack_from("<Q", raw, 24)[0]
                # Wait that doesn't make sense. Let me just read it properly.
                pass

            if base == 0 or size == 0:
                address += 0x1000
                continue

            if state == MEM_COMMIT and prot in (0x02, 0x04, 0x20, 0x40):
                if size < 100_000_000:
                    read_buf = (ctypes.c_char * size)()
                    bytes_read = ctypes.c_size_t(0)

                    ok = kernel32.ReadProcessMemory(
                        handle, ctypes.c_void_p(base), read_buf, size,
                        ctypes.byref(bytes_read))

                    if ok and bytes_read.value > 0:
                        data = read_buf.raw[:bytes_read.value]
                        total_bytes += bytes_read.value

                        off = 0
                        while off < len(data):
                            idx = data.find(packed, off)
                            if idx == -1:
                                break
                            results.append(base + idx)
                            off = idx + 1

                        if len(results) > 500000:
                            print(f"  (stopped at 500k)")
                            break

                    regions += 1

            address = base + size
        else:
            address += 0x1000

    kernel32.CloseHandle(handle)
    print(f"  Scanned {regions} regions ({total_bytes // (1024*1024)}MB)")
    return results


def read_u32(pm, addr):
    try:
        return struct.unpack("<I", pm.read_bytes(addr, 4))[0]
    except Exception:
        return None


def dump_nearby(pm, addr, radius=64):
    print(f"\n  Memory around 0x{addr:016X}:")
    for offset in range(-radius, radius + 1, 4):
        a = addr + offset
        v = read_u32(pm, a)
        if v is not None:
            marker = " <--- SCORE" if offset == 0 else ""
            flag = " *" if 0 < v < 50 and offset != 0 else ""
            print(f"  {offset:>+6}  0x{a:016X}  {v:>10}{marker}{flag}")


def main():
    print("=" * 55)
    print("  FL26 Memory Scanner v4")
    print("=" * 55)

    for name in ["FL_2026", "FL2026", "PES2021"]:
        try:
            pm = pymem.Pymem(name)
            print(f"Connected: {name} (PID: {pm.process_id})")
            break
        except Exception:
            continue
    else:
        print("FL26 not found.")
        return

    # Quick test: can we read ANY memory?
    print("\nTesting memory access...")
    try:
        test = pm.read_bytes(pm.process_base.lpBaseOfDll, 4)
        print(f"  Read test OK: {test.hex()}")
    except Exception as e:
        print(f"  Read test FAILED: {e}")
        print("  Try running as Administrator.")
        return

    print()
    print("STEP 1: Score a goal in FL26, then enter the HOME score.\n")

    score = int(input("  HOME score (> 0): ").strip())
    if score <= 0:
        print("Must be > 0!")
        return

    print(f"\nScanning for {score}...")
    candidates = scan(pm, score)
    print(f"Found {len(candidates)} matches")

    if not candidates:
        print("\nNo u32 matches. Trying u8 and u16...")
        for dtype, sz, fmt in [("u8", 1, "<B"), ("u16", 2, "<H")]:
            packed = struct.pack(fmt, score)
            handle = kernel32.OpenProcess(
                PROCESS_VM_READ | PROCESS_QUERY_INFO, False, pm.process_id)
            buf = (ctypes.c_char * 64)()
            address = 0
            count = 0
            while address < 0x7FFFFFFFFFFF:
                ret = kernel32.VirtualQueryEx(handle, ctypes.c_void_p(address), buf, 64)
                if ret == 0:
                    address += 0x1000
                    continue
                raw = buf.raw[:ret]
                base = struct.unpack_from("<Q", raw, 0)[0]
                size = struct.unpack_from("<Q", raw, 16)[0]
                if base == 0 or size == 0 or size > 0x7FFFFFFFFFFF:
                    address += 0x1000
                    continue
                # Check if committed
                prot_off = 12  # offset of protection in MBI
                state_off = 24  # approximate
                state_val = struct.unpack_from("<I", raw, state_off)[0] if len(raw) > state_off+4 else 0
                prot_val = struct.unpack_from("<I", raw, prot_off+4)[0] if len(raw) > prot_off+8 else 0

                if state_val == MEM_COMMIT and prot_val in (0x02, 0x04, 0x20, 0x40):
                    if size < 100_000_000:
                        rbuf = (ctypes.c_char * size)()
                        bread = ctypes.c_size_t(0)
                        ok = kernel32.ReadProcessMemory(
                            handle, ctypes.c_void_p(base), rbuf, size, ctypes.byref(bread))
                        if ok and bread.value > 0:
                            data = rbuf.raw[:bread.value]
                            off = 0
                            while off < len(data):
                                idx = data.find(packed, off)
                                if idx == -1:
                                    break
                                candidates.append(base + idx)
                                off = idx + 1
                            if len(candidates) > 500000:
                                break
                address = base + size
            kernel32.CloseHandle(handle)
            print(f"  {dtype}: {len(candidates)} matches")
            if candidates:
                break

    if not candidates:
        print("\nStill nothing. The game may encrypt/obfuscate memory.")
        print("FL26/SmokePatch is known to have anti-tamper protections.")
        print("\nFALLBACK: Use /quickresult + /updatestats manually in Discord.")
        return

    # Narrow if too many
    if len(candidates) > 5000:
        print(f"\nToo many. Score another goal and narrow down.")
        new = int(input(f"  New score (was {score}): ").strip())
        candidates = [a for a in candidates if read_u32(pm, a) == new]
        score = new
        print(f"Narrowed to {len(candidates)}")

    # Save
    with open("fl26_scan_results.txt", "w") as f:
        for a in candidates[:200]:
            f.write(f"0x{a:016X}\n")

    # Live monitor
    if 0 < len(candidates) <= 10000:
        print(f"\nMonitoring {len(candidates)} addresses. Score a goal. Ctrl+C to stop.\n")
        prev = {a: read_u32(pm, a) for a in candidates}
        try:
            while True:
                time.sleep(0.3)
                for a in candidates:
                    v = read_u32(pm, a)
                    if v != prev[a]:
                        print(f"\n>>> CHANGED: 0x{a:016X}: {prev[a]} -> {v}")
                        dump_nearby(pm, a, 64)
                        with open("fl26_score_address.txt", "w") as f:
                            f.write(f"0x{a:016X}\n")
                        print("  Saved! Send me this address.")
                        prev[a] = v
        except KeyboardInterrupt:
            print("\n\nStopped.")

    print("\nDone.")


if __name__ == "__main__":
    import ctypes
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("Run as Administrator!")
        sys.exit(1)
    main()
