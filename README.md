# GEDCOM Browser

A powerful Python tool for browsing and validating genealogical data in GEDCOM format, with strict support for GEDCOM 5.5.5 and compatibility for other versions.

## Features

- **Multi-version Support**
  - Strict GEDCOM 5.5.5 compliance mode
  - Relaxed compatibility mode for GEDCOM 4.0, 5.5.1, and 7.0
  - Validation against version-specific requirements

- **Encoding Support**
  - UTF-8 and UTF-16 with BOM (required for 5.5.5)
  - ASCII and ANSEL (for older versions in relaxed mode)
  - Automatic encoding detection

- **Comprehensive Validation**
  - Structure validation (levels, tags, records)
  - Encoding and character set validation
  - Line format and length validation
  - Header and cross-reference validation

- **Browsing Capabilities**
  - Browse individuals and their details
  - Explore family relationships
  - View events, attributes, and notes
  - Search for specific individuals

## Installation

### Prerequisites

- Python 3.7 or higher

### Setup

```bash
# Clone the repository
git clone https://github.com/username/gedcom-browser.git
cd gedcom-browser

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run the program with a GEDCOM file to list all individuals:

```bash
python main.py path/to/gedcom_file.ged
```

### Validation Only

Validate a GEDCOM file without browsing:

```bash
python main.py path/to/gedcom_file.ged --validate-only
```

### List All Individuals

Explicitly list all individuals in the file:

```bash
python main.py path/to/gedcom_file.ged --list-individuals
```

### View Individual Details

Show detailed information for a specific individual:

```bash
python main.py path/to/gedcom_file.ged --individual @XREF_ID@
```

Where `@XREF_ID@` is the ID of the individual (e.g., `@I123@`).

### Relaxed Mode for Older GEDCOM Versions

Enable relaxed mode to work with GEDCOM versions other than 5.5.5:

```bash
python main.py path/to/gedcom_file.ged --relaxed
```

You can combine the relaxed mode with other options:

```bash
python main.py path/to/gedcom_file.ged --list-individuals --relaxed
python main.py path/to/gedcom_file.ged --individual @XREF_ID@ --relaxed
```

## GEDCOM Support

### Strict Mode (Default)

By default, this tool strictly adheres to the GEDCOM 5.5.5 specification. It will reject files that:

- Use older GEDCOM versions (5.5.1 and earlier) or newer versions
- Lack proper Unicode encoding (UTF-8 or UTF-16)
- Are missing a Byte Order Mark (BOM)
- Have structural errors in the file format
- Exceed line length limits
- Contain empty lines or leading whitespace
- Have invalid headers

### Relaxed Mode

The tool also provides a relaxed mode (with the `--relaxed` flag) that can read and browse:

- GEDCOM 4.0 files
- GEDCOM 5.5.1 files
- GEDCOM 7.0 files
- Files without BOM markers
- Files with various encodings (UTF-8, UTF-16, ASCII, ANSEL approximated with Latin-1)
- Files with minor format deviations

Relaxed mode attempts to handle various encoding types and format quirks found in older GEDCOM files while still extracting valid genealogical data.

## GEDCOM Version Differences

### GEDCOM 4.0
- Simpler structure
- ASCII or ANSEL encoding
- No BOM requirement
- Less structured name and event formatting

### GEDCOM 5.5.1
- Introduces FORM tag
- ASCII or ANSEL encoding
- No BOM requirement
- Structured event handling

### GEDCOM 5.5.5
- Requires UTF-8 or UTF-16 encoding
- Requires BOM
- Strict validation rules
- CONC/CONT limits in headers

### GEDCOM 7.0
- More structured name components (GIVN, SURN)
- Different formatting for some fields
- Primarily uses UTF-8 encoding

## Architecture

The GEDCOM Browser consists of three main components:

1. **GEDCOM Parser (`gedcom_parser.py`)**
   - Parses and validates GEDCOM files
   - Handles multiple versions and encodings
   - Builds a memory model of GEDCOM records

2. **GEDCOM Browser (`gedcom_browser.py`)**
   - Provides high-level access to GEDCOM data
   - Extracts individuals, families, events, and attributes
   - Forms relationships between records

3. **CLI Interface (`main.py`)**
   - Command-line interface
   - Handles user arguments
   - Displays formatted output

## Development

### Project Structure

```
gedcom-browser/
├── gedcom_parser.py     # Core GEDCOM parsing and validation
├── gedcom_browser.py    # Higher-level browsing functionality
├── main.py              # CLI interface and command handling
├── requirements.txt     # Project dependencies
├── setup.py             # Package setup
├── tests/               # Test suite
│   ├── __init__.py
│   ├── test_gedcom_parser.py
│   └── test_gedcom_browser.py
└── test_files/          # Sample GEDCOM files for testing
    ├── valid_simple.ged
    ├── valid_with_notes.ged
    └── valid_complex.ged
```

### Running Tests

To run all tests:

```bash
pytest
```

To run a specific test file:

```bash
pytest tests/test_gedcom_parser.py
```

To run a specific test:

```bash
pytest tests/test_gedcom_parser.py::test_function_name
```

### Development Commands

```bash
# Run linting
flake8 .

# Run type checking
mypy .

# Run pytest with coverage
pytest --cov=.
```

## GEDCOM 5.5.5 Specification

For more information about the GEDCOM 5.5.5 specification, visit:
https://www.gedcom.org/gedcom.html

## Extending the Browser

To add new functionality:

1. **New Record Types**: Add parsing in `gedcom_parser.py` and accessor methods in `gedcom_browser.py`
2. **New Commands**: Update the argument parser and command handling in `main.py`
3. **New Output Formats**: Modify the display functions in `main.py`

## License

See the LICENSE file for details.