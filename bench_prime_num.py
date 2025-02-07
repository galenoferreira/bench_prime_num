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

# Import Rich for animated output
from rich.live import Live
from rich.text import Text
from rich.console import Console

# Initialize colorama (colors will be used only for percentage variations)
init(autoreset=True)

# Create a Rich Console object
console = Console()

# Constant: natural logarithm of 10
LOG10 = math.log(10)

# ---------------- Utility Functions ----------------

def format_scientific(n, precision=3):
    """
    Formats a large integer in scientific notation without converting it to float.
    For example, for a 1000-digit number with precision=3, returns "1.23e+999".
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
    For metrics where higher is better: ((current - best) / best) * 100.
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

# ---------------- System Information Functions ----------------

def get_system_info():
    """
    Returns a dictionary with a summary of the system information:
      - Computer: computer name
      - Processor: processor description
      - Threads: total number of threads (logical cores)
      - Total Memory (GB): total installed memory in GB
    """
    try:
        uname = platform.uname()
        return {
            "Computer": uname.node,
            "Processor": uname.processor,
            "Threads": psutil.cpu_count(logical=True),
            "Total Memory (GB)": round(psutil.virtual_memory().total / (1024**3), 2)
        }
    except Exception as e:
        return {"Computer": "N/A", "Processor": "N/A", "Threads": "N/A", "Total Memory (GB)": "N/A"}

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
      - System information from the best test.
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
        best["cpu"] = min(e["cpu"] for e in same_digit_entries if "cpu" in e)
        best_entry = min(same_digit_entries, key=lambda e: e.get("elapsed", float('inf')))
        best["prime_scientific"] = best_entry.get("prime_scientific", "N/A")
        best["system_info"] = best_entry.get("system_info", {})
    except Exception as e:
        print(f"Error processing historical metrics: {e}")
        return None
    return best

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

# ---------------- Main Function ----------------

def main(digits_param=None):
    # Print program header
    print("Prime search with specified digit count.\n")
    
    # Get digit count from parameter or prompt user
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

    # Display the requested digit count
    print(f"Digit Count: {digits}\n")
    
    try:
        lower = 10**(digits - 1)
        upper = 10**digits
    except Exception as e:
        print(f"Error computing bounds for digits: {e}")
        return

    # Read historical best metrics for this digit count (if available)
    historical_best = get_best_historical_metrics(digits)
    static_eta = None  # ETA will be calculated once

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
    
    # Set up a spinner animation using Rich
    spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    spinner_index = 0

    start_time = time.time()
    try:
        # Use Rich's Live to update the output with animation below the progress line
        with Live("", refresh_per_second=4, console=console) as live:
            while not found_event.is_set():
                time.sleep(0.5)
                elapsed = time.time() - start_time
                with global_attempts.get_lock():
                    attempts_val = global_attempts.value
                speed = attempts_val / elapsed if elapsed > 0 else 0
                cpu_percent = psutil.cpu_percent(interval=0.0)
                if static_eta is None and speed > 0:
                    try:
                        if digits > 1:
                            p_val = 30 / (8 * (digits - 1) * LOG10)
                        else:
                            p_val = 0.5
                        expected_total_attempts = 1 / p_val
                        remaining_attempts = max(expected_total_attempts - attempts_val, 0)
                        static_eta = remaining_attempts / speed
                    except Exception as e:
                        static_eta = 0
                eta = static_eta if static_eta is not None else 0
                progress_line = (f"Digit Count: {digits} | Attempts: {attempts_val} | Time: {format_time(elapsed)} | "
                                 f"Numbers/Sec: {speed:.2f} | CPU Usage: {cpu_percent:.2f}% | ETA: {format_time(eta)}")
                # Update spinner
                spinner = spinner_chars[spinner_index]
                spinner_index = (spinner_index + 1) % len(spinner_chars)
                combined_text = Text(progress_line + "\n" + spinner)
                live.update(combined_text)
    except KeyboardInterrupt:
        found_event.set()
        print("\nInterrupted by user.")
    except Exception as e:
        print(f"\nError during progress update: {e}")
        found_event.set()
    
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

    # Clear the live display
    console.clear()

    # Get system info for the current test
    system_info = get_system_info()
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "digits": digits,
        "attempts": final_attempts,
        "elapsed": total_elapsed,
        "speed": final_speed,
        "cpu": cpu_percent,
        "prime": str(prime),
        "prime_scientific": format_scientific(prime, precision=3),
        "system_info": system_info
    }
    
    try:
        log_file = "prime_log.json"
        logs = update_log(entry, log_file)
    except Exception as e:
        print(f"Error updating log: {e}")
        logs = []
    
    if historical_best is None:
        historical_best = {
            "attempts": final_attempts,
            "elapsed": total_elapsed,
            "speed": final_speed,
            "cpu": cpu_percent,
            "prime_scientific": format_scientific(prime, precision=3),
            "system_info": system_info
        }
    
    # Calculate percentage variations for each metric
    var_attempts = compute_variation(final_attempts, historical_best["attempts"], lower_is_better=True)
    var_time = compute_variation(total_elapsed, historical_best["elapsed"], lower_is_better=True)
    var_speed = compute_variation(final_speed, historical_best["speed"], lower_is_better=False)
    var_cpu = compute_variation(cpu_percent, historical_best["cpu"], lower_is_better=True)

    # Display the results in a table with Current, Best, and Variation (%) columns
    print("\nResults:")
    header = "{:<15} {:<20} {:<20} {:<15}".format("Label", "Current", "Best", "Variation (%)")
    print(header)
    print("-" * len(header))
    print("{:<15} {:<20} {:<20} {:<15}".format("Attempts", str(final_attempts), str(historical_best["attempts"]), format_variation(var_attempts)))
    print("{:<15} {:<20} {:<20} {:<15}".format("Time", format_time(total_elapsed), format_time(historical_best["elapsed"]), format_variation(var_time)))
    print("{:<15} {:<20} {:<20} {:<15}".format("Numbers/Sec", f"{final_speed:.2f}", f"{historical_best['speed']:.2f}", format_variation(var_speed)))
    print("{:<15} {:<20} {:<20} {:<15}".format("CPU Usage", f"{cpu_percent:.2f}%", f"{historical_best['cpu']:.2f}%", format_variation(var_cpu)))
    print("{:<15} {:<20} {:<20}".format("Prime", format_scientific(prime, precision=3), historical_best["prime_scientific"]))
    
    # Display the system info of the best test in a summarized single line
    best_sys = historical_best.get("system_info", system_info)
    summary_line = "Computer: {} | Processor: {} | Threads: {} | Total Memory (GB): {}".format(
        best_sys.get("Computer", "N/A"),
        best_sys.get("Processor", "N/A"),
        best_sys.get("Threads", "N/A"),
        best_sys.get("Total Memory (GB)", "N/A")
    )
    print("\nSystem Info (Best Test):")
    print(f"Digit Count: {digits} | {summary_line}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prime search with specified digit count")
    # Optional positional argument: if provided, it will be used; otherwise, the user is prompted.
    parser.add_argument("digits", type=int, nargs="?", help="Digit count for the prime")
    args = parser.parse_args()
    try:
        multiprocessing.set_start_method("fork")
    except RuntimeError:
        pass
    try:
        main(digits_param=args.digits)
    except Exception as e:
        print(f"Unexpected error: {e}")

