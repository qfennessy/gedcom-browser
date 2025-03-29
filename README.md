# GEDCOM Browser

A powerful Python tool for browsing, validating, and anonymizing genealogical data in GEDCOM format, with strict support for GEDCOM 5.5.5 and compatibility for other versions.

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
  
- **Advanced Anonymization**
  - Generate realistic fake names, places, and contact information
  - Preserve gender and relationships
  - Consistent anonymization across multiple files
  - Support for emails, phone numbers, addresses, and URLs

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

The required dependencies include:
- `faker`: Generates realistic fake data for anonymization
- Development dependencies like `pytest`, `pytest-cov`, `flake8`, `mypy`, and `black` for testing and code quality

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

## Generating Test GEDCOM Files

The tool includes a test GEDCOM generator that can create sample files for different GEDCOM versions:

```bash
# Generate a GEDCOM 5.5.5 file with 50 people across 3 generations
python create-test-gedcom.py --start-date 1900-01-01 --end-date 2000-01-01 --num-people 50 --num-generations 3 --v555 --output test_data.ged

# Generate a GEDCOM 4.0 file (for testing older formats)
python create-test-gedcom.py --start-date 1900-01-01 --end-date 2000-01-01 --num-people 20 --num-generations 2 --v40 --output test_40.ged

# Generate a GEDCOM 7.0 file
python create-test-gedcom.py --start-date 1900-01-01 --end-date 2000-01-01 --num-people 30 --num-generations 3 --v70 --output test_70.ged

# Generate a GEDCOM file with Hispanic naming conventions
python create-test-gedcom.py --start-date 1900-01-01 --end-date 2000-01-01 --num-people 50 --num-generations 3 --culture hispanic --output hispanic_families.ged

# Generate a GEDCOM file with Spanish names and conventions
python create-test-gedcom.py --start-date 1900-01-01 --end-date 2000-01-01 --num-people 50 --num-generations 3 --region es_ES --output spanish_families.ged
```

The generator supports the following options:
- `--v40`: GEDCOM 4.0 (ASCII encoding, basic format)
- `--v551`: GEDCOM 5.5.1 (ASCII encoding, with FORM tag) - Default if no version specified
- `--v555`: GEDCOM 5.5.5 (UTF-8 with BOM, stricter validation)
- `--v70`: GEDCOM 7.0 (UTF-8 encoding, latest standard)
- `--culture`: Controls surname inheritance patterns (choices: western, hispanic, asian, nordic)
- `--region`: Sets the locale for name generation (e.g., "es_ES", "en_US", "zh_CN")

Family naming conventions respect cultural patterns:
- Western/Asian: Children typically inherit the father's surname
- Hispanic/Spanish: Children often use both parents' surnames (father-mother)
- Nordic: Traditional patronymic naming (simplified implementation)

Generated files contain realistic individuals with events, attributes, and family relationships. Each file is encoded appropriately for its GEDCOM version.

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

## Anonymizing GEDCOM Files

The GEDCOM Browser includes a powerful anonymization tool to protect personal data while preserving the structure and relationships in genealogical files.

### Basic Anonymization

To anonymize a single GEDCOM file:

```bash
python anonymize_gedcom.py --file path/to/gedcom_file.ged
```

This will create a new file with the suffix `_anonymized` (e.g., `gedcom_file_anonymized.ged`).

### Anonymizing a Directory

To anonymize all GEDCOM files in a directory:

```bash
python anonymize_gedcom.py --directory path/to/directory
```

Add the `--recursive` flag to process subdirectories:

```bash
python anonymize_gedcom.py --directory path/to/directory --recursive
```

### Overwriting Original Files

By default, the anonymizer creates new files. To overwrite the original files:

```bash
python anonymize_gedcom.py --file path/to/gedcom_file.ged --overwrite
```

### Specifying Output Path

For single files, you can specify an output path:

```bash
python anonymize_gedcom.py --file path/to/gedcom_file.ged --output path/to/output.ged
```

### Reproducible Anonymization

Set a random seed for reproducible results:

```bash
python anonymize_gedcom.py --file path/to/gedcom_file.ged --seed 12345
```

### Consistent Anonymization Across Runs

To maintain consistent anonymization mappings across multiple runs:

```bash
python anonymize_gedcom.py --file path/to/gedcom_file.ged --mapping-file mappings.pkl
```

This saves the name mappings to the specified file and loads them for future runs.

### Anonymization Features

The anonymizer preserves:
- GEDCOM structure and record relationships
- Gender-appropriate names (male names replaced with male names, etc.)
- File encodings and Byte Order Marks (BOMs)
- Consistent mapping of original to fake names
- Special tags like GIVN, SURN, PLAC, EMAIL, PHON, ADDR, and WWW

## Architecture

The GEDCOM Browser consists of four main components:

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
   
4. **Anonymizer (`anonymize_gedcom.py`)**
   - Anonymizes personal data in GEDCOM files
   - Generates realistic fake names, places, and contact information
   - Preserves gender, relationships, and file structure

## Development

### Project Structure

```
gedcom-browser/
├── gedcom_parser.py         # Core GEDCOM parsing and validation
├── gedcom_browser.py        # Higher-level browsing functionality
├── main.py                  # CLI interface and command handling
├── anonymize_gedcom.py      # GEDCOM anonymization tool
├── anonymization_mapping.py # Helper for consistent anonymization (optional)
├── create-test-gedcom.py    # Generate test GEDCOM files with multiple versions
├── requirements.txt         # Project dependencies
├── setup.py                 # Package setup
├── ROADMAP.md               # Future development plans
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── test_gedcom_parser.py
│   ├── test_gedcom_browser.py
│   ├── test_anonymizer.py
│   └── test_gedcom_generator.py
└── test_files/              # Sample GEDCOM files for testing
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

# Test anonymization functionality
pytest tests/test_anonymizer.py
```

### Using the Anonymizer as a Library

You can also use the anonymization functionality programmatically in your own scripts:

```python
from anonymize_gedcom import GedcomAnonymizer, anonymize_gedcom_file

# Create an anonymizer with custom settings
anonymizer = GedcomAnonymizer(
    seed=42,
    preserve_structure=True,
    mapping_file="mappings.pkl"
)

# Anonymize a single file
anonymized_file = anonymize_gedcom_file(
    "input.ged",
    "output.ged",
    anonymizer=anonymizer
)

# The GedcomAnonymizer class provides methods to anonymize specific data types:
fake_name = anonymizer.anonymize_given_name("John", gender="M")
fake_surname = anonymizer.anonymize_surname("Smith")
fake_place = anonymizer.anonymize_place("New York, NY")
fake_email = anonymizer.anonymize_email("john@example.com")
```

## GEDCOM 5.5.5 Specification

For more information about the GEDCOM 5.5.5 specification, visit:
https://www.gedcom.org/gedcom.html

## Extending the Browser

To add new functionality:

1. **New Record Types**: Add parsing in `gedcom_parser.py` and accessor methods in `gedcom_browser.py`
2. **New Commands**: Update the argument parser and command handling in `main.py`
3. **New Output Formats**: Modify the display functions in `main.py`
4. **Advanced Anonymization**: Enhance the `GedcomAnonymizer` class in `anonymize_gedcom.py`
5. **Test Data Generation**: Update options in `create-test-gedcom.py` to simulate different GEDCOM versions

See the `ROADMAP.md` file for planned future enhancements.

## License

See the LICENSE file for details.