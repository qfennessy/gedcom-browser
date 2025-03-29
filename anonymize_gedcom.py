#!/usr/bin/env python3
"""
GEDCOM Anonymizer
A tool to anonymize personal data in GEDCOM genealogical data files.
"""
import os
import sys
import re
import argparse
import logging
from pathlib import Path

from anonymization_mapping import anonymize_name, anonymize_place

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Regular expressions for identifying patterns to anonymize
NAME_PATTERN = re.compile(r'^(\d+\s+NAME\s+)(.+)$')
PLAC_PATTERN = re.compile(r'^(\d+\s+PLAC\s+)(.+)$')
GIVN_PATTERN = re.compile(r'^(\d+\s+GIVN\s+)(.+)$')
SURN_PATTERN = re.compile(r'^(\d+\s+SURN\s+)(.+)$')


def detect_file_encoding(file_path):
    """
    Detect the encoding and BOM of a GEDCOM file.
    
    Args:
        file_path: Path to the GEDCOM file
        
    Returns:
        Tuple of (encoding, bom_length)
    """
    with open(file_path, 'rb') as f:
        bom = f.read(4)
        
        if bom.startswith(b'\xef\xbb\xbf'):
            return 'utf-8', 3
        elif bom.startswith(b'\xff\xfe'):
            return 'utf-16-le', 2
        elif bom.startswith(b'\xfe\xff'):
            return 'utf-16-be', 2
        else:
            # Try to guess encoding - most GEDCOM files are ASCII, ANSEL, or UTF-8
            return 'utf-8', 0


def anonymize_gedcom_file(input_file, output_file=None, overwrite=False):
    """
    Anonymize a GEDCOM file by replacing names and places.
    
    Args:
        input_file: Path to the input GEDCOM file
        output_file: Path to the output GEDCOM file (optional)
        overwrite: Whether to overwrite the input file
        
    Returns:
        Path to the anonymized file
    """
    if output_file is None:
        if overwrite:
            output_file = input_file
        else:
            # Create a new filename with _anonymized suffix
            input_path = Path(input_file)
            output_file = str(input_path.with_stem(f"{input_path.stem}_anonymized"))
    
    # Detect encoding
    encoding, bom_length = detect_file_encoding(input_file)
    logger.info(f"Detected encoding: {encoding}" + (f" with BOM ({bom_length} bytes)" if bom_length > 0 else ""))
    
    # Read the file content, skipping the BOM
    content = []
    with open(input_file, 'rb') as f:
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
            logger.warning(f"Failed to decode with {encoding}, trying fallback encodings")
            for fallback_encoding in ['utf-8', 'latin-1', 'ascii']:
                try:
                    f.seek(bom_length)  # Reset to start after BOM
                    file_content = f.read().decode(fallback_encoding, errors='replace')
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
    
    # Process each line and anonymize names and places
    anonymized_content = []
    name_count = 0
    place_count = 0
    
    for line in content:
        # Anonymize NAME tags
        name_match = NAME_PATTERN.match(line)
        if name_match:
            prefix, name = name_match.groups()
            anonymized_name = anonymize_name(name)
            anonymized_line = f"{prefix}{anonymized_name}"
            anonymized_content.append(anonymized_line)
            if anonymized_name != name:
                name_count += 1
            continue
            
        # Anonymize PLAC tags
        place_match = PLAC_PATTERN.match(line)
        if place_match:
            prefix, place = place_match.groups()
            anonymized_place = anonymize_place(place)
            anonymized_line = f"{prefix}{anonymized_place}"
            anonymized_content.append(anonymized_line)
            if anonymized_place != place:
                place_count += 1
            continue
            
        # Anonymize GIVN tags (for GEDCOM 7.0)
        givn_match = GIVN_PATTERN.match(line)
        if givn_match:
            prefix, given_name = givn_match.groups()
            anonymized_given = anonymize_name(given_name)
            anonymized_line = f"{prefix}{anonymized_given}"
            anonymized_content.append(anonymized_line)
            if anonymized_given != given_name:
                name_count += 1
            continue
            
        # Anonymize SURN tags (for GEDCOM 7.0)
        surn_match = SURN_PATTERN.match(line)
        if surn_match:
            prefix, surname = surn_match.groups()
            anonymized_surname = anonymize_name(surname)
            anonymized_line = f"{prefix}{anonymized_surname}"
            anonymized_content.append(anonymized_line)
            if anonymized_surname != surname:
                name_count += 1
            continue
            
        # Keep other lines unchanged
        anonymized_content.append(line)
    
    # Write the anonymized content
    with open(output_file, 'wb') as f:
        # Write the original BOM if present
        if bom_length > 0:
            if encoding == 'utf-8':
                f.write(b'\xef\xbb\xbf')
            elif encoding == 'utf-16-le':
                f.write(b'\xff\xfe')
            elif encoding == 'utf-16-be':
                f.write(b'\xfe\xff')
        
        # Write the anonymized content
        output_text = '\n'.join(anonymized_content)
        f.write(output_text.encode(encoding))
    
    logger.info(f"Anonymized {name_count} names and {place_count} places")
    logger.info(f"Wrote anonymized file to {output_file}")
    
    return output_file


def anonymize_directory(directory, recursive=False, overwrite=False):
    """
    Anonymize all GEDCOM files in a directory.
    
    Args:
        directory: Path to the directory
        recursive: Whether to process subdirectories recursively
        overwrite: Whether to overwrite the original files
        
    Returns:
        Number of files processed
    """
    processed = 0
    
    # Get all .ged files in the directory
    directory_path = Path(directory)
    
    if recursive:
        ged_files = list(directory_path.glob('**/*.ged'))
    else:
        ged_files = list(directory_path.glob('*.ged'))
    
    logger.info(f"Found {len(ged_files)} GEDCOM files in {directory}")
    
    for ged_file in ged_files:
        logger.info(f"Processing {ged_file}")
        try:
            anonymize_gedcom_file(str(ged_file), overwrite=overwrite)
            processed += 1
        except Exception as e:
            logger.error(f"Error processing {ged_file}: {e}")
    
    return processed


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="Anonymize personal data in GEDCOM files")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--file', help='Path to a single GEDCOM file to anonymize')
    group.add_argument('--directory', help='Path to a directory containing GEDCOM files')
    
    parser.add_argument('--output', help='Output file path (for single file only)')
    parser.add_argument('--recursive', action='store_true', 
                        help='Process subdirectories recursively (for directory only)')
    parser.add_argument('--overwrite', action='store_true',
                        help='Overwrite original files instead of creating new ones')
    
    args = parser.parse_args()
    
    if args.file:
        if not os.path.isfile(args.file):
            logger.error(f"File not found: {args.file}")
            return 1
            
        if not args.file.lower().endswith('.ged'):
            logger.warning(f"File does not have .ged extension: {args.file}")
            
        try:
            anonymize_gedcom_file(args.file, args.output, args.overwrite)
        except Exception as e:
            logger.error(f"Error anonymizing file: {e}")
            return 1
    
    elif args.directory:
        if not os.path.isdir(args.directory):
            logger.error(f"Directory not found: {args.directory}")
            return 1
            
        try:
            processed = anonymize_directory(args.directory, args.recursive, args.overwrite)
            logger.info(f"Successfully anonymized {processed} files")
        except Exception as e:
            logger.error(f"Error anonymizing directory: {e}")
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())