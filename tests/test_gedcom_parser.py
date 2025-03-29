#!/usr/bin/env python3
"""Tests for the GEDCOM parser module."""
import os
import tempfile
from io import StringIO

import pytest

from gedcom_parser import Encoding, GedcomError, GedcomParser, GedcomRecord, Version


def create_test_file(content, encoding="utf-8"):
    """Create a temporary file with the given content and encoding."""
    fd, path = tempfile.mkstemp(suffix=".ged")
    os.close(fd)

    # Add appropriate BOM
    if encoding == "utf-8":
        bom = b"\xef\xbb\xbf"
    elif encoding == "utf-16-le":
        bom = b"\xff\xfe"
    elif encoding == "utf-16-be":
        bom = b"\xfe\xff"
    else:
        bom = b""

    with open(path, "wb") as f:
        f.write(bom)
        f.write(content.encode(encoding))

    return path


def test_valid_gedcom_utf8():
    """Test parsing a valid GEDCOM file with UTF-8 encoding."""
    content = """0 HEAD
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
0 @I1@ INDI
1 NAME John /Doe/
1 BIRT
2 DATE 1 JAN 1900
0 TRLR"""

    path = create_test_file(content, "utf-8")

    try:
        parser = GedcomParser()
        parser.parse_file(path)

        # Check if the parser correctly parsed the header
        assert len(parser.root_records) == 3
        assert parser.root_records[0].tag == "HEAD"

        # Check individuals
        individuals = parser.get_all_individuals()
        assert len(individuals) == 1
        assert individuals[0].xref_id == "@I1@"

        # Check name
        name_records = [c for c in individuals[0].children if c.tag == "NAME"]
        assert len(name_records) == 1
        assert name_records[0].value == "John /Doe/"

    finally:
        os.unlink(path)


def test_validate_header_strict_mode():
    """Test validation of the GEDCOM header in strict mode."""
    # Valid header
    valid_header = GedcomRecord(0, "HEAD")
    gedc = GedcomRecord(1, "GEDC")
    vers = GedcomRecord(2, "VERS", "5.5.5")
    form = GedcomRecord(2, "FORM", "LINEAGE-LINKED")
    char = GedcomRecord(1, "CHAR", "UTF-8")

    valid_header.add_child(gedc)
    gedc.add_child(vers)
    gedc.add_child(form)
    valid_header.add_child(char)

    parser = GedcomParser(strict_mode=True)
    parser.encoding = Encoding.UTF8
    parser.version = Version.V555

    # Should not raise an exception
    parser._validate_header(valid_header)

    # Invalid FORM
    invalid_form = GedcomRecord(2, "FORM", "OTHER")
    gedc.children = [vers, invalid_form]

    with pytest.raises(GedcomError, match="Unsupported GEDCOM form"):
        parser._validate_header(valid_header)

    # Restore valid form
    gedc.children = [vers, form]

    # Missing CHAR
    valid_header.children = [gedc]

    with pytest.raises(GedcomError, match="Missing CHAR record"):
        parser._validate_header(valid_header)

    # Restore CHAR
    valid_header.children = [gedc, char]

    # Test with invalid encoding - this is now handled differently in the updated code
    # Instead of testing CHAR vs detected encoding, let's use an actually invalid encoding
    invalid_char = GedcomRecord(1, "CHAR", "INVALID_ENCODING")
    valid_header.children = [gedc, invalid_char]

    with pytest.raises(GedcomError):
        parser._validate_header(valid_header)


def test_validate_header_relaxed_mode():
    """Test validation of the GEDCOM header in relaxed mode."""
    # 5.5.1 header in relaxed mode
    header_551 = GedcomRecord(0, "HEAD")
    gedc = GedcomRecord(1, "GEDC")
    vers = GedcomRecord(2, "VERS", "5.5.1")
    form = GedcomRecord(2, "FORM", "LINEAGE-LINKED")
    char = GedcomRecord(1, "CHAR", "ASCII")

    header_551.add_child(gedc)
    gedc.add_child(vers)
    gedc.add_child(form)
    header_551.add_child(char)

    parser = GedcomParser(strict_mode=False)
    parser.encoding = Encoding.ASCII
    parser.version = Version.V551

    # Should not raise an exception in relaxed mode
    parser._validate_header(header_551)

    # Even 4.0 should work in relaxed mode
    vers_40 = GedcomRecord(2, "VERS", "4.0")
    gedc.children = [vers_40, form]
    parser.version = Version.V40

    # Should not raise an exception in relaxed mode
    parser._validate_header(header_551)


def test_multiple_version_support():
    """Test that the parser correctly handles files of different versions."""
    # Create files for each supported version with appropriate content
    version_content = {
        "4.0": """0 HEAD
1 GEDC
2 VERS 4.0
1 CHAR ASCII
0 @I1@ INDI
1 NAME John /Doe/
0 TRLR""",
        "5.5.1": """0 HEAD
1 GEDC
2 VERS 5.5.1
2 FORM LINEAGE-LINKED
1 CHAR ASCII
0 @I1@ INDI
1 NAME John /Doe/
0 TRLR""",
        "5.5.5": """0 HEAD
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
0 @I1@ INDI
1 NAME John /Doe/
0 TRLR""",
        "7.0": """0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME John /Doe/
1 GIVN John
1 SURN Doe
0 TRLR""",
    }

    # Add UTF-8 BOM to 5.5.5 version, as it requires it
    temp_files = {}
    try:
        for version, content in version_content.items():
            fd, path = tempfile.mkstemp(suffix=".ged")
            os.close(fd)

            with open(path, "wb") as f:
                # Add BOM only for 5.5.5 in strict mode
                if version == "5.5.5":
                    f.write(b"\xef\xbb\xbf")

                f.write(content.encode("utf-8"))

            temp_files[version] = path

        # Test strict mode - should work only for 5.5.5
        strict_parser = GedcomParser(strict_mode=True)

        # 5.5.5 should work in strict mode
        strict_parser.parse_file(temp_files["5.5.5"])
        assert strict_parser.version == Version.V555

        # Other versions should fail in strict mode
        for version in ["4.0", "5.5.1", "7.0"]:
            with pytest.raises(GedcomError):
                strict_parser = GedcomParser(strict_mode=True)
                strict_parser.parse_file(temp_files[version])

        # Test relaxed mode - should work for all versions
        for version, version_enum in [
            ("4.0", Version.V40),
            ("5.5.1", Version.V551),
            ("5.5.5", Version.V555),
            ("7.0", Version.V70),
        ]:
            relaxed_parser = GedcomParser(strict_mode=False)
            relaxed_parser.parse_file(temp_files[version])
            assert relaxed_parser.version == version_enum

            # Check that we can get individuals
            assert len(relaxed_parser.get_all_individuals()) == 1

    finally:
        # Clean up temporary files
        for path in temp_files.values():
            os.unlink(path)


def test_conc_cont_tags():
    """Test handling of CONC and CONT tags."""
    content = """0 HEAD
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
0 @I1@ INDI
1 NAME John /Doe/
1 NOTE This is a note
2 CONC  that continues on the same line
2 CONT And this is on a new line
0 TRLR"""

    path = create_test_file(content, "utf-8")

    try:
        parser = GedcomParser()
        parser.parse_file(path)

        individuals = parser.get_all_individuals()
        note_records = [c for c in individuals[0].children if c.tag == "NOTE"]

        assert len(note_records) == 1
        assert (
            note_records[0].value
            == "This is a note that continues on the same line\nAnd this is on a new line"
        )

    finally:
        os.unlink(path)


def test_invalid_gedcom_no_bom():
    """Test that files without BOM are rejected."""
    content = """0 HEAD
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
0 TRLR"""

    fd, path = tempfile.mkstemp(suffix=".ged")
    os.close(fd)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    try:
        parser = GedcomParser()
        with pytest.raises(GedcomError, match="No valid BOM found"):
            parser.parse_file(path)

    finally:
        os.unlink(path)


def test_invalid_gedcom_empty_line():
    """Test that files with empty lines are rejected."""
    content = """0 HEAD
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8

0 TRLR"""

    path = create_test_file(content, "utf-8")

    try:
        parser = GedcomParser()
        with pytest.raises(GedcomError, match="Empty line"):
            parser.parse_file(path)

    finally:
        os.unlink(path)


def test_invalid_gedcom_leading_whitespace():
    """Test that files with leading whitespace are rejected."""
    content = """0 HEAD
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
 0 TRLR"""

    path = create_test_file(content, "utf-8")

    try:
        parser = GedcomParser()
        with pytest.raises(GedcomError, match="Leading whitespace"):
            parser.parse_file(path)

    finally:
        os.unlink(path)


def test_invalid_gedcom_skip_level():
    """Test that files that skip levels are rejected."""
    content = """0 HEAD
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
0 @I1@ INDI
2 NAME John /Doe/
0 TRLR"""

    path = create_test_file(content, "utf-8")

    try:
        parser = GedcomParser()
        with pytest.raises(GedcomError, match="Skipped level"):
            parser.parse_file(path)

    finally:
        os.unlink(path)


def test_invalid_gedcom_leading_zero():
    """Test that files with leading zeros in level numbers are rejected."""
    content = """0 HEAD
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
0 @I1@ INDI
01 NAME John /Doe/
0 TRLR"""

    path = create_test_file(content, "utf-8")

    try:
        parser = GedcomParser()
        with pytest.raises(GedcomError, match="Leading zeros"):
            parser.parse_file(path)

    finally:
        os.unlink(path)


def test_invalid_gedcom_long_line():
    """Test that files with lines exceeding max length are rejected."""
    # Create a line longer than 255 characters
    long_value = "x" * 250
    content = f"""0 HEAD
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
0 @I1@ INDI
1 NOTE {long_value}
0 TRLR"""

    path = create_test_file(content, "utf-8")

    try:
        parser = GedcomParser()
        with pytest.raises(GedcomError, match="exceeds maximum length"):
            parser.parse_file(path)

    finally:
        os.unlink(path)


def test_invalid_gedcom_conc_cont_in_header():
    """Test that CONC/CONT tags in the header are rejected."""
    content = """0 HEAD
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
1 NOTE Test
2 CONC more text
0 TRLR"""

    path = create_test_file(content, "utf-8")

    try:
        parser = GedcomParser()
        with pytest.raises(GedcomError, match="CONC or CONT tags are not allowed"):
            parser.parse_file(path)

    finally:
        os.unlink(path)
