# NSE PIT Disclosure Tool

A command-line Python application that automatically fetches, downloads, parses, and converts National Stock Exchange (NSE) Prohibition of Insider Trading (PIT) disclosures into clean, structured Excel (`.xlsx`) and CSV files.

---

## 📋 Table of Contents
- [Prerequisites: Installing Python](#-prerequisites-installing-python)
- [Project Setup](#-project-setup)
  - [Option A: If you received a ZIP file](#option-a-if-you-received-a-zip-file)
  - [Option B: If fetching from GitHub](#option-b-if-fetching-from-github)
  - [Installing Dependencies](#installing-dependencies)
- [How to Use (Commands & Use Cases)](#-how-to-use-commands--use-cases)
  - [1. Download All Available Disclosures](#1-download-all-available-disclosures)
  - [2. Download Disclosures for a Specific Date Range](#2-download-disclosures-for-a-specific-date-range)
  - [3. Clear Cache & Re-download Fresh XML Files](#3-clear-cache--re-download-fresh-xml-files)
  - [4. Combine Date Range with Cache Clearing](#4-combine-date-range-with-cache-clearing)
  - [5. View Help & Available Flags](#5-view-help--available-flags)
- [Output Location](#-output-location)
- [Project Directory Structure](#-project-directory-structure)

---

## ⚙️ Prerequisites: Installing Python

Before running this tool, ensure you have **Python 3.10 or higher** installed on your computer.

1. **Download Python**:
   - Visit [python.org/downloads](https://www.python.org/downloads/) and download the latest version for Windows, macOS, or Linux.
   - *Windows Users*: Make sure to check the box **"Add Python to PATH"** during installation.

2. **Verify Installation**:
   Open a terminal (Command Prompt, PowerShell, or macOS/Linux Terminal) and run:
   ```bash
   python --version
   ```
   *(or `python3 --version` on macOS/Linux)*

---

## 🚀 Project Setup

### Option A: If you received a ZIP file

1. Extract the `.zip` archive to a folder of your choice on your computer.
2. Open your terminal/command prompt and navigate into the extracted directory:
   ```bash
   cd path/to/pit
   ```
3. *(Optional)* If you want to track changes using Git inside this extracted folder, initialize a local Git repository:
   ```bash
   git init
   ```

### Option B: If fetching from GitHub

1. Clone the repository using Git:
   ```bash
   git clone <repository-url>
   ```
2. Navigate into the cloned directory:
   ```bash
   cd pit
   ```

---

### Installing Dependencies

It is recommended to run the project inside a virtual environment to isolate dependencies.

1. **Create a Virtual Environment**:
   ```bash
   # Windows
   python -m venv .venv

   # macOS / Linux
   python3 -m venv .venv
   ```

2. **Activate the Virtual Environment**:
   ```bash
   # Windows (PowerShell)
   \.venv\Scripts\Activate.ps1

   # Windows (Command Prompt)
   \.venv\Scripts\activate.bat

   # macOS / Linux
   source .venv/bin/activate
   ```

3. **Install Requirements**:
   Install the necessary libraries (`requests` and `openpyxl`) via `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🛠️ How to Use (Commands & Use Cases)

All commands are executed through `main.py`.

### 1. Download All Available Disclosures
Fetch the complete set of PIT disclosures currently exposed by the NSE portal.

```bash
python main.py
```
* **Use Case**: Default run when you want to get all existing PIT filings from NSE without any date restrictions.

---

### 2. Download Disclosures for a Specific Date Range
Fetch disclosures filed within a targeted date range (Date format: `DD-MM-YYYY`).

```bash
python main.py --from-date 01-09-2026 --to-date 21-09-2026
```
* **Use Case**: When you only need disclosure data for a specific week, month, or customized date interval (e.g., from September 1, 2026 to September 21, 2026).
* **Note**: Both `--from-date` and `--to-date` must be provided together.

---

### 3. Clear Cache & Re-download Fresh XML Files
Wipe locally stored XBRL `.xml` files in the `cache/` directory and re-download fresh files from NSE servers.

```bash
python main.py --clear-cache
```
* **Use Case**: Use this if files in `cache/` became corrupted, if you suspect missing/updated files on NSE, or if you want a clean sync.

---

### 4. Combine Date Range with Cache Clearing
Combine date range filters while forcing a fresh XML re-download.

```bash
python main.py --from-date 01-09-2026 --to-date 21-09-2026 --clear-cache
```
* **Use Case**: Performing a fresh, uncached sync for a specific historical date range.

---

### 5. View Help & Available Flags
Display the built-in help text explaining command-line arguments.

```bash
python main.py --help
```

---

## 📊 Output Location

After processing completes, formatted reports are automatically saved to the `output/` folder:

* `output/NSE_PIT_Disclosures.xlsx` — Formatted Excel workbook containing:
  * **Main Sheet**: Clean, human-readable fields (Company Name, Symbol, Person Name, Category, Acquisition/Disposal, Shares, Price, Total Value, Transaction Date, Mode, Post-Transaction Holdings, Revision Details).
  * **Source Details Sheet**: Technical URLs, broadcast timestamps, and XBRL metadata.
* `output/NSE_PIT_Disclosures.csv` — CSV format for automated data analysis and database import.

---

## 📂 Project Directory Structure

```text
pit/
├── .gitignore          # Rules for ignoring temp cache, outputs, and environments
├── README.md            # Project guide and usage instructions
├── requirements.txt    # Python package dependencies
├── config.py           # Central settings, URLs, headers, and timeouts
├── main.py             # CLI entry point and execution orchestration
├── nse_client.py       # NSE API interface
├── downloader.py       # Concurrent XML file downloader & caching handler
├── xml_parser.py       # XBRL XML parser & field extraction engine
├── normalizer.py       # Data cleaning, field mapping, and price calculations
├── progress.py         # Terminal progress bar with ETA calculations
└── exporter.py         # Excel (.xlsx) and CSV export formatter
```
