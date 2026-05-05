# CSE321 PA1: B-tree Index Structures

This repository contains a from-scratch Python implementation of three index
structures:

- B-tree
- B+ tree
- B* tree

The project uses `student.csv`, which contains 100,000 student records. The
index key is `Student ID`, and the RID is the array index of the record after
loading the CSV file into memory.

## Environment

- Language: Python
- Tested Python version: Python 3.14.3
- Required dependencies for the core experiments: none

Only the Python standard library is required to run the tree implementations,
validation script, and benchmark experiments.

## Core files

```text
README.md
student.csv
src/main.py
src/btree.py
src/bplustree.py
src/bstar_tree.py
src/record_store.py
src/student_record.py
src/measure_time.py
src/additional_experiments.py
src/full_dataset_check.py
```

## How to Run

Run all commands from the repository root.

### 1. Basic sample run

```bash
python3 src/main.py
```

This loads the dataset, inserts sample records into the three trees, and prints
basic search/delete results.

### 2. Correctness check

```bash
python3 src/full_dataset_check.py
```

This builds all three trees using the full dataset and validates:

- random point searches
- B+ tree range query correctness
- sample deletions
- basic structural integrity after deletion

### 3. Main benchmark experiment

```bash
python3 src/measure_time.py
```

Default settings:

```text
orders d: 3, 5, 10
point search keys: 10,000
deleted keys: 2,000
trials: 3
random seed: 321
output directory: results
```

This experiment measures:

- insertion time
- point search mean time
- range query time
- deletion time
- node utilization
- split count
- B* redistribution and 2-to-3 split counts

The script prints the results to the terminal and writes CSV/SVG result files to
the `results/` directory.

### 4. Additional experiments

```bash
python3 src/additional_experiments.py
```

This runs two additional experiments:

1. Insertion order sensitivity
   - random order
   - ascending order
   - descending order

2. Range query selectivity
   - 0.1%, 1%, 5%, 10%, and 50% ranges

The script prints summary tables to the terminal and writes CSV result files to
the `results/` directory.

## Useful Options

You can change benchmark settings from the command line.

Example:

```bash
python3 src/measure_time.py --orders 3 5 10 --search-count 10000 --delete-count 2000 --trials 3
```

Example for a shorter smoke test:

```bash
python3 src/measure_time.py --orders 3 --search-count 100 --delete-count 50 --trials 1
```

Additional experiments also support custom options:

```bash
python3 src/additional_experiments.py --orders 3 5 10 --range-order 10 --trials 3 --range-trials 5
```
