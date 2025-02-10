# Prime Search with Specified Digit Count

**Version:** 1.2  
**Credits:** Galeno Garbe

## Overview

This project is a Python program that searches for a prime number with a specified digit count. The program is designed to efficiently work with very large numbers by leveraging:
- **gmpy2** for fast arbitrary-precision arithmetic,
- **multiprocessing** to distribute the workload across multiple CPU cores, and
- **Rich** to display an animated spinner during processing.

Performance data such as the number of attempts, elapsed time, numbers per second, and CPU usage are logged to a JSON file (`prime_log.json`). The program also compares the current run's performance with the best historical results and displays these comparisons in a formatted table. Additionally, system information from the best test is shown in a summarized format.

## Features

- **Dynamic Algorithm Selection:**  
  - For numbers with up to 300 digits, the program uses `gmpy2` for primality testing.
  - For numbers with more than 300 digits, the program switches to a Miller-Rabin test.
  - The chosen algorithm is recorded and displayed.

- **Parallel Processing:**  
  The workload is distributed across all available CPU cores using Python's `multiprocessing` module.

- **Real-Time Progress Display:**  
  A progress line is updated in real time showing:
  - Digit Count
  - Attempts
  - Time elapsed
  - Numbers tested per second
  - CPU usage
  - Estimated time of arrival (ETA)  
  An animated spinner (using the Rich library) is displayed below the progress information.

- **Performance Logging & Comparison:**  
  All performance data is logged in a JSON file. At the end of the run, a summary table compares:
  - The current run’s metrics (Current)
  - The best historical metrics (Best)
  - The percentage variation between them (Variation %), where improvements (positive values) are shown in green and regressions (negative values) in red.

- **System Information:**  
  The system information (computer name, processor, threads, and total memory in GB) of the best test is displayed in a single, summarized line along with the digit count.

## Prerequisites

- **Python 3.11 or later** (recommended)
- **Required Python packages:**
  - `gmpy2`
  - `psutil`
  - `colorama`
  - `rich`
  
  These packages can be installed via pip.

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://your-repo-url.git
   cd your-repo-directory

