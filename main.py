#!/usr/bin/env python3
"""
GEDCOM Browser
Command-line interface for browsing GEDCOM genealogical data files.
"""
import argparse
import sys
from typing import List, Optional

from gedcom_parser import GedcomError, GedcomParser, GedcomRecord
from gedcom_browser import GedcomBrowser


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="GEDCOM file browser")
    parser.add_argument('gedcom_file', help='Path to the GEDCOM file')
    parser.add_argument('--validate-only', action='store_true', 
                        help='Only validate the file, do not browse')
    parser.add_argument('--list-individuals', action='store_true',
                        help='List all individuals in the file')
    parser.add_argument('--individual', metavar='XREF_ID',
                        help='Show details for a specific individual by XREF ID')
    parser.add_argument('--relaxed', action='store_true',
                        help='Enable relaxed validation for older GEDCOM versions')
    
    return parser.parse_args()


def validate_file(file_path: str, relaxed_mode: bool = False) -> bool:
    """
    Validate a GEDCOM file against its specification.
    
    Args:
        file_path: Path to the GEDCOM file
        relaxed_mode: Whether to use relaxed validation for older versions
        
    Returns:
        True if valid, False if invalid
    """
    parser = GedcomParser(strict_mode=not relaxed_mode)
    
    try:
        parser.parse_file(file_path)
        version_str = parser.version.value if parser.version else "Unknown"
        
        if relaxed_mode:
            print(f"✓ File '{file_path}' is a valid GEDCOM {version_str} file (relaxed mode)")
        else:
            print(f"✓ File '{file_path}' is a valid GEDCOM {version_str} file")
            
        print(f"  - Encoding: {parser.encoding.value}")
        print(f"  - {len(parser.get_all_individuals())} individuals")
        print(f"  - {len(parser.get_all_families())} families")
        return True
    
    except GedcomError as e:
        if relaxed_mode:
            print(f"✗ File '{file_path}' is not a valid GEDCOM file (even in relaxed mode):")
        else:
            print(f"✗ File '{file_path}' is not a valid GEDCOM file:")
        print(f"  Error: {e}")
        return False


def list_individuals(browser: GedcomBrowser) -> None:
    """
    List all individuals in the GEDCOM file.
    
    Args:
        browser: Initialized GedcomBrowser instance
    """
    individuals = browser.get_individuals()
    
    if not individuals:
        print("No individuals found in the file.")
        return
    
    # Sort by surname then given name
    def get_sort_key(person):
        name = person['name']
        parts = name.split('/')
        if len(parts) >= 3:  # Handle "Given /Surname/ Rest" format
            return (parts[1].lower(), parts[0].lower())
        return (name.lower(), "")
    
    individuals.sort(key=get_sort_key)
    
    print(f"\nIndividuals ({len(individuals)}):")
    print("-" * 80)
    print(f"{'ID':<12} {'Name':<40} {'Birth':<12} {'Death':<12}")
    print("-" * 80)
    
    for individual in individuals:
        print(f"{individual['id']:<12} {individual['name']:<40} "
              f"{individual['birth']:<12} {individual['death']:<12}")


def show_individual(browser: GedcomBrowser, xref_id: str) -> None:
    """
    Show detailed information for an individual.
    
    Args:
        browser: Initialized GedcomBrowser instance
        xref_id: XREF ID of the individual to display
    """
    details = browser.get_individual_details(xref_id)
    
    if not details:
        print(f"No individual found with ID: {xref_id}")
        return
    
    print("\n" + "=" * 80)
    print(f"Individual: {details['name']} ({details['id']})")
    print("=" * 80)
    
    # Events
    if details['events']:
        print("\nEvents:")
        print("-" * 80)
        for event in details['events']:
            print(f"{event['type']:<5} Date: {event['date']:<30} "
                  f"Place: {event['place']}")
    
    # Attributes
    if details['attributes']:
        print("\nAttributes:")
        print("-" * 80)
        for attr in details['attributes']:
            print(f"{attr['type']:<5} {attr['value']}")
            if attr['date'] or attr['place']:
                print(f"      Date: {attr['date']:<30} Place: {attr['place']}")
    
    # Family as spouse
    if details['families']['spouse']:
        print("\nSpouse in Families:")
        print("-" * 80)
        for family in details['families']['spouse']:
            print(f"Family: {family['id']}")
            print(f"Spouse: {family['spouse_name']} ({family['spouse_id']})")
    
    # Family as child
    if details['families']['parent']:
        print("\nChild in Families:")
        print("-" * 80)
        for family in details['families']['parent']:
            print(f"Family: {family['id']}")
            for parent in family['parents']:
                print(f"{parent['relation']}: {parent['name']} ({parent['id']})")
    
    # Notes
    if details['notes']:
        print("\nNotes:")
        print("-" * 80)
        for note in details['notes']:
            print(note)
    
    # Sources
    if details['sources']:
        print("\nSources:")
        print("-" * 80)
        for source in details['sources']:
            print(f"{source['id']}: {source['citation']}")


def main():
    """Main entry point for the application."""
    args = parse_args()
    
    # Validate the file first
    if not validate_file(args.gedcom_file, relaxed_mode=args.relaxed):
        sys.exit(1)
    
    # Stop here if only validation was requested
    if args.validate_only:
        sys.exit(0)
    
    try:
        # Create a GedcomBrowser using a parser with the appropriate relaxed/strict mode
        parser = GedcomParser(strict_mode=not args.relaxed)
        parser.parse_file(args.gedcom_file)
        browser = GedcomBrowser(args.gedcom_file, parser=parser)
        
        if args.individual:
            show_individual(browser, args.individual)
        elif args.list_individuals:
            list_individuals(browser)
        else:
            # Default behavior: list individuals
            list_individuals(browser)
    
    except GedcomError as e:
        print(f"Error browsing GEDCOM file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()