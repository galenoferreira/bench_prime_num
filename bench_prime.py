#!/usr/bin/env python3
"""
Prime Search with Specified Digit Count
Version: 1.1
Credits: Galeno Garbe

This program searches for a prime number with a specified digit count.
It uses gmpy2 for fast arbitrary-precision arithmetic and multiprocessing to 
distribute the work across CPU cores. Performance data is logged to a JSON file 
and compared against historical best results.

An animated spinner (using the Rich library) is displayed below the progress 
information during processing.
"""

import sys
# Increase the maximum number of digits for integer-to-string conversion (Python 3.11+)
if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(10000)

import time
import psutil
import os
import math
import random
import json
import multiprocessing
import argparse
import platform
import gmpy2
from gmpy2 import mpz
from colorama import init, Fore, Style
import subprocess   # to ensure the beep command is fully executed
import signal       # to implement input with timeout (not used in this version)

# Import Rich for animated output
from rich.live import Live
from rich.text import Text
from rich.console import Console

# Initialize colorama
init(autoreset=True)
# Create a Rich Console object
console = Console()

# Constant: natural logarithm of 10
LOG10 = math.log(10)

# ---------------- Function to play beep ----------------
def play_beep():
    """
    Plays a beep using the appropriate command based on the operating system.
    On macOS it uses AppleScript (via subprocess.run to wait for completion);
    on Linux it tries to use the 'beep' command if available, otherwise prints the BEL character.
    """
    if sys.platform == "darwin":
        subprocess.run(['osascript', '-e', 'beep'], check=True)
    elif sys.platform.startswith("linux"):
        if os.system("command -v beep > /dev/null 2>&1") == 0:
            os.system("beep")
        else:
            print('\a')
    else:
        print('\a')
# ---------------------------------------------------------

# ---------------- Utility Functions ----------------
def format_scientific(n, precision=3):
    """
    Formats a large integer in scientific notation without converting it to float.
    For example, a 1000-digit number with precision=3 returns "1.23e+999".
    """
    try:
        s = str(n)
    except Exception as e:
        raise ValueError(f"Error converting integer to string: {e}")
    if len(s) <= precision:
        return s
    exponent = len(s) - 1
    if precision == 1:
        mantissa = s[0]
    else:
        mantissa = s[0] + '.' + s[1:precision]
    return f"{mantissa}e+{exponent}"

def format_time(seconds):
    """
    Formats a time value (in seconds) as mm:ss.d.
    """
    try:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        deciseconds = int((seconds - int(seconds)) * 10)
    except Exception as e:
        raise ValueError(f"Error formatting time: {e}")
    return f"{minutes:02d}:{secs:02d}.{deciseconds}"

def is_probable_prime(n, k=10):
    """
    Tests if 'n' is prime using gmpy2.
    Converts n to mpz and uses gmpy2.is_prime.
    Returns True if the number is (probably) prime.
    """
    try:
        n = mpz(n)
        return gmpy2.is_prime(n) > 0
    except Exception as e:
        raise ValueError(f"Error in is_probable_prime: {e}")

def compute_variation(actual, best, lower_is_better=True):
    """
    Calculates the percentage variation comparing the current value with the best historical value.
    For metrics where lower is better: ((best - current) / best) * 100.
    For metrics where higher is better: ((actual - best) / best) * 100.
    Returns 0 if best is 0.
    """
    try:
        if best == 0:
            return 0.0
        if lower_is_better:
            return ((best - actual) / best) * 100
        else:
            return ((actual - best) / best) * 100
    except Exception as e:
        raise ValueError(f"Error computing variation: {e}")

def format_variation(value):
    """
    Formats the variation value with two decimal places.
    Colors the value green if positive (improvement) and red if negative (worse).
    """
    try:
        formatted = f"{value:.2f}"
    except Exception as e:
        formatted = "0.00"
    if value > 0:
        return f"{Fore.GREEN}{formatted}{Style.RESET_ALL}"
    elif value < 0:
        return f"{Fore.RED}{formatted}{Style.RESET_ALL}"
    else:
        return formatted
# ---------------------------------------------------------

# ---------------- Log Handling Functions ----------------
def update_log(entry, log_file="prime_log.json"):
    """
    Updates the log (JSON file) with the given entry.
    If the file exists, it loads the history, appends the new entry, and writes it back.
    """
    logs = []
    try:
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                logs = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logs = []
    except Exception as e:
        print(f"Error reading log file: {e}")
        logs = []
    try:
        logs.append(entry)
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        print(f"Error updating log file: {e}")
    return logs

def get_best_historical_metrics(digits, log_file="prime_log.json"):
    """
    Reads the log file and filters entries with the same digit count.
    Returns a dictionary with the best historical values for:
      - Attempts (minimum)
      - Time (minimum)
      - Numbers/Sec (maximum)
      - CPU Usage (minimum)
      - Prime (in scientific notation) from the test with the lowest time.
    Returns None if no records exist.
    """
    if not os.path.exists(log_file):
        return None
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            logs = json.load(f)
    except Exception as e:
        print(f"Error reading log file: {e}")
        return None
    same_digit_entries = [e for e in logs if e.get("digits") == digits]
    if not same_digit_entries:
        return None
    try:
        best = {}
        best["attempts"] = min(e["attempts"] for e in same_digit_entries if "attempts" in e)
        best["elapsed"] = min(e["elapsed"] for e in same_digit_entries if "elapsed" in e)
        best["speed"] = max(e["speed"] for e in same_digit_entries if "speed" in e)
        best_entry = min(same_digit_entries, key=lambda e: e.get("elapsed", float('inf')))
        best["prime_scientific"] = best_entry.get("prime_scientific", "N/A")
    except Exception as e:
        print(f"Error processing historical metrics: {e}")
        return None
    return best

def get_previous_best_ratio(digits, log_file="prime_log.json"):
    """
    Scans the log file for entries with the given digit count and computes the minimal
    Performance Ratio (elapsed/attempts in ms). Returns None if no entries are found.
    """
    if not os.path.exists(log_file):
        return None
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            logs = json.load(f)
        ratios = [e["elapsed"]/e["attempts"] for e in logs 
                  if e.get("digits") == digits and e.get("attempts", 0) > 0]
        if ratios:
            return min(ratios)*1000
        else:
            return None
    except Exception as e:
        return None
# ---------------------------------------------------------

# ---------------- Multiprocessing Worker ----------------
def worker(lower, upper, global_attempts, found_event, result_dict):
    """
    Function executed by each process:
      - Generates random candidates in the interval [lower, upper) using a simple wheel filter.
      - Updates the global counter for each candidate generated.
      - Tests for primality (using gmpy2) and, if a prime is found, stores the result.
    """
    wheel_offsets = (1, 7, 11, 13, 17, 19, 23, 29)
    try:
        while not found_event.is_set():
            candidate = random.randrange(lower, upper)
            with global_attempts.get_lock():
                global_attempts.value += 1
            if candidate % 30 not in wheel_offsets:
                continue
            if is_probable_prime(candidate):
                with global_attempts.get_lock():
                    result_dict['attempts'] = global_attempts.value
                result_dict['prime'] = candidate
                found_event.set()
                break
    except Exception as e:
        print(f"Error in worker process: {e}")
# ---------------------------------------------------------

# ---------------- Main Function ----------------
def main(digits_param=None, repeat_mode=False, repeat_count=10):
    """
    Executes the test for the given digit count and displays the results.
    Also shows:
      - Performance Ratio: (current test ratio in ms/attempt)
      - Previous best ratio: (record value from the log, if available)
    If repeat_mode is True (via -r), the test is repeated for the specified number of times (repeat_count).
    """
    # Get digit count either from parameter or via input
    if digits_param is None:
        while True:
            try:
                digits = int(input("Digit Count: "))
                if digits < 1:
                    print("Enter a positive integer.")
                    continue
                break
            except ValueError:
                print("Invalid input. Please enter an integer.")
    else:
        digits = digits_param

    print("\n")  # Blank line

    # Display the algorithm (in two lines)
    print("Algorithm used: Random candidate generation with wheel filter optimization")
    print("and gmpy2 probabilistic prime test.\n")

    try:
        lower = 10**(digits - 1)
        upper = 10**digits
    except Exception as e:
        print(f"Error computing bounds for digits: {e}")
        return

    # Calculate historical average speed (not displayed)
    historical_avg_speed = None
    log_file = "prime_log.json"
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                logs = json.load(f)
            relevant_entries = [entry for entry in logs if entry.get("digits") == digits and "speed" in entry]
            if relevant_entries:
                historical_avg_speed = sum(entry["speed"] for entry in relevant_entries) / len(relevant_entries)
        except Exception as e:
            historical_avg_speed = None

    # Get historical best metrics (if available)
    historical_best = get_best_historical_metrics(digits)

    num_processes = psutil.cpu_count(logical=True)
    manager = multiprocessing.Manager()
    result_dict = manager.dict()
    found_event = multiprocessing.Event()
    global_attempts = multiprocessing.Value('l', 0)
    
    # Start worker processes
    workers = []
    for _ in range(num_processes):
        try:
            p = multiprocessing.Process(target=worker,
                                        args=(lower, upper, global_attempts, found_event, result_dict))
            p.start()
            workers.append(p)
        except Exception as e:
            print(f"Error starting a worker process: {e}")

    start_time = time.time()
    try:
        # Update the interface (without ETA)
        with Live("", refresh_per_second=4, console=console) as live:
            while not found_event.is_set():
                time.sleep(0.5)
                elapsed = time.time() - start_time
                with global_attempts.get_lock():
                    attempts_val = global_attempts.value
                speed = attempts_val / elapsed if elapsed > 0 else 0
                cpu_percent = psutil.cpu_percent(interval=0.0)
                progress_line = (f"Digit Count: {digits} | Attempts: {attempts_val} | Time: {format_time(elapsed)} | "
                                 f"Numbers/Sec: {speed:.2f} | CPU Usage: {cpu_percent:.2f}%")
                live.update(Text(progress_line, style="bold"))
    except KeyboardInterrupt:
        found_event.set()
        print("\nInterrupted by user.")
        return
    except Exception as e:
        print(f"\nError during progress update: {e}")
        found_event.set()
        return
    
    # Wait for all worker processes to finish
    for p in workers:
        p.join()
    
    total_elapsed = time.time() - start_time
    with global_attempts.get_lock():
        final_attempts = global_attempts.value
    final_speed = final_attempts / total_elapsed if total_elapsed > 0 else 0
    prime = result_dict.get('prime', None)
    if prime is None:
        print("No prime found.")
        return

    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "digits": digits,
        "attempts": final_attempts,
        "elapsed": total_elapsed,
        "speed": final_speed,
        "cpu": cpu_percent,
        "prime": str(prime),
        "prime_scientific": format_scientific(prime, precision=3)
    }
    
    try:
        update_log(entry, log_file)
    except Exception as e:
        print(f"Error updating log: {e}")
    
    # Compute current performance ratio (ms/attempt)
    current_ratio_ms = (total_elapsed / final_attempts) * 1000
    # Get previous best ratio from log
    previous_best_ratio_ms = get_previous_best_ratio(digits, log_file)
    if previous_best_ratio_ms is None:
        previous_best_ratio_ms = current_ratio_ms

    # Display final results
    print("\nResults:")
    header = "{:<15} {:<20} {:<20} {:<15}".format("Label", "Current", "Best", "Variation (%)")
    print(header)
    print("-" * len(header))
    print("{:<15} {:<20} {:<20} {:<15}".format("Attempts", str(final_attempts),
          str(historical_best["attempts"]) if historical_best else str(final_attempts),
          format_variation(compute_variation(final_attempts, historical_best["attempts"]) if historical_best else 0)))
    print("{:<15} {:<20} {:<20} {:<15}".format("Time", format_time(total_elapsed),
          format_time(historical_best["elapsed"]) if historical_best else format_time(total_elapsed),
          format_variation(compute_variation(total_elapsed, historical_best["elapsed"]) if historical_best else 0)))
    print("{:<15} {:<20} {:<20} {:<15}".format("Numbers/Sec", f"{final_speed:.2f}",
          f"{historical_best['speed']:.2f}" if historical_best else f"{final_speed:.2f}",
          format_variation(compute_variation(final_speed, historical_best["speed"], lower_is_better=False) if historical_best else 0)))
    print("{:<15} {:<20} {:<20} {:<15}".format("CPU Usage", f"{cpu_percent:.2f}%",
          f"{historical_best['cpu']:.2f}%" if historical_best and "cpu" in historical_best else f"{cpu_percent:.2f}%",
          format_variation(compute_variation(cpu_percent, historical_best["cpu"]) if historical_best and "cpu" in historical_best else 0)))
    # Display "Prime Found" in bold
    print("{:<15} {:<20}".format("Prime Found", f"\033[1m{format_scientific(prime, precision=3)}\033[0m"))
    
    print(f"\nPerformance Ratio: {current_ratio_ms:.3f} ms/attempt")
    print(f"Previous best ratio: {previous_best_ratio_ms:.3f} ms/attempt")
    
    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prime search with specified digit count")
    parser.add_argument("digits", type=int, nargs="?", help="Digit count for the prime")
    parser.add_argument("-r", "--repeat", type=int, nargs="?", const=10,
                        help="Repeat tests for the specified number of times (default 10)")
    args = parser.parse_args()
    try:
        multiprocessing.set_start_method("fork")
    except RuntimeError:
        pass

    try:
        if args.repeat is not None:
            # Repeat tests for args.repeat times (default 10)
            for i in range(args.repeat):
                print(f"\n--- Test iteration {i+1} of {args.repeat} ---\n")
                main(digits_param=args.digits, repeat_mode=True)
                print("\nRepeating test...\n")
                time.sleep(1)
        else:
            main(digits_param=args.digits, repeat_mode=False)
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Exiting gracefully.")
        sys.exit(0)

