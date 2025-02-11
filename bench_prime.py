#!/usr/bin/env python3
"""
Prime Search with Specified Digit Count
Version: 1.1
Credits: Galeno Garbe

This program searches for a prime number with a specified digit count.
It uses gmpy2 for fast arbitrary-precision arithmetic and multiprocessing to 
distribute the work across physical CPU cores. Performance data is logged to a JSON file 
and compared against historical best results.

An animated spinner (using the Rich library) is displayed below the progress 
information during processing.
"""

import sys
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
import signal       # (not used for interactive prompt in this version)

from rich.live import Live
from rich.text import Text
from rich.console import Console

# Initialize colorama and create a Rich console
init(autoreset=True)
console = Console()

# Constant: natural logarithm of 10
LOG10 = math.log(10)

# ---------------- Função para tocar som ----------------
def play_beep():
    """
    Toca um beep usando o comando adequado conforme o sistema operacional.
    No macOS utiliza AppleScript; no Linux tenta usar o comando "beep" se estiver disponível,
    caso contrário, imprime o caractere BEL.
    """
    if sys.platform == "darwin":
        os.system('osascript -e "beep"')
        
    elif sys.platform.startswith("linux"):
        # Tenta usar o comando 'beep' se estiver instalado; caso contrário, imprime o caractere BEL.
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
    Formats a time value (in seconds) as MM:SS.D (minutes, seconds and deciseconds)
    for the live progress display.
    """
    try:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        deciseconds = int((seconds - int(seconds)) * 10)
    except Exception as e:
        raise ValueError(f"Error formatting time: {e}")
    return f"{minutes:02d}:{secs:02d}.{deciseconds}"

def format_final_time(seconds):
    """
    For the final summary: if elapsed time is less than 1 second, display in milliseconds;
    otherwise, display in the format MM:SS:CC (minutes, seconds, centiseconds).
    """
    if seconds < 1:
        return f"{seconds * 1000:.3f} ms"
    else:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        centiseconds = int((seconds - int(seconds)) * 100)
        return f"{minutes:02d}:{secs:02d}:{centiseconds:02d}"

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
    Formats the variation value with two decimal places and colors it.
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
    Updates the JSON log file with the new entry.
    """
    logs = []
    try:
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                logs = json.load(f)
    except (json.JSONDecodeError, IOError):
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
    Computes the previous best ratio based on the historical best speed.
    The ratio is defined as (1 / speed) * 1000 (ms/attempt).
    Returns None if no valid speed is found.
    """
    if not os.path.exists(log_file):
        return None
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            logs = json.load(f)
        speeds = [entry["speed"] for entry in logs 
                  if entry.get("digits") == digits and entry.get("speed", 0) > 0]
        if speeds:
            best_speed = max(speeds)  # Assuming "best" speed means the highest speed.
            return (1 / best_speed) * 1000
        else:
            return None
    except Exception as e:
        return None
# ---------------------------------------------------------

# ---------------- Multiprocessing Worker ----------------
def worker(lower, upper, global_attempts, found_event, result_dict, batch_size):
    """
    Worker process: generates random candidates and updates the global counter in batches.
    Uses a local counter to reduce lock contention.
    """
    wheel_offsets = (1, 7, 11, 13, 17, 19, 23, 29)
    local_count = 0
    try:
        while not found_event.is_set():
            candidate = random.randrange(lower, upper)
            local_count += 1
            if local_count >= batch_size:
                with global_attempts.get_lock():
                    global_attempts.value += local_count
                local_count = 0
            if candidate % 30 not in wheel_offsets:
                continue
            if is_probable_prime(candidate):
                with global_attempts.get_lock():
                    global_attempts.value += local_count
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
    Shows:
      - Performance Ratio: (current test ratio in ms/attempt)
      - Previous best ratio: (record value from the log based on best speed)
    If a new record is achieved (current ratio < previous best ratio), the script plays a beep,
    shows "New record achieved!" and stops.
    If not, and if repeat_mode is True, the test is repeated for the specified number of iterations.
    For the final summary, if elapsed time < 1 sec, time is shown in milliseconds;
    otherwise, in MM:SS:CC.
    """
    # Get digit count from parameter or input
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

    # Display algorithm (two lines)
    print("Algorithm used: Random candidate generation with wheel filter optimization")
    print("and gmpy2 probabilistic prime test.\n")

    try:
        lower = 10**(digits - 1)
        upper = 10**digits
    except Exception as e:
        print(f"Error computing bounds for digits: {e}")
        return

    # Historical average speed (not used in display)
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

    # Historical best metrics (if available)
    historical_best = get_best_historical_metrics(digits)

    # Use physical cores to avoid hyperthreading
    physical_cores = psutil.cpu_count(logical=False) or psutil.cpu_count(logical=True)
    num_processes = physical_cores

    # Define batch size = max(1, 10% of digit count)
    batch_size = max(1, int(0.1 * digits))

    manager = multiprocessing.Manager()
    result_dict = manager.dict()
    found_event = multiprocessing.Event()
    global_attempts = multiprocessing.Value('l', 0)
    
    # Start worker processes, passing the batch_size to each
    workers = []
    for _ in range(num_processes):
        try:
            p = multiprocessing.Process(target=worker,
                                        args=(lower, upper, global_attempts, found_event, result_dict, batch_size))
            p.start()
            workers.append(p)
        except Exception as e:
            print(f"Error starting a worker process: {e}")

    start_time = time.time()
    try:
        # Live progress update (without ETA); double the sleep interval for updates (1.0 sec)
        with Live("", refresh_per_second=4, console=console) as live:
            while not found_event.is_set():
                time.sleep(1.0)
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

    # Compute current performance ratio in ms/attempt
    current_ratio_ms = (total_elapsed / final_attempts) * 1000
    # Compute previous best ratio using the best speed from historical metrics (1 / best speed * 1000)
    if historical_best is not None and "speed" in historical_best and historical_best["speed"] > 0:
        previous_best_ratio_ms = (1 / historical_best["speed"]) * 1000
    else:
        previous_best_ratio_ms = current_ratio_ms

    print("\nResults:")
    header = "{:<15} {:<20} {:<20} {:<15}".format("Label", "Current", "Best", "Variation (%)")
    print(header)
    print("-" * len(header))
    print("{:<15} {:<20} {:<20} {:<15}".format("Attempts", str(final_attempts),
          str(historical_best["attempts"]) if historical_best else str(final_attempts),
          format_variation(compute_variation(final_attempts, historical_best["attempts"]) if historical_best else 0)))
    print("{:<15} {:<20} {:<20} {:<15}".format("Time", format_final_time(total_elapsed),
          format_final_time(historical_best["elapsed"]) if historical_best else format_final_time(total_elapsed),
          format_variation(compute_variation(total_elapsed, historical_best["elapsed"]) if historical_best else 0)))
    print("{:<15} {:<20} {:<20} {:<15}".format("Numbers/Sec", f"{final_speed:.2f}",
          f"{historical_best['speed']:.2f}" if historical_best else f"{final_speed:.2f}",
          format_variation(compute_variation(final_speed, historical_best["speed"], lower_is_better=False) if historical_best else 0)))
    print("{:<15} {:<20} {:<20} {:<15}".format("CPU Usage", f"{cpu_percent:.2f}%",
          f"{historical_best['cpu']:.2f}%" if historical_best and "cpu" in historical_best else f"{cpu_percent:.2f}%",
          format_variation(compute_variation(cpu_percent, historical_best["cpu"]) if historical_best and "cpu" in historical_best else 0)))
    print("{:<15} {:<20}".format("Prime Found", f"\033[1m{format_scientific(prime, precision=3)}\033[0m"))
    
    print(f"\nPerformance Ratio: {current_ratio_ms:.3f} ms/attempt")
    print(f"Previous best ratio: {previous_best_ratio_ms:.3f} ms/attempt")
    
    # If the new record is achieved (current ratio < previous best), play the beep and stop.
    if current_ratio_ms < previous_best_ratio_ms:
        play_beep()
        print("\nNew record achieved!")
        print("\nTo see full number type: jq '.[-1].prime' prime_log.json")
        sys.exit(0)
    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prime search with specified digit count")
    parser.add_argument("digits", type=int, nargs="?", help="Digit count for the prime")
    parser.add_argument("-r", "--repeat", type=int, nargs="?", const=10,
                        help="Repeat tests for the specified number of iterations (default 10)")
    args = parser.parse_args()
    try:
        multiprocessing.set_start_method("fork")
    except RuntimeError:
        pass

    try:
        if args.repeat is not None:
            for i in range(args.repeat):
                print(f"\n--- Test iteration {i+1} of {args.repeat} ---\n")
                main(digits_param=args.digits, repeat_mode=True)
                print("\nRepeating test...\n")
                time.sleep(2)  # doubled sleep interval between iterations
        else:
            main(digits_param=args.digits, repeat_mode=False)
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Exiting gracefully.")
        sys.exit(0)

