# Prime Search with Specified Digit Count

## Overview
This script (`prime_search.py`) searches for a prime number with a specified digit count. It leverages `gmpy2` for efficient arbitrary-precision arithmetic and `multiprocessing` to distribute the workload across CPU cores. Performance data is logged in a JSON file, allowing historical comparisons.

An animated spinner (using the `Rich` library) is displayed alongside progress information during processing.

## Features
- **Multi-core processing** for parallelized prime search.
- **Performance tracking**, storing results in `prime_log.json`.
- **Live progress updates** using the `Rich` library.
- **Beep notification** when a new best result is achieved.
- **Formatted time and scientific notation** for large numbers.

## Installation
Ensure you have the required dependencies installed:
```sh
pip install gmpy2 rich colorama psutil
```

## Usage
Run the script with the desired number of digits:
```sh
python3 prime_search.py <digit_count>
```
For example, to search for a prime with 50 digits:
```sh
python3 prime_search.py 50
```

To run multiple iterations (default: 10):
```sh
python3 prime_search.py 50 -r
```

## Example Output
```
Digit Count: 50 | Attempts: 124500 | Time: 02:15.4 | Numbers/Sec: 1523.67 | CPU Usage: 97.2%
Prime Found: 9.87e+49
Performance Ratio: 1.54 ms/attempt
Previous best ratio: 1.62 ms/attempt
New record achieved!
```

## Logging
Each successful search logs the following details in `prime_log.json`:
- `digits`: Number of digits in the prime.
- `attempts`: Number of random candidates tested.
- `elapsed`: Time taken for the search.
- `speed`: Numbers tested per second.
- `cpu`: CPU usage percentage.
- `prime`: The discovered prime number (scientific notation for readability).

View the latest prime found with:
```sh
jq '.[-1].prime' prime_log.json
```

## Performance Metrics
The script compares each run with historical data, highlighting variations in:
- Attempts
- Execution time
- Speed (numbers tested per second)
- CPU utilization
- Prime number found

## Notes
- The method is **probabilistic**: results are likely prime but not guaranteed.
- Uses **wheel factorization** for candidate generation to improve efficiency.
- If interrupted (`Ctrl+C`), the script stops gracefully.
- Uses **scientific notation** for very large numbers.

## License
This project is released under the MIT License.


