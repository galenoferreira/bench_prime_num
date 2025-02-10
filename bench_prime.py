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
import subprocess  # para garantir que o comando beep seja executado por completo

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

# ---------------- Função para tocar som ----------------
def play_beep():
    """
    Toca um beep usando o comando adequado conforme o sistema operacional.
    No macOS utiliza AppleScript (usando subprocess.run para aguardar a execução);
    no Linux tenta usar o comando "beep" se estiver disponível, caso contrário, imprime o caractere BEL.
    """
    if sys.platform == "darwin":
        # Usa subprocess.run para aguardar a execução completa do som
        subprocess.run(['osascript', '-e', 'beep'], check=True)
    elif sys.platform.startswith("linux"):
        # Tenta usar o comando 'beep' se estiver instalado; caso contrário, imprime o caractere BEL.
        if os.system("command -v beep > /dev/null 2>&1") == 0:
            os.system("beep")
        else:
            print('\a')
    else:
        print('\a')
# --------------------------------------------------------

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
    """
    Executa o teste para o dígito informado e exibe os resultados.
    Retorna True se o teste atual produziu um novo recorde no Performance Ratio,
    ou False caso contrário.
    """
    # Obter contagem de dígitos do parâmetro ou via input
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

    print(f"\n")  # Linha em branco

    try:
        lower = 10**(digits - 1)
        upper = 10**digits
    except Exception as e:
        print(f"Error computing bounds for digits: {e}")
        return False

    # ---------------- NOVA FUNCIONALIDADE: Cálculo da média histórica de "speed" ----------------
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
    # ----------------------------------------------------------------------------------------------

    # Ler métricas históricas para este dígito (se disponível)
    historical_best = get_best_historical_metrics(digits)
    static_eta = None  # cálculo de ETA usando a velocidade atual como fallback

    num_processes = psutil.cpu_count(logical=True)
    manager = multiprocessing.Manager()
    result_dict = manager.dict()
    found_event = multiprocessing.Event()
    global_attempts = multiprocessing.Value('l', 0)
    
    # Iniciar os processos worker
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
        # Utiliza o Live do Rich para atualizar a interface
        with Live("", refresh_per_second=4, console=console) as live:
            while not found_event.is_set():
                time.sleep(0.5)
                elapsed = time.time() - start_time
                with global_attempts.get_lock():
                    attempts_val = global_attempts.value
                speed = attempts_val / elapsed if elapsed > 0 else 0
                cpu_percent = psutil.cpu_percent(interval=0.0)
                # ---------------- Cálculo do ETA usando a média histórica ----------------
                if historical_avg_speed is not None and historical_avg_speed > 0:
                    if digits > 1:
                        p_val = 30 / (8 * (digits - 1) * LOG10)
                    else:
                        p_val = 0.5
                    expected_total_attempts = 1 / p_val
                    remaining_attempts = max(expected_total_attempts - attempts_val, 0)
                    eta = remaining_attempts / historical_avg_speed
                else:
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
                # --------------------------------------------------------------------------------
                progress_line = (f"Digit Count: {digits} | Attempts: {attempts_val} | Time: {format_time(elapsed)} | "
                                 f"Numbers/Sec: {speed:.2f} | CPU Usage: {cpu_percent:.2f}% | ETA: {format_time(eta)}")
                live.update(Text(progress_line, style="bold"))
    except KeyboardInterrupt:
        found_event.set()
        print("\nInterrupted by user.")
    except Exception as e:
        print(f"\nError during progress update: {e}")
        found_event.set()
    
    # Aguarda a finalização de todos os processos worker
    for p in workers:
        p.join()
    
    total_elapsed = time.time() - start_time
    with global_attempts.get_lock():
        final_attempts = global_attempts.value
    final_speed = final_attempts / total_elapsed if total_elapsed > 0 else 0
    prime = result_dict.get('prime', None)
    if prime is None:
        print("No prime found.")
        return False

    # Obter informações do sistema para o teste atual
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
    
    # Calcular as variações percentuais para cada métrica
    var_attempts = compute_variation(final_attempts, historical_best["attempts"], lower_is_better=True)
    var_time = compute_variation(total_elapsed, historical_best["elapsed"], lower_is_better=True)
    var_speed = compute_variation(final_speed, historical_best["speed"], lower_is_better=False)
    var_cpu = compute_variation(cpu_percent, historical_best["cpu"], lower_is_better=True)

    # Exibir os resultados em uma tabela
    print("\nResults:")
    header = "{:<15} {:<20} {:<20} {:<15}".format("Label", "Current", "Best", "Variation (%)")
    print(header)
    print("-" * len(header))
    print("{:<15} {:<20} {:<20} {:<15}".format("Attempts", str(final_attempts), str(historical_best["attempts"]), format_variation(var_attempts)))
    print("{:<15} {:<20} {:<20} {:<15}".format("Time", format_time(total_elapsed), format_time(historical_best["elapsed"]), format_variation(var_time)))
    print("{:<15} {:<20} {:<20} {:<15}".format("Numbers/Sec", f"{final_speed:.2f}", f"{historical_best['speed']:.2f}", format_variation(var_speed)))
    print("{:<15} {:<20} {:<20} {:<15}".format("CPU Usage", f"{cpu_percent:.2f}%", f"{historical_best['cpu']:.2f}%", format_variation(var_cpu)))
    print("{:<15} {:<20} {:<20}".format("Prime", format_scientific(prime, precision=3), historical_best["prime_scientific"]))
    
    # ------------- NOVA FUNCIONALIDADE: Exibição do Performance Ratio -------------
    # Calcula o Performance Ratio (tempo/attempt) em milissegundos para o teste atual
    current_ratio = total_elapsed / final_attempts if final_attempts else 0
    current_ratio_ms = current_ratio * 1000

    # Filtra o log para obter o melhor índice anterior (excluindo o registro atual)
    current_ts = entry["timestamp"]
    previous_best_ratio = None
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                all_logs = json.load(f)
            previous_entries = [
                e for e in all_logs 
                if e.get("digits") == digits and e.get("timestamp") != current_ts and e.get("attempts", 0) > 0
            ]
            if previous_entries:
                ratios = [e["elapsed"] / e["attempts"] for e in previous_entries]
                previous_best_ratio = min(ratios)
        except Exception as e:
            previous_best_ratio = None

    previous_best_ratio_ms = previous_best_ratio * 1000 if previous_best_ratio is not None else None

    print("")  # Linha em branco
    # Exibe o Performance Ratio atual (em negrito)
    print("\033[1mPerformance Ratio: {:.3f} ms/attempt\033[0m".format(current_ratio_ms))
    new_record = False
    # Se existir um registro anterior, mostra também o melhor índice anterior e toca um som se for novo recorde.
    if previous_best_ratio_ms is not None:
        if current_ratio_ms < previous_best_ratio_ms:
            print("\033[1mNew record! Previous best Performance Ratio: {:.3f} ms/attempt\033[0m".format(previous_best_ratio_ms))
            play_beep()
            new_record = True
        else:
            print("Best Performance Ratio: {:.3f} ms/attempt".format(previous_best_ratio_ms))
    else:
        # Se não houver registro anterior, consideramos o resultado como recorde.
        new_record = True
    # ----------------------------------------------------------------------------

    # Exibir as informações do sistema do melhor teste
    best_sys = historical_best.get("system_info", system_info)
    summary_line = "Computer: {} | Processor: {} | Threads: {} | Total Memory (GB): {}".format(
        best_sys.get("Computer", "N/A"),
        best_sys.get("Processor", "N/A"),
        best_sys.get("Threads", "N/A"),
        best_sys.get("Total Memory (GB)", "N/A")
    )
    print("\nSystem Info (Best Test):")
    print(f"Digit Count: {digits} | {summary_line}")

    return new_record

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prime search with specified digit count")
    # Parâmetro posicional para os dígitos
    parser.add_argument("digits", type=int, nargs="?", help="Digit count for the prime")
    # Novo parâmetro opcional "-r" para repetir os testes até obter um novo recorde
    parser.add_argument("-r", "--repeat", action="store_true", help="Repeat tests until a better Performance Ratio is obtained")
    args = parser.parse_args()
    try:
        multiprocessing.set_start_method("fork")
    except RuntimeError:
        pass

    if args.repeat:
        new_record = False
        while not new_record:
            new_record = main(digits_param=args.digits)
            if not new_record:
                print("\nNo new record achieved. Repeating test...\n")
                time.sleep(1)  # pequena pausa antes de repetir
    else:
        main(digits_param=args.digits)

