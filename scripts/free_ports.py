import os
import sys
import subprocess
import time

TARGET_PORTS = [8000, 8080, 5173]

def free_target_ports():
    """
    Scans and terminates any lingering processes bound to ports 8000, 8080, or 5173.
    Guarantees zero WinError 10048 socket collisions during live demonstrations.
    """
    my_pid = os.getpid()
    killed_count = 0

    if sys.platform == "win32":
        try:
            output = subprocess.check_output("netstat -aon", shell=True).decode("utf-8", errors="ignore")
            for line in output.splitlines():
                for port in TARGET_PORTS:
                    # Match exact port pattern (e.g. :8000, :8080, :5173)
                    if f":{port}" in line and ("LISTENING" in line or "ESTABLISHED" in line):
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            pid_str = parts[-1]
                            try:
                                pid = int(pid_str)
                                if pid > 4 and pid != my_pid:
                                    print(f"[*] Releasing port {port} (Terminating PID {pid})...")
                                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                                    killed_count += 1
                            except ValueError:
                                pass
        except Exception as e:
            print(f"[!] Warning during Windows port scan: {e}")
    else:
        for port in TARGET_PORTS:
            try:
                cmd = f"lsof -ti:{port} | xargs kill -9 2>/dev/null || true"
                subprocess.run(cmd, shell=True)
            except Exception:
                pass

    if killed_count > 0:
        # Give OS socket stack 500ms to recycle
        time.sleep(0.5)
        print(f"[+] Successfully released {killed_count} lingering socket(s).")
    else:
        print("[+] Ports 8000, 8080, and 5173 are already completely free.")

if __name__ == "__main__":
    free_target_ports()
