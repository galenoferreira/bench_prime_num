Below is a sample README text in Markdown that you can use on your GitHub repository. It contains all the instructions for using the program, what to download and install, recommended interpreters (with a special recommendation for PyPy3), and detailed usage instructions. Feel free to customize it further as needed.

---

# Prime Search with Specified Digit Count

**Version:** 1.0  
**Credits:** Galeno Garbe

## Overview

This project is a Python program that searches for a prime number with a specified digit count. It is designed to efficiently handle very large numbers by using the **gmpy2** library for fast arbitrary-precision arithmetic and parallel processing (via Python’s built-in `multiprocessing` module). The program logs performance data (such as attempts, time, numbers per second, and CPU usage) into a JSON file (`prime_log.json`) and compares the current run against the best historical performance.

## Features

- **Efficient Primality Testing:** Uses `gmpy2.is_prime` for fast and reliable tests on huge numbers.
- **Parallel Processing:** Distributes the workload across multiple CPU cores.
- **Performance Logging:** Saves each test's performance data and compares the current test with the historical best.
- **User-Friendly Output:** Displays results in a formatted table with three columns: _Current_, _Best_, and _Variation (%)_.
- **System Information:** Shows summarized system details (computer name, processor, threads, and total memory) of the best test.
- **Customizable Digit Count:** Accepts the desired digit count as a command-line parameter or prompts the user interactively.

## Requirements

- **Python 3.7+** (recommended)
- **PyPy3** (recommended for improved performance with pure Python code)
- **gmpy2** – For fast arbitrary-precision arithmetic.
- **psutil** – For obtaining system resource metrics.
- **colorama** – For colored output (used only for percentage variation values).
- Other modules such as `multiprocessing`, `argparse`, and `platform` are part of the standard library.

> **Note:**  
> Python 3.11 introduces a limit on the number of digits when converting integers to strings. The program includes a workaround using `sys.set_int_max_str_digits()`. You may adjust this value if you work with extremely large numbers.

## Installation

### 1. Install PyPy3 (Recommended)

- **Download from Official Site:**  
  Visit [pypy.org](https://www.pypy.org/) and download the appropriate version for your operating system.

- **Using Homebrew (macOS):**
  ```bash
  brew install pypy3
  ```

- **Using apt-get (Debian/Ubuntu):**
  ```bash
  sudo apt-get install pypy3
  ```

### 2. Create a Virtual Environment (Optional but Recommended)

Using PyPy3:
```bash
pypy3 -m venv venv
source venv/bin/activate
```

### 3. Install Required Python Packages

Create a `requirements.txt` file with the following content:
```
gmpy2
psutil
colorama
```
Then run:
```bash
pip install -r requirements.txt
```
Alternatively, install them individually:
```bash
pip install gmpy2 psutil colorama
```

## Usage

Run the program using PyPy3 for best performance:
```bash
pypy3 gpt_primo.py [digits]
```

- **Example:**  
  To search for a prime number with 1000 digits, run:
  ```bash
  pypy3 gpt_primo.py 1000
  ```
- If no digit count is provided as an argument, the program will prompt you to enter it interactively.

## How It Works

- **Candidate Generation:**  
  The program generates random candidates in the interval `[10^(digits-1), 10^digits)` using a simple wheel filter to quickly discard numbers that are obviously composite.

- **Primality Testing:**  
  It uses `gmpy2.is_prime` (with numbers converted to the `mpz` type) to efficiently test whether a candidate is prime.

- **Parallel Processing:**  
  The workload is distributed across multiple CPU cores using Python’s `multiprocessing` module.

- **Performance Logging:**  
  All performance metrics (attempts, elapsed time, numbers per second, CPU usage) are logged to `prime_log.json`. The program reads historical data and compares the current run with the best historical results.

- **Results Display:**  
  At the end of the test, a table is displayed showing:
  - **Label**: Metric name  
  - **Current**: The value from the current test  
  - **Best**: The best historical value  
  - **Variation (%)**: The percentage variation (green for improvement, red for worse)
  
  Finally, a summary line with system information (computer, processor, threads, total memory) from the best test is displayed.

## Error Handling

The program includes error handling for:
- Converting large integers to strings (using `sys.set_int_max_str_digits()` to increase the limit).
- File I/O operations (reading and writing the JSON log).
- Exceptions during multiprocessing and arithmetic operations.

## Recommended Interpreter

For best performance, we recommend using **PyPy3** as it generally runs Python code faster than CPython, especially for code written in pure Python.

## Credits

Developed by **Galeno Garbe**

## License

[Specify your license here, e.g., MIT License]

---

This README provides complete instructions for downloading, installing, and running the program along with all necessary details about dependencies and recommended interpreter usage.
