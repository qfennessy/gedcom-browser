#!/usr/bin/env python3
"""
GEDCOM 5.5.5 Parser
Strict implementation of the GEDCOM 5.5.5 standard for genealogical data.
"""
import re
from enum import Enum, auto
from io import StringIO
from typing import Dict, List, Optional, TextIO, Tuple, Union


class Version(Enum):
    """Supported GEDCOM versions."""

    V40 = "4.0"
    V551 = "5.5.1"
    V555 = "5.5.5"
    V70 = "7.0"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, version_str: str) -> "Version":
        """Convert a version string to a Version enum."""
        version_map = {
            "4.0": cls.V40,
            "5.5.1": cls.V551,
            "5.5.5": cls.V555,
            "7.0": cls.V70,
            "7.00": cls.V70,  # Handle variant format
        }
        return version_map.get(version_str, cls.UNKNOWN)


class Encoding(Enum):
    """Valid GEDCOM encodings."""

    ASCII = "ASCII"  # For GEDCOM 4.0 and 5.5.1
    ANSEL = "ANSEL"  # For GEDCOM 4.0 and 5.5.1
    UTF8 = "UTF-8"  # For GEDCOM 5.5.5+
    UTF16 = "UNICODE"  # UTF-16 is called UNICODE in GEDCOM 5.5.5+
    UNICODE = "UNICODE"  # Alternative name

    @classmethod
    def valid_for_version(cls, encoding: "Encoding", version: Version) -> bool:
        """Check if the encoding is valid for the given version."""
        if version == Version.V40 or version == Version.V551:
            return encoding in (cls.ASCII, cls.ANSEL, cls.UTF8, cls.UTF16, cls.UNICODE)
        elif version == Version.V555:
            return encoding in (cls.UTF8, cls.UTF16, cls.UNICODE)
        elif version == Version.V70:
            # GEDCOM 7.0 primarily uses UTF-8
            return encoding == cls.UTF8
        return False


class GedcomError(Exception):
    """Base exception for GEDCOM parsing errors."""

    pass


class GedcomRecord:
    """Represents a GEDCOM record with level, tag, xref_id, and value."""

    def __init__(self, level: int, tag: str, value: str = "", xref_id: str = ""):
        self.level = level
        self.tag = tag
        self.value = value
        self.xref_id = xref_id
        self.children: List[GedcomRecord] = []

    def add_child(self, record: "GedcomRecord") -> None:
        """Add a child record to this record."""
        self.children.append(record)

    def __str__(self) -> str:
        """String representation of this record."""
        if self.xref_id:
            return f"{self.level} {self.xref_id} {self.tag} {self.value}"
        return f"{self.level} {self.tag} {self.value}"


class GedcomParser:
    """
    Parser for GEDCOM files.
    Validates according to the specific GEDCOM version specification.
    """

    # Regular expression for valid GEDCOM line (works across versions)
    LINE_PATTERN = re.compile(r"^(\d+) (?:(@[^@]+@) )?([A-Z0-9_]+)(?: (.*))?$")

    # Maximum allowed line length in code units (varies by version)
    MAX_LINE_LENGTH_555 = 255
    MAX_LINE_LENGTH_551 = 255
    MAX_LINE_LENGTH_40 = 255  # 4.0 spec is less clear, using 255 as a default
    MAX_LINE_LENGTH_70 = 0  # No line length limit in 7.0

    # Specific version validation options
    STRICT_BOM_VERSIONS = [Version.V555]  # Versions that require BOM

    def __init__(self, strict_mode=True):
        self.records: Dict[str, GedcomRecord] = {}
        self.root_records: List[GedcomRecord] = []
        self.encoding: Optional[Encoding] = None
        self.version: Version = Version.UNKNOWN
        self.strict_mode: bool = strict_mode
        self._current_record_stack: List[GedcomRecord] = []
        self._record_buffer: List[str] = []

    def get_max_line_length(self) -> int:
        """Get the maximum line length for the current version."""
        if self.version == Version.V555:
            return self.MAX_LINE_LENGTH_555
        elif self.version == Version.V551:
            return self.MAX_LINE_LENGTH_551
        elif self.version == Version.V40:
            return self.MAX_LINE_LENGTH_40
        elif self.version == Version.V70:
            return self.MAX_LINE_LENGTH_70
        return self.MAX_LINE_LENGTH_555  # Default to 5.5.5 behavior

    def parse_file(self, file_path: str) -> None:
        """
        Parse a GEDCOM file from the given path.

        Args:
            file_path: Path to the GEDCOM file

        Raises:
            GedcomError: If the file doesn't comply with its GEDCOM version specification
        """
        # First try detecting encoding with BOM
        encoding_from_bom, bom = self._detect_encoding_from_bom(file_path)

        # For version detection, we need to open the file and check the GEDCOM version
        # Try different encodings if needed
        possible_encodings = ["utf-8", "utf-16", "ascii", "latin-1"]
        file_version = None
        file_encoding = None

        # First try with BOM-detected encoding if available
        if encoding_from_bom:
            python_encoding = (
                "utf-8" if encoding_from_bom == Encoding.UTF8 else "utf-16"
            )
            possible_encodings.insert(0, python_encoding)

        # For detecting the version, it's best to read as binary first
        # and extract the header section to avoid encoding issues
        file_version = None
        with open(file_path, "rb") as f:
            # Read the first 5000 bytes which should include the header
            header_bytes = f.read(5000)

            # Try to detect version directly from the binary data
            # Look for patterns like "VERS 5.5.1" or "VERS 5.5.5"
            version_patterns = [
                (b"VERS 4.0", Version.V40),
                (b"VERS 5.5.1", Version.V551),
                (b"VERS 5.5.5", Version.V555),
                (b"VERS 7.0", Version.V70),
                (b"VERS 7.00", Version.V70),
            ]

            for pattern, version in version_patterns:
                if pattern in header_bytes:
                    file_version = version
                    break

            # If we couldn't find the version directly, try decoding and parsing
            if file_version is None:
                # Try to decode with different encodings
                for enc in ["utf-8", "utf-16", "latin-1", "ascii"]:
                    try:
                        header_text = header_bytes.decode(enc, errors="replace")
                        lines = header_text.split("\n")

                        # Find GEDC/VERS to determine version
                        in_gedc_section = False
                        for line in lines:
                            line = line.strip()
                            match = self.LINE_PATTERN.match(line)
                            if not match:
                                continue

                            level_str, _, tag, value = match.groups()
                            level = int(level_str or "0")

                            if level == 1 and tag == "GEDC":
                                in_gedc_section = True
                            elif (
                                in_gedc_section
                                and level == 2
                                and tag == "VERS"
                                and value
                            ):
                                file_version = Version.from_string(value)
                                break
                            elif level == 1 and in_gedc_section:
                                # We've left the GEDC section without finding VERS
                                in_gedc_section = False

                            # Also look for CHAR tag to determine encoding
                            if level == 1 and tag == "CHAR" and value:
                                try:
                                    file_encoding = Encoding(value.upper())
                                except ValueError:
                                    file_encoding = None

                        # If we found a version, we can stop looking
                        if file_version is not None:
                            break

                    except UnicodeDecodeError:
                        continue

        # If we still couldn't determine the version, default to 5.5.1 for relaxed mode
        if file_version is None and not self.strict_mode:
            file_version = Version.V551

        if file_version is not None:
            self.version = file_version

        if file_version is None:
            raise GedcomError("Could not determine GEDCOM version from file")

        # Validate BOM if required for this version
        if self.version in self.STRICT_BOM_VERSIONS and not bom and self.strict_mode:
            raise GedcomError(
                f"No valid BOM found. GEDCOM {self.version.value} requires a BOM for UTF-8 or UTF-16"
            )

        # Save the encoding
        self.encoding = encoding_from_bom or file_encoding or Encoding.ASCII

        # For non-strict mode, default to UTF-8 for parsing if we couldn't determine encoding
        if not self.strict_mode and not self.encoding:
            self.encoding = Encoding.UTF8

        # Re-open the file with the correct encoding, defaulting to UTF-8 for safety
        open_encoding = "utf-8"
        if self.encoding == Encoding.UTF16 or self.encoding == Encoding.UNICODE:
            open_encoding = "utf-16"
        elif self.encoding == Encoding.ASCII:
            open_encoding = "ascii"
        elif self.encoding == Encoding.ANSEL:
            # Use Latin-1 as closest approximation for ANSEL, or fall back to UTF-8
            # if file content is actually UTF-8 despite claiming ANSEL encoding
            open_encoding = "latin-1"

        # The proper way to handle this is to use a binary read first to skip the BOM,
        # then reopen the file in text mode
        if bom:
            # Calculate the number of bytes to skip
            bom_length = len(bom)
        else:
            bom_length = 0

        # For strict mode, use the detected encoding
        if self.strict_mode:
            try:
                with open(file_path, "rb") as f:
                    if bom_length > 0:
                        f.seek(bom_length)  # Skip BOM

                    # Re-open in text mode
                    text_content = f.read().decode(open_encoding)
                    self._parse_gedcom(StringIO(text_content))
            except UnicodeDecodeError as e:
                raise GedcomError(f"Encoding error: {e}")
        else:
            # For relaxed mode, try multiple encodings with error replacement
            # First try the detected encoding, then UTF-8 with replacement
            for try_encoding in [open_encoding, "utf-8", "latin-1"]:
                try:
                    with open(file_path, "rb") as f:
                        if bom_length > 0:
                            f.seek(bom_length)  # Skip BOM

                        # Re-open in text mode with the current encoding
                        text_content = f.read().decode(try_encoding, errors="replace")
                        self._parse_gedcom(StringIO(text_content))
                        break  # If successful, exit the loop
                except (UnicodeDecodeError, UnicodeError):
                    if try_encoding == "latin-1":  # Last resort failed
                        raise GedcomError(
                            "Unable to decode file with any supported encoding"
                        )
                    continue  # Try next encoding

    def _detect_encoding_from_bom(
        self, file_path: str
    ) -> Tuple[Optional[Encoding], bytes]:
        """
        Detect the encoding from the BOM at the beginning of the file.

        Args:
            file_path: Path to the GEDCOM file

        Returns:
            Tuple of (detected encoding, BOM bytes)
        """
        with open(file_path, "rb") as f:
            # Read potential BOM
            bom = f.read(4)

            if bom.startswith(b"\xef\xbb\xbf"):
                return Encoding.UTF8, bom[:3]
            elif bom.startswith(b"\xff\xfe") or bom.startswith(b"\xfe\xff"):
                return Encoding.UTF16, bom[:2]
            else:
                return None, b""

    def _parse_gedcom(self, file: TextIO) -> None:
        """
        Parse GEDCOM content from file.

        Args:
            file: File object to read from

        Raises:
            GedcomError: For any validation errors
        """
        header_found = False
        header_validated = False
        current_level = -1
        header_record = None
        max_line_length = self.get_max_line_length()

        for line_num, line in enumerate(file, 1):
            # Check for empty lines - all versions require non-empty lines
            if not line.strip():
                if self.strict_mode:
                    raise GedcomError(f"Empty line at line {line_num}")
                else:
                    continue

            # Check for leading whitespace - all versions forbid this
            if line[0].isspace():
                if self.strict_mode:
                    raise GedcomError(f"Leading whitespace at line {line_num}")
                else:
                    # Try to fix by stripping leading whitespace
                    line = line.lstrip()

            # Check line length (excluding line terminators)
            line = line.rstrip("\r\n")
            if max_line_length > 0 and len(line) > max_line_length and self.strict_mode:
                raise GedcomError(f"Line exceeds maximum length at line {line_num}")

            # Parse line
            match = self.LINE_PATTERN.match(line)
            if not match:
                if self.strict_mode:
                    raise GedcomError(
                        f"Invalid GEDCOM format at line {line_num}: {line}"
                    )
                else:
                    continue  # Skip invalid lines in non-strict mode

            level_str, xref_id, tag, value = match.groups()
            xref_id = xref_id or ""
            value = value or ""

            # Validate level number (no leading zeros, no skipped levels)
            if level_str.startswith("0") and level_str != "0" and self.strict_mode:
                raise GedcomError(f"Leading zeros in level number at line {line_num}")

            level = int(level_str)
            if level > current_level + 1 and self.strict_mode:
                raise GedcomError(
                    f"Skipped level at line {line_num} (jumped from {current_level} to {level})"
                )

            current_level = level

            # Process special continuation tags
            if tag in ("CONT", "CONC"):
                if not self._current_record_stack:
                    if self.strict_mode:
                        raise GedcomError(
                            f"{tag} tag without parent record at line {line_num}"
                        )
                    else:
                        continue  # Skip orphaned CONT/CONC in non-strict mode

                parent = self._current_record_stack[-1]

                # Check if this is under the HEAD record - only for 5.5.5 in strict mode
                if (
                    self.version == Version.V555
                    and self.strict_mode
                    and header_record
                    and self._is_under_header(parent)
                ):
                    raise GedcomError(
                        f"CONC or CONT tags are not allowed in the basic header at line {line_num}"
                    )

                if tag == "CONT":
                    parent.value += "\n" + value
                else:  # CONC
                    parent.value += value

                continue

            # Create new record
            record = GedcomRecord(level, tag, value, xref_id)

            # Add to proper parent
            if level == 0:
                self.root_records.append(record)
                self._current_record_stack = [record]

                # Store records with XREF IDs in the dictionary
                if xref_id:
                    if xref_id in self.records and self.strict_mode:
                        raise GedcomError(
                            f"Duplicate XREF ID: {xref_id} at line {line_num}"
                        )
                    self.records[xref_id] = record

                # Process header
                if tag == "HEAD":
                    if header_found and self.strict_mode:
                        raise GedcomError(
                            f"Multiple HEAD records found at line {line_num}"
                        )
                    header_found = True
                    header_record = record

            else:
                # Remove items from stack if needed
                while len(self._current_record_stack) > level:
                    self._current_record_stack.pop()

                # Add as child to parent
                if not self._current_record_stack:
                    if self.strict_mode:
                        raise GedcomError(f"Invalid level structure at line {line_num}")
                    else:
                        # In non-strict mode, try to recover by adding to the last record
                        if self.root_records:
                            parent = self.root_records[-1]
                            parent.add_child(record)
                            self._current_record_stack = [parent, record]
                        continue

                parent = self._current_record_stack[-1]
                parent.add_child(record)
                self._current_record_stack.append(record)

        if not header_found and self.strict_mode:
            raise GedcomError("No HEAD record found in GEDCOM file")

        # Validate the header at the end of parsing
        if header_record and self.strict_mode:
            self._validate_header(header_record)

    def _is_under_header(self, record: GedcomRecord) -> bool:
        """Check if a record is under the HEAD record."""
        # Traverse up the stack to see if we're under HEAD
        stack_idx = (
            self._current_record_stack.index(record)
            if record in self._current_record_stack
            else -1
        )
        if stack_idx < 0:
            return False

        for i in range(stack_idx, -1, -1):
            if (
                self._current_record_stack[i].level == 0
                and self._current_record_stack[i].tag == "HEAD"
            ):
                return True

        return False

    def _validate_header(self, header_record: GedcomRecord) -> None:
        """
        Validate the GEDCOM header structure.

        Args:
            header_record: The HEAD record to validate

        Raises:
            GedcomError: If the header is invalid
        """
        # Check for required GEDC structure
        gedc_records = [r for r in header_record.children if r.tag == "GEDC"]
        if not gedc_records:
            raise GedcomError("Missing GEDC record in header")

        gedc = gedc_records[0]

        # Check VERS under GEDC
        vers_records = [r for r in gedc.children if r.tag == "VERS"]
        if not vers_records:
            raise GedcomError("Missing VERS record under GEDC")

        # Validate GEDCOM version based on what was detected
        detected_version = Version.from_string(vers_records[0].value)

        # In strict mode, only accept 5.5.5
        if self.strict_mode and detected_version != Version.V555:
            raise GedcomError(
                f"Unsupported GEDCOM version: {vers_records[0].value}. Only 5.5.5 is supported in strict mode"
            )

        if detected_version != self.version:
            # If the version in the header doesn't match what we detected earlier,
            # update to use the version from the header
            self.version = detected_version

        # Check FORM under GEDC for 5.5+ versions
        if self.version in [Version.V551, Version.V555]:
            form_records = [r for r in gedc.children if r.tag == "FORM"]
            if not form_records:
                raise GedcomError("Missing FORM record under GEDC")

            if form_records[0].value != "LINEAGE-LINKED":
                raise GedcomError(
                    f"Unsupported GEDCOM form: {form_records[0].value}. Only LINEAGE-LINKED is supported"
                )

        # Check CHAR in header for 5.5+ versions
        char_records = [r for r in header_record.children if r.tag == "CHAR"]
        if not char_records and self.version in [Version.V551, Version.V555]:
            raise GedcomError("Missing CHAR record in header")

        # Validate encoding if CHAR is present
        if char_records:
            char_value = char_records[0].value

            try:
                file_encoding = Encoding(char_value.upper())

                # Update encoding if different
                if file_encoding != self.encoding:
                    self.encoding = file_encoding

                # For 5.5.5 in strict mode, validate UTF-8/UNICODE only
                if self.version == Version.V555 and self.strict_mode:
                    if file_encoding not in [
                        Encoding.UTF8,
                        Encoding.UTF16,
                        Encoding.UNICODE,
                    ]:
                        raise GedcomError(
                            f"Invalid encoding for GEDCOM 5.5.5: {file_encoding.value}. "
                            "Only UTF-8 and UNICODE (UTF-16) are supported"
                        )
            except ValueError:
                if self.strict_mode:
                    raise GedcomError(f"Unsupported character encoding: {char_value}")

        # Check for CONC/CONT in header
        for child in header_record.children:
            if child.tag in ("CONC", "CONT"):
                raise GedcomError(
                    "CONC or CONT tags are not allowed in the basic header"
                )

    def get_individual(self, xref_id: str) -> Optional[GedcomRecord]:
        """Get an individual record by its XREF ID."""
        record = self.records.get(xref_id)
        if record and record.tag == "INDI":
            return record
        return None

    def get_all_individuals(self) -> List[GedcomRecord]:
        """Get all individual records."""
        return [r for r in self.root_records if r.tag == "INDI"]

    def get_all_families(self) -> List[GedcomRecord]:
        """Get all family records."""
        return [r for r in self.root_records if r.tag == "FAM"]
