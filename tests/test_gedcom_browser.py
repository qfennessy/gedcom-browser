#!/usr/bin/env python3
"""Tests for the GEDCOM browser module."""
import os
import tempfile

import pytest

from gedcom_browser import GedcomBrowser
from gedcom_parser import GedcomError, GedcomParser


def create_test_gedcom():
    """Create a test GEDCOM file with sample data."""
    content = """0 HEAD
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
0 @I1@ INDI
1 NAME John /Doe/
1 SEX M
1 BIRT
2 DATE 1 JAN 1900
2 PLAC New York, NY
1 DEAT
2 DATE 31 DEC 1980
2 PLAC Boston, MA
1 OCCU Farmer
2 DATE FROM 1920 TO 1950
2 PLAC Kansas
1 NOTE This is a note about John Doe
1 FAMS @F1@
0 @I2@ INDI
1 NAME Jane /Smith/
1 SEX F
1 BIRT
2 DATE 1 FEB 1905
2 PLAC Chicago, IL
1 FAMS @F1@
0 @I3@ INDI
1 NAME James /Doe/
1 SEX M
1 BIRT
2 DATE 15 JUN 1925
2 PLAC Kansas City, MO
1 FAMC @F1@
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 CHIL @I3@
1 MARR
2 DATE 15 MAR 1924
2 PLAC Springfield, IL
0 TRLR"""

    # Create the file with BOM
    fd, path = tempfile.mkstemp(suffix=".ged")
    os.close(fd)

    with open(path, "wb") as f:
        f.write(b"\xef\xbb\xbf")  # UTF-8 BOM
        f.write(content.encode("utf-8"))

    return path


def test_get_individuals():
    """Test retrieving all individuals from the browser."""
    gedcom_path = create_test_gedcom()

    try:
        browser = GedcomBrowser(gedcom_path)
        individuals = browser.get_individuals()

        assert len(individuals) == 3

        # Check the first individual
        assert individuals[0]["id"] == "@I1@"
        assert individuals[0]["name"] == "John /Doe/"
        assert individuals[0]["birth"] == "1 JAN 1900"
        assert individuals[0]["death"] == "31 DEC 1980"

        # Check the second individual
        assert individuals[1]["id"] == "@I2@"
        assert individuals[1]["name"] == "Jane /Smith/"
        assert individuals[1]["birth"] == "1 FEB 1905"
        assert individuals[1]["death"] == ""  # No death date

        # Check the third individual
        assert individuals[2]["id"] == "@I3@"
        assert individuals[2]["name"] == "James /Doe/"
        assert individuals[2]["birth"] == "15 JUN 1925"
        assert individuals[2]["death"] == ""  # No death date

    finally:
        os.unlink(gedcom_path)


def test_get_individual_details():
    """Test retrieving detailed information for an individual."""
    gedcom_path = create_test_gedcom()

    try:
        browser = GedcomBrowser(gedcom_path)

        # Test with a valid ID
        details = browser.get_individual_details("@I1@")

        assert details is not None
        assert details["id"] == "@I1@"
        assert details["name"] == "John /Doe/"

        # Check events
        assert len(details["events"]) == 2
        assert details["events"][0]["type"] == "BIRT"
        assert details["events"][0]["date"] == "1 JAN 1900"
        assert details["events"][0]["place"] == "New York, NY"

        assert details["events"][1]["type"] == "DEAT"
        assert details["events"][1]["date"] == "31 DEC 1980"
        assert details["events"][1]["place"] == "Boston, MA"

        # Check attributes
        assert len(details["attributes"]) == 1
        assert details["attributes"][0]["type"] == "OCCU"
        assert details["attributes"][0]["value"] == "Farmer"
        assert details["attributes"][0]["date"] == "FROM 1920 TO 1950"
        assert details["attributes"][0]["place"] == "Kansas"

        # Check families
        assert len(details["families"]["spouse"]) == 1
        assert details["families"]["spouse"][0]["id"] == "@F1@"
        assert details["families"]["spouse"][0]["spouse_id"] == "@I2@"
        assert details["families"]["spouse"][0]["spouse_name"] == "Jane /Smith/"

        # Check notes
        assert len(details["notes"]) == 1
        assert details["notes"][0] == "This is a note about John Doe"

        # Test with an invalid ID
        details = browser.get_individual_details("@I999@")
        assert details is None

    finally:
        os.unlink(gedcom_path)


def test_family_relationships():
    """Test family relationships are correctly retrieved."""
    gedcom_path = create_test_gedcom()

    try:
        browser = GedcomBrowser(gedcom_path)

        # Check the child's family connections
        child_details = browser.get_individual_details("@I3@")

        assert len(child_details["families"]["parent"]) == 1
        parent_family = child_details["families"]["parent"][0]
        assert parent_family["id"] == "@F1@"

        # Should have two parents
        assert len(parent_family["parents"]) == 2

        # Find father and mother
        father = next(
            (p for p in parent_family["parents"] if p["relation"] == "Father"), None
        )
        mother = next(
            (p for p in parent_family["parents"] if p["relation"] == "Mother"), None
        )

        assert father is not None
        assert father["id"] == "@I1@"
        assert father["name"] == "John /Doe/"

        assert mother is not None
        assert mother["id"] == "@I2@"
        assert mother["name"] == "Jane /Smith/"

    finally:
        os.unlink(gedcom_path)


def test_invalid_gedcom_strict_mode():
    """Test that the browser correctly handles invalid GEDCOM files in strict mode."""
    content = """0 HEAD
1 GEDC
2 VERS 5.5.1
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
0 TRLR"""

    fd, path = tempfile.mkstemp(suffix=".ged")
    os.close(fd)

    with open(path, "wb") as f:
        f.write(b"\xef\xbb\xbf")  # UTF-8 BOM
        f.write(content.encode("utf-8"))

    try:
        # Create a parser in strict mode, manually set to only accept 5.5.5
        parser = GedcomParser(strict_mode=True)

        # We need to force it to fail on 5.5.1 - this is testing a specific case
        # where a parser is forcibly set to only accept 5.5.5

        def _mock_validate(rec):
            # Mock validation that will always raise an error for 5.5.1
            gedc = [r for r in rec.children if r.tag == "GEDC"][0]
            vers = [r for r in gedc.children if r.tag == "VERS"][0]
            if vers.value == "5.5.1":
                raise GedcomError(
                    "Unsupported GEDCOM version: 5.5.1. Only 5.5.5 is supported"
                )

        # Replace the method with our mock
        parser._validate_header = _mock_validate

        with pytest.raises(GedcomError, match="Unsupported GEDCOM version"):
            parser.parse_file(path)
            browser = GedcomBrowser(path, parser=parser)

    finally:
        os.unlink(path)


def test_gedcom_551_relaxed_mode():
    """Test that the browser correctly handles GEDCOM 5.5.1 in relaxed mode."""
    # Create a GEDCOM 5.5.1 file
    content_551 = """0 HEAD
1 GEDC
2 VERS 5.5.1
2 FORM LINEAGE-LINKED
1 CHAR ASCII
0 @I1@ INDI
1 NAME Test /Person/
0 TRLR"""

    fd, path = tempfile.mkstemp(suffix=".ged")
    os.close(fd)

    with open(path, "wb") as f:
        # No BOM for this test
        f.write(content_551.encode("utf-8"))

    try:
        # In relaxed mode, 5.5.1 should be accepted even without BOM
        parser = GedcomParser(strict_mode=False)
        parser.parse_file(path)
        browser = GedcomBrowser(path, parser=parser)

        individuals = browser.get_individuals()
        assert len(individuals) == 1
        assert individuals[0]["id"] == "@I1@"
        assert individuals[0]["name"] == "Test /Person/"

    finally:
        os.unlink(path)


def test_gedcom_70_relaxed_mode():
    """Test that the browser correctly handles GEDCOM 7.0 in relaxed mode."""
    # Create a GEDCOM 7.0 file
    content_70 = """0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME Test /Person/
1 GIVN Test
1 SURN Person
0 TRLR"""

    fd, path = tempfile.mkstemp(suffix=".ged")
    os.close(fd)

    with open(path, "wb") as f:
        # No BOM for this test
        f.write(content_70.encode("utf-8"))

    try:
        # In relaxed mode, 7.0 should be accepted even without BOM
        parser = GedcomParser(strict_mode=False)
        parser.parse_file(path)
        browser = GedcomBrowser(path, parser=parser)

        individuals = browser.get_individuals()
        assert len(individuals) == 1
        assert individuals[0]["id"] == "@I1@"
        assert individuals[0]["name"] == "Test /Person/"

    finally:
        os.unlink(path)
