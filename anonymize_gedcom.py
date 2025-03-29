#!/usr/bin/env python3
"""
GEDCOM Anonymizer
A tool to anonymize personal data in GEDCOM genealogical data files using realistic fake data.
"""
import argparse
import logging
import os
import pickle
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

from faker import Faker

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Initialize Faker
fake = Faker()
# Set seed for reproducibility
random.seed(42)
fake.seed_instance(42)

# Regular expressions for identifying patterns to anonymize
NAME_PATTERN = re.compile(r"^(\d+\s+NAME\s+)(.+)$")
PLAC_PATTERN = re.compile(r"^(\d+\s+PLAC\s+)(.+)$")
GIVN_PATTERN = re.compile(r"^(\d+\s+GIVN\s+)(.+)$")
SURN_PATTERN = re.compile(r"^(\d+\s+SURN\s+)(.+)$")
ADDR_PATTERN = re.compile(r"^(\d+\s+ADDR\s+)(.+)$")
EMAIL_PATTERN = re.compile(r"^(\d+\s+EMAIL\s+)(.+)$")
PHON_PATTERN = re.compile(r"^(\d+\s+PHON\s+)(.+)$")
WWW_PATTERN = re.compile(r"^(\d+\s+WWW\s+)(.+)$")

# Pattern to extract names from GEDCOM NAME field
GEDCOM_NAME_PARTS = re.compile(r"^(.*?)(?:/([^/]+)/)?(.*)$")


class GedcomAnonymizer:
    """Class to handle GEDCOM anonymization with consistent name mapping."""

    def __init__(self, seed=42, preserve_structure=True, mapping_file=None):
        """
        Initialize the anonymizer.

        Args:
            seed: Random seed for reproducibility
            preserve_structure: Whether to preserve family relationships
            mapping_file: Path to load/save name mappings
        """
        self.seed = seed
        self.preserve_structure = preserve_structure
        self.mapping_file = mapping_file

        # Initialize mapping dictionaries
        self.given_name_map = {}
        self.surname_map = {}
        self.place_map = {}
        self.email_map = {}
        self.phone_map = {}
        self.url_map = {}
        self.address_map = {}

        # Set random seed
        random.seed(seed)
        fake.seed_instance(seed)

        # Load existing mappings if provided
        if mapping_file and os.path.exists(mapping_file):
            self.load_mappings(mapping_file)

    def load_mappings(self, mapping_file):
        """Load name mappings from a file to ensure consistency across runs."""
        try:
            with open(mapping_file, "rb") as f:
                mappings = pickle.load(f)
                self.given_name_map = mappings.get("given_name_map", {})
                self.surname_map = mappings.get("surname_map", {})
                self.place_map = mappings.get("place_map", {})
                self.email_map = mappings.get("email_map", {})
                self.phone_map = mappings.get("phone_map", {})
                self.url_map = mappings.get("url_map", {})
                self.address_map = mappings.get("address_map", {})
                logger.info(
                    f"Loaded {len(self.given_name_map)} given names, {len(self.surname_map)} surnames, and {len(self.place_map)} places from {mapping_file}"
                )
        except Exception as e:
            logger.warning(f"Error loading mappings: {e}")

    def save_mappings(self, mapping_file):
        """Save name mappings to a file for consistency across runs."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(mapping_file)), exist_ok=True)
            with open(mapping_file, "wb") as f:
                mappings = {
                    "given_name_map": self.given_name_map,
                    "surname_map": self.surname_map,
                    "place_map": self.place_map,
                    "email_map": self.email_map,
                    "phone_map": self.phone_map,
                    "url_map": self.url_map,
                    "address_map": self.address_map,
                }
                pickle.dump(mappings, f)
                logger.info(f"Saved mappings to {mapping_file}")
        except Exception as e:
            logger.warning(f"Error saving mappings: {e}")

    def anonymize_given_name(self, name, gender=None):
        """
        Anonymize a given name, preserving gender if possible.

        Args:
            name: Original given name
            gender: Optional gender hint (M or F)

        Returns:
            Anonymized given name
        """
        name = name.strip()
        if not name:
            return ""

        # Check if we already have a mapping for this name
        if name in self.given_name_map:
            return self.given_name_map[name]

        # Try to guess gender from the name if not provided
        if gender is None:
            # Use faker to guess gender, defaulting to random
            if random.random() < 0.5:
                gender = "M"
            else:
                gender = "F"

        # Generate a new name based on gender
        if gender == "M":
            fake_name = fake.first_name_male()
        elif gender == "F":
            fake_name = fake.first_name_female()
        else:
            fake_name = fake.first_name()

        # Store the mapping
        self.given_name_map[name] = fake_name
        return fake_name

    def anonymize_surname(self, surname):
        """
        Anonymize a surname consistently.

        Args:
            surname: Original surname

        Returns:
            Anonymized surname
        """
        surname = surname.strip()
        if not surname:
            return ""

        # Check if we already have a mapping for this surname
        if surname in self.surname_map:
            return self.surname_map[surname]

        # Generate a new surname
        fake_surname = fake.last_name()

        # Store the mapping
        self.surname_map[surname] = fake_surname
        return fake_surname

    def anonymize_gedcom_name(self, name_field):
        """
        Anonymize a GEDCOM name field, which typically has the format "Given /Surname/ Suffix".

        Args:
            name_field: Original GEDCOM name field

        Returns:
            Anonymized GEDCOM name field
        """
        # Extract parts from the GEDCOM name
        match = GEDCOM_NAME_PARTS.match(name_field)
        if not match:
            # If no match, treat the whole thing as a given name
            return self.anonymize_given_name(name_field)

        given_name, surname, suffix = match.groups()
        given_name = given_name.strip() if given_name else ""
        surname = surname.strip() if surname else ""
        suffix = suffix.strip() if suffix else ""

        # Anonymize each part if present
        anonymized_given = self.anonymize_given_name(given_name or "")
        anonymized_surname = self.anonymize_surname(surname or "")

        # Reconstruct the name in GEDCOM format
        if surname:
            result = f"{anonymized_given}/{anonymized_surname}/"
            if suffix:
                result += f" {suffix}"
        else:
            result = anonymized_given
            if suffix:
                result += f" {suffix}"

        return result

    def anonymize_place(self, place):
        """
        Anonymize a place name consistently.

        Args:
            place: Original place name

        Returns:
            Anonymized place name
        """
        if not place.strip():
            return ""

        # Check if we already have a mapping for this place
        if place in self.place_map:
            return self.place_map[place]

        # Parse place components (typically comma-separated)
        parts = [part.strip() for part in place.split(",")]

        # Generate appropriate fake place components
        anonymized_parts = []
        for i, part in enumerate(parts):
            if i == 0:  # First component is usually a city/town
                anonymized_parts.append(fake.city())
            elif i == len(parts) - 1:  # Last component is usually a country
                anonymized_parts.append(fake.country())
            elif i == len(parts) - 2:  # Second-to-last is usually a state/province
                anonymized_parts.append(fake.state())
            else:  # Other components could be counties, districts, etc.
                anonymized_parts.append(fake.state())

        # Reconstruct the place name
        anonymized_place = ", ".join(anonymized_parts)

        # Store the mapping
        self.place_map[place] = anonymized_place
        return anonymized_place

    def anonymize_email(self, email):
        """
        Anonymize an email address consistently.

        Args:
            email: Original email address

        Returns:
            Anonymized email address
        """
        if not email.strip():
            return ""

        # Check if we already have a mapping for this email
        if email in self.email_map:
            return self.email_map[email]

        # Generate a new email
        fake_email = fake.email()

        # Store the mapping
        self.email_map[email] = fake_email
        return fake_email

    def anonymize_phone(self, phone):
        """
        Anonymize a phone number consistently.

        Args:
            phone: Original phone number

        Returns:
            Anonymized phone number
        """
        if not phone.strip():
            return ""

        # Check if we already have a mapping for this phone
        if phone in self.phone_map:
            return self.phone_map[phone]

        # Generate a new phone number
        fake_phone = fake.phone_number()

        # Store the mapping
        self.phone_map[phone] = fake_phone
        return fake_phone

    def anonymize_url(self, url):
        """
        Anonymize a URL consistently.

        Args:
            url: Original URL

        Returns:
            Anonymized URL
        """
        if not url.strip():
            return ""

        # Check if we already have a mapping for this URL
        if url in self.url_map:
            return self.url_map[url]

        # Generate a new URL
        fake_url = fake.url()

        # Store the mapping
        self.url_map[url] = fake_url
        return fake_url

    def anonymize_address(self, address):
        """
        Anonymize an address consistently.

        Args:
            address: Original address

        Returns:
            Anonymized address
        """
        if not address.strip():
            return ""

        # Check if we already have a mapping for this address
        if address in self.address_map:
            return self.address_map[address]

        # Generate a new address
        fake_address = fake.address().replace("\n", ", ")

        # Store the mapping
        self.address_map[address] = fake_address
        return fake_address


def detect_file_encoding(file_path):
    """
    Detect the encoding and BOM of a GEDCOM file.

    Args:
        file_path: Path to the GEDCOM file

    Returns:
        Tuple of (encoding, bom_length)
    """
    with open(file_path, "rb") as f:
        bom = f.read(4)

        if bom.startswith(b"\xef\xbb\xbf"):
            return "utf-8", 3
        elif bom.startswith(b"\xff\xfe"):
            return "utf-16-le", 2
        elif bom.startswith(b"\xfe\xff"):
            return "utf-16-be", 2
        else:
            # Try to guess encoding - most GEDCOM files are ASCII, ANSEL, or UTF-8
            return "utf-8", 0


def anonymize_gedcom_file(
    input_file, output_file=None, overwrite=False, anonymizer=None, save_mappings=True
):
    """
    Anonymize a GEDCOM file by replacing personal data with fake information.

    Args:
        input_file: Path to the input GEDCOM file
        output_file: Path to the output GEDCOM file (optional)
        overwrite: Whether to overwrite the input file
        anonymizer: GedcomAnonymizer instance to use
        save_mappings: Whether to save name mappings

    Returns:
        Path to the anonymized file
    """
    if anonymizer is None:
        anonymizer = GedcomAnonymizer()

    if output_file is None:
        if overwrite:
            output_file = input_file
        else:
            # Create a new filename with _anonymized suffix
            input_path = Path(input_file)
            output_file = str(input_path.with_stem(f"{input_path.stem}_anonymized"))

    # Detect encoding
    encoding, bom_length = detect_file_encoding(input_file)
    logger.info(
        f"Detected encoding: {encoding}"
        + (f" with BOM ({bom_length} bytes)" if bom_length > 0 else "")
    )

    # Read the file content, skipping the BOM
    content = []
    with open(input_file, "rb") as f:
        if bom_length > 0:
            f.seek(bom_length)

        # Read and decode using the detected encoding
        try:
            file_content = f.read().decode(encoding)
            lines = file_content.splitlines()
            logger.info(f"Read {len(lines)} lines from {input_file}")
            content = lines
        except UnicodeDecodeError:
            # If we failed with the detected encoding, try a fallback
            logger.warning(
                f"Failed to decode with {encoding}, trying fallback encodings"
            )
            for fallback_encoding in ["utf-8", "latin-1", "ascii"]:
                try:
                    f.seek(bom_length)  # Reset to start after BOM
                    file_content = f.read().decode(fallback_encoding, errors="replace")
                    lines = file_content.splitlines()
                    logger.info(f"Read {len(lines)} lines using {fallback_encoding}")
                    content = lines
                    encoding = fallback_encoding
                    break
                except UnicodeDecodeError:
                    continue

    if not content:
        logger.error(f"Could not read {input_file} with any supported encoding")
        return None

    # Process each line and anonymize data
    anonymized_content = []
    name_count = 0
    place_count = 0
    other_count = 0  # track other anonymized fields

    # Get the gender for individuals if possible (to preserve in anonymization)
    individual_genders = {}
    current_individual = None

    # First pass to gather gender information
    for line in content:
        if line.startswith("0 @I") and " INDI" in line:
            # Extract the ID from lines like "0 @I1@ INDI"
            match = re.match(r"0 @([^@]+)@ INDI", line)
            if match:
                current_individual = match.group(1)
        elif current_individual and line.startswith("1 SEX "):
            # Extract gender
            gender = line.split("1 SEX ")[1].strip()
            if gender in ["M", "F"]:
                individual_genders[current_individual] = gender
        elif line.startswith("0 ") and current_individual:
            # Reset current individual when we reach a new level 0 record
            current_individual = None

    # Track names for each individual for consistency
    individual_names = defaultdict(dict)

    # Second pass to anonymize
    current_individual = None

    # First process all NAME tags to build our mapping dictionary
    name_line_indices = []
    for i, line in enumerate(content):
        if line.startswith("0 @I") and " INDI" in line:
            match = re.match(r"0 @([^@]+)@ INDI", line)
            if match:
                current_individual = match.group(1)
        elif line.startswith("0 ") and current_individual:
            current_individual = None

        name_match = NAME_PATTERN.match(line)
        if name_match and current_individual:
            prefix, name = name_match.groups()
            match = GEDCOM_NAME_PARTS.match(name)
            if match:
                given_name, surname, _ = match.groups()
                if given_name:
                    given_name = given_name.strip()
                    if given_name:
                        individual_names[current_individual]["given"] = given_name
                        gender = individual_genders.get(current_individual)
                        # Pre-anonymize to populate the mapping dictionaries
                        anonymizer.anonymize_given_name(given_name, gender)

                if surname:
                    surname = surname.strip()
                    if surname:
                        individual_names[current_individual]["surname"] = surname
                        # Pre-anonymize to populate the mapping dictionaries
                        anonymizer.anonymize_surname(surname)

            name_line_indices.append(i)

    # Now process all lines and apply anonymization consistently
    current_individual = None
    for i, line in enumerate(content):
        # Track the current individual
        if line.startswith("0 @I") and " INDI" in line:
            match = re.match(r"0 @([^@]+)@ INDI", line)
            if match:
                current_individual = match.group(1)
            anonymized_content.append(line)
            continue
        elif line.startswith("0 ") and current_individual:
            current_individual = None
            anonymized_content.append(line)
            continue

        # Get gender for current individual if available
        gender = (
            individual_genders.get(current_individual) if current_individual else None
        )

        # Anonymize NAME tags
        name_match = NAME_PATTERN.match(line)
        if name_match:
            prefix, name = name_match.groups()
            anonymized_name = anonymizer.anonymize_gedcom_name(name)
            anonymized_line = f"{prefix}{anonymized_name}"
            anonymized_content.append(anonymized_line)
            name_count += 1
            continue

        # Anonymize GIVN tags (for GEDCOM 7.0)
        givn_match = GIVN_PATTERN.match(line)
        if (
            givn_match
            and current_individual
            and "given" in individual_names[current_individual]
        ):
            prefix, given_name = givn_match.groups()
            # Use same mapping as in NAME tag for consistency
            original_given = individual_names[current_individual]["given"]
            if original_given in anonymizer.given_name_map:
                anonymized_given = anonymizer.given_name_map[original_given]
                anonymized_line = f"{prefix}{anonymized_given}"
                anonymized_content.append(anonymized_line)
                name_count += 1
                continue
        elif givn_match:
            prefix, given_name = givn_match.groups()
            anonymized_given = anonymizer.anonymize_given_name(given_name, gender)
            anonymized_line = f"{prefix}{anonymized_given}"
            anonymized_content.append(anonymized_line)
            name_count += 1
            continue

        # Anonymize SURN tags (for GEDCOM 7.0)
        surn_match = SURN_PATTERN.match(line)
        if (
            surn_match
            and current_individual
            and "surname" in individual_names[current_individual]
        ):
            prefix, surname = surn_match.groups()
            # Use same mapping as in NAME tag for consistency
            original_surname = individual_names[current_individual]["surname"]
            if original_surname in anonymizer.surname_map:
                anonymized_surname = anonymizer.surname_map[original_surname]
                anonymized_line = f"{prefix}{anonymized_surname}"
                anonymized_content.append(anonymized_line)
                name_count += 1
                continue
        elif surn_match:
            prefix, surname = surn_match.groups()
            anonymized_surname = anonymizer.anonymize_surname(surname)
            anonymized_line = f"{prefix}{anonymized_surname}"
            anonymized_content.append(anonymized_line)
            name_count += 1
            continue

        # Anonymize PLAC tags
        place_match = PLAC_PATTERN.match(line)
        if place_match:
            prefix, place = place_match.groups()
            anonymized_place = anonymizer.anonymize_place(place)
            anonymized_line = f"{prefix}{anonymized_place}"
            anonymized_content.append(anonymized_line)
            place_count += 1
            continue

        # Anonymize EMAIL tags
        email_match = EMAIL_PATTERN.match(line)
        if email_match:
            prefix, email = email_match.groups()
            anonymized_email = anonymizer.anonymize_email(email)
            anonymized_line = f"{prefix}{anonymized_email}"
            anonymized_content.append(anonymized_line)
            other_count += 1
            continue

        # Anonymize PHON tags
        phone_match = PHON_PATTERN.match(line)
        if phone_match:
            prefix, phone = phone_match.groups()
            anonymized_phone = anonymizer.anonymize_phone(phone)
            anonymized_line = f"{prefix}{anonymized_phone}"
            anonymized_content.append(anonymized_line)
            other_count += 1
            continue

        # Anonymize ADDR tags
        addr_match = ADDR_PATTERN.match(line)
        if addr_match:
            prefix, addr = addr_match.groups()
            anonymized_addr = anonymizer.anonymize_address(addr)
            anonymized_line = f"{prefix}{anonymized_addr}"
            anonymized_content.append(anonymized_line)
            other_count += 1
            continue

        # Anonymize WWW tags
        www_match = WWW_PATTERN.match(line)
        if www_match:
            prefix, url = www_match.groups()
            anonymized_url = anonymizer.anonymize_url(url)
            anonymized_line = f"{prefix}{anonymized_url}"
            anonymized_content.append(anonymized_line)
            other_count += 1
            continue

        # Keep other lines unchanged
        anonymized_content.append(line)

    # Write the anonymized content
    with open(output_file, "wb") as f:
        # Write the original BOM if present
        if bom_length > 0:
            if encoding == "utf-8":
                f.write(b"\xef\xbb\xbf")
            elif encoding == "utf-16-le":
                f.write(b"\xff\xfe")
            elif encoding == "utf-16-be":
                f.write(b"\xfe\xff")

        # Write the anonymized content
        output_text = "\n".join(anonymized_content)
        f.write(output_text.encode(encoding))

    logger.info(
        f"Anonymized {name_count} names, {place_count} places, and {other_count} other personal items"
    )
    logger.info(f"Wrote anonymized file to {output_file}")

    # Save mappings if requested
    if save_mappings and anonymizer.mapping_file:
        anonymizer.save_mappings(anonymizer.mapping_file)

    return output_file


def anonymize_directory(directory, recursive=False, overwrite=False, anonymizer=None):
    """
    Anonymize all GEDCOM files in a directory.

    Args:
        directory: Path to the directory
        recursive: Whether to process subdirectories recursively
        overwrite: Whether to overwrite the original files
        anonymizer: GedcomAnonymizer instance to use

    Returns:
        Number of files processed
    """
    if anonymizer is None:
        # Create a new anonymizer with mappings stored in the directory
        mapping_file = os.path.join(directory, ".gedcom_anonymizer_mappings.pkl")
        anonymizer = GedcomAnonymizer(mapping_file=mapping_file)

    processed = 0

    # Get all .ged files in the directory
    directory_path = Path(directory)

    if recursive:
        ged_files = list(directory_path.glob("**/*.ged"))
    else:
        ged_files = list(directory_path.glob("*.ged"))

    # Filter out files that already have "_anonymized" in their name, unless overwrite is True
    if not overwrite:
        ged_files = [f for f in ged_files if "_anonymized" not in f.stem]

    logger.info(f"Found {len(ged_files)} GEDCOM files to process in {directory}")

    for ged_file in ged_files:
        logger.info(f"Processing {ged_file}")
        try:
            anonymize_gedcom_file(
                str(ged_file),
                overwrite=overwrite,
                anonymizer=anonymizer,
                save_mappings=False,  # We'll save at the end
            )
            processed += 1
        except Exception as e:
            logger.error(f"Error processing {ged_file}: {e}")

    # Save mappings once at the end
    if anonymizer.mapping_file:
        anonymizer.save_mappings(anonymizer.mapping_file)

    return processed


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description="Anonymize personal data in GEDCOM files using realistic fake data"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to a single GEDCOM file to anonymize")
    group.add_argument(
        "--directory", help="Path to a directory containing GEDCOM files"
    )

    parser.add_argument("--output", help="Output file path (for single file only)")
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Process subdirectories recursively (for directory only)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite original files instead of creating new ones",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible anonymization",
    )
    parser.add_argument(
        "--mapping-file", help="File to store name mappings for consistency across runs"
    )
    parser.add_argument(
        "--preserve-structure",
        action="store_true",
        help="Preserve family relationships in anonymization",
    )

    args = parser.parse_args()

    # Create anonymizer with specified options
    anonymizer = GedcomAnonymizer(
        seed=args.seed,
        preserve_structure=args.preserve_structure,
        mapping_file=args.mapping_file,
    )

    if args.file:
        if not os.path.isfile(args.file):
            logger.error(f"File not found: {args.file}")
            return 1

        if not args.file.lower().endswith(".ged"):
            logger.warning(f"File does not have .ged extension: {args.file}")

        try:
            anonymize_gedcom_file(
                args.file, args.output, args.overwrite, anonymizer=anonymizer
            )
        except Exception as e:
            logger.error(f"Error anonymizing file: {e}")
            return 1

    elif args.directory:
        if not os.path.isdir(args.directory):
            logger.error(f"Directory not found: {args.directory}")
            return 1

        try:
            processed = anonymize_directory(
                args.directory, args.recursive, args.overwrite, anonymizer=anonymizer
            )
            logger.info(f"Successfully anonymized {processed} files")
        except Exception as e:
            logger.error(f"Error anonymizing directory: {e}")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
