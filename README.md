**Version:** 1.0  
**Credits:** Galeno Garbe

## Overview

This project is a Python program that searches for a prime number with a specified digit count. It is designed to efficiently handle very large numbers by using the **gmpy2** library for fast arbitrary-precision arithmetic and parallel processing via Python’s built-in `multiprocessing` module. The program logs performance data (such as attempts, time, numbers per second, and CPU usage) into a JSON file (`prime_log.json`) and compares the current run against the best historical performance.

## Features

- **Efficient Primality Testing:** Uses `gmpy2.is_prime` for fast and reliable tests on huge numbers.
- **Parallel Processing:** Distributes the workload across multiple CPU cores.
- **Performance Logging:** Saves each test's performance data and compares the current test with the historical best.
- **User-Friendly Output:** Displays results in a formatted table with three columns: _Current_, _Best_, and _Variation (%)_. Percentage variations are colored green when positive (indicating an improvement) and red when negative (indicating worse performance).
- **System Information:** Shows summarized system details (computer name, processor, threads, and total memory) of the best test.
- **Customizable Digit Count:** Accepts the desired digit count as a command-line parameter or prompts the user interactively.

## Prerequisites

### Python

- **Python 3.7 or higher** is required. You can download the latest version from the [official Python website](https://www.python.org/downloads/).

### Required Python Packages

This project depends on the following Python libraries:

- **gmpy2** – For fast arbitrary-precision arithmetic.
- **psutil** – For obtaining system resource metrics.
- **colorama** – For colored output (used only for percentage variation values).

Other modules used (such as `multiprocessing`, `argparse`, and `platform`) are part of the Python standard library.

### Installation Steps

1. **Install Python 3:**

   - **Windows/Mac/Linux:** Download and install Python from [python.org](https://www.python.org/downloads/).

2. **Create a Virtual Environment (Recommended):**

   Open your terminal (or command prompt) and run:
   ```bash
   python3 -m venv venv
   ```
   Then activate the virtual environment:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

3. **Install Required Packages:**

   You can install all dependencies using pip. Create a file named `requirements.txt` with the following content:
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

4. **Note on Python 3.11:**

   If you are using Python 3.11 or later, the conversion of large integers to strings is now limited by default. The program includes a workaround using `sys.set_int_max_str_digits()`. This is set in the code as follows:
   ```python
   import sys
   if hasattr(sys, "set_int_max_str_digits"):
       sys.set_int_max_str_digits(10000)
   ```
   You may adjust this value if you are working with extremely large numbers.

## Usage

Run the program using the standard Python 3 interpreter:

```bash
python3 gpt_primo.py [digits]
```

- **Example:**  
  To search for a prime number with 1000 digits, run:
  ```bash
  python3 gpt_primo.py 1000
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
  
  Finally, a summary line with system information (computer, processor, threads, and total memory) from the best test is displayed.

## Error Handling

The program includes error handling for:
- Converting large integers to strings (using `sys.set_int_max_str_digits()` to increase the limit).
- File I/O operations (reading and writing the JSON log).
- Exceptions during multiprocessing and arithmetic operations.

## License

[Specify your license here, e.g., MIT License]

---
