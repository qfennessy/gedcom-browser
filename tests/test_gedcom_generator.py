#!/usr/bin/env python3
"""Tests for the GEDCOM test file generator module."""
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

# Add the parent directory to sys.path to import the module
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Import the module - need to adjust the name since it has a hyphen
import importlib.util
spec = importlib.util.spec_from_file_location(
    "create_test_gedcom", 
    os.path.join(parent_dir, "create-test-gedcom.py")
)
create_test_gedcom = importlib.util.module_from_spec(spec)
spec.loader.exec_module(create_test_gedcom)

# Import specific classes and functions
Person = create_test_gedcom.Person
Family = create_test_gedcom.Family
GedcomGenerator = create_test_gedcom.GedcomGenerator
parse_date = create_test_gedcom.parse_date


class TestGedcomGenerator(unittest.TestCase):
    """Test cases for the GEDCOM generator."""

    def setUp(self):
        """Set up test fixtures."""
        self.start_date = datetime.strptime("1900-01-01", "%Y-%m-%d")
        self.end_date = datetime.strptime("2000-01-01", "%Y-%m-%d")
        self.seed = 42
        
    def test_person_initialization(self):
        """Test that a Person can be initialized correctly."""
        faker = create_test_gedcom.Faker()
        faker.seed_instance(self.seed)
        
        person = Person(faker, birth_date=self.start_date, gender='M')
        
        self.assertIsNotNone(person.id)
        self.assertEqual(person.gender, 'M')
        self.assertEqual(person.birth_date, self.start_date)
        self.assertIsNotNone(person.given_name)
        self.assertIsNotNone(person.surname)
        
    def test_person_events_generation(self):
        """Test that a Person generates life events correctly."""
        faker = create_test_gedcom.Faker()
        faker.seed_instance(self.seed)
        
        birth_date = self.start_date
        death_date = birth_date + timedelta(days=80*365)  # 80 years later
        
        person = Person(faker, birth_date=birth_date, death_date=death_date, gender='F')
        
        # Test that birth event is always present
        birth_events = [e for e in person.events if e['tag'] == 'BIRT']
        self.assertEqual(len(birth_events), 1)
        self.assertEqual(birth_events[0]['date'], birth_date.strftime("%d %b %Y").upper())
        
        # Test that death event is present
        death_events = [e for e in person.events if e['tag'] == 'DEAT']
        self.assertEqual(len(death_events), 1)
        self.assertEqual(death_events[0]['date'], death_date.strftime("%d %b %Y").upper())
        
        # Test that burial typically follows death
        burial_events = [e for e in person.events if e['tag'] == 'BURI']
        if burial_events:
            burial_date = datetime.strptime(burial_events[0]['date'], "%d %b %Y")
            death_date_obj = datetime.strptime(death_events[0]['date'], "%d %b %Y")
            self.assertGreaterEqual(burial_date, death_date_obj)
            self.assertLessEqual((burial_date - death_date_obj).days, 14)
    
    def test_family_initialization(self):
        """Test that a Family can be initialized correctly."""
        faker = create_test_gedcom.Faker()
        faker.seed_instance(self.seed)
        
        husband = Person(faker, gender='M')
        wife = Person(faker, gender='F')
        
        family = Family(faker, husband, wife)
        
        self.assertIsNotNone(family.id)
        self.assertEqual(family.husband, husband)
        self.assertEqual(family.wife, wife)
        self.assertEqual(len(family.children), 0)
        
    def test_gedcom_generator_initialization(self):
        """Test that the GedcomGenerator initializes with correct parameters."""
        generator = GedcomGenerator(
            start_date=self.start_date,
            end_date=self.end_date,
            num_people=10,
            num_generations=2,
            seed=self.seed
        )
        
        self.assertEqual(generator.start_date, self.start_date)
        self.assertEqual(generator.end_date, self.end_date)
        self.assertEqual(generator.num_people, 10)
        self.assertEqual(generator.num_generations, 2)
        self.assertEqual(generator.version, "5.5.1")  # Default version
        
    def test_gedcom_generator_with_version(self):
        """Test that the GedcomGenerator accepts custom version."""
        for version in ["4.0", "5.5.1", "5.5.5", "7.0"]:
            generator = GedcomGenerator(
                start_date=self.start_date,
                end_date=self.end_date,
                num_people=5,
                num_generations=1,
                seed=self.seed,
                version=version
            )
            
            self.assertEqual(generator.version, version)
            
    def test_generate_different_versions(self):
        """Test that different GEDCOM versions are generated correctly."""
        # Create temporary files for test output
        temp_files = {}
        for version in ["4.0", "5.5.1", "5.5.5", "7.0"]:
            fd, path = tempfile.mkstemp(suffix=".ged")
            os.close(fd)
            temp_files[version] = path
            
        try:
            # Generate files for each version
            for version in ["4.0", "5.5.1", "5.5.5", "7.0"]:
                generator = GedcomGenerator(
                    start_date=self.start_date,
                    end_date=self.end_date,
                    num_people=5,
                    num_generations=1,
                    seed=self.seed,
                    version=version
                )
                generator.save_to_file(temp_files[version])
                
                # Check file exists and has content
                self.assertTrue(os.path.exists(temp_files[version]))
                self.assertGreater(os.path.getsize(temp_files[version]), 0)
                
                # Check the file contains the correct version header
                with open(temp_files[version], 'rb') as f:
                    content = f.read()
                    if version in ["5.5.5", "7.0"]:
                        # These should have a UTF-8 BOM
                        self.assertTrue(content.startswith(b'\xef\xbb\xbf'))
                        # Skip BOM for text decoding
                        text_content = content[3:].decode('utf-8')
                    else:
                        # These should be plain ASCII
                        text_content = content.decode('ascii')
                
                    # Check version in header
                    version_pattern = f"2 VERS {version}"
                    self.assertIn(version_pattern, text_content)
                    
                    # Check character set
                    if version in ["4.0", "5.5.1"]:
                        self.assertIn("1 CHAR ASCII", text_content)
                    else:
                        self.assertIn("1 CHAR UTF-8", text_content)
                
        finally:
            # Clean up temporary files
            for path in temp_files.values():
                if os.path.exists(path):
                    os.unlink(path)

    def test_set_version_from_cli_args(self):
        """Test that command-line arguments correctly set the GEDCOM version."""
        # Test that --v40 sets version to 4.0
        args = type('Args', (), {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'num_people': 5,
            'num_generations': 1,
            'seed': self.seed,
            'region': None,
            'v40': True,
            'v551': False,
            'v555': False,
            'v70': False,
            'output': 'test.ged'
        })
        
        # Mock the generator
        with patch.object(create_test_gedcom, 'GedcomGenerator') as mock_generator:
            # Call main with mocked args
            with patch.object(create_test_gedcom.argparse.ArgumentParser, 'parse_args', return_value=args):
                # Prevent actual file creation
                with patch.object(create_test_gedcom.GedcomGenerator, 'save_to_file'):
                    create_test_gedcom.main()
                    
                    # Check version passed to generator
                    generator_calls = mock_generator.call_args_list
                    self.assertEqual(len(generator_calls), 1)
                    _, kwargs = generator_calls[0]
                    self.assertEqual(kwargs['version'], "4.0")
        
        # Test that --v555 sets version to 5.5.5
        args.v40 = False
        args.v555 = True
        
        with patch.object(create_test_gedcom, 'GedcomGenerator') as mock_generator:
            with patch.object(create_test_gedcom.argparse.ArgumentParser, 'parse_args', return_value=args):
                with patch.object(create_test_gedcom.GedcomGenerator, 'save_to_file'):
                    create_test_gedcom.main()
                    
                    generator_calls = mock_generator.call_args_list
                    self.assertEqual(len(generator_calls), 1)
                    _, kwargs = generator_calls[0]
                    self.assertEqual(kwargs['version'], "5.5.5")
                    
        # Test that --v70 sets version to 7.0
        args.v555 = False
        args.v70 = True
        
        with patch.object(create_test_gedcom, 'GedcomGenerator') as mock_generator:
            with patch.object(create_test_gedcom.argparse.ArgumentParser, 'parse_args', return_value=args):
                with patch.object(create_test_gedcom.GedcomGenerator, 'save_to_file'):
                    create_test_gedcom.main()
                    
                    generator_calls = mock_generator.call_args_list
                    self.assertEqual(len(generator_calls), 1)
                    _, kwargs = generator_calls[0]
                    self.assertEqual(kwargs['version'], "7.0")

    def test_parse_date(self):
        """Test the parse_date function properly validates dates."""
        # Valid date
        date = parse_date("2022-01-01")
        self.assertEqual(date.year, 2022)
        self.assertEqual(date.month, 1)
        self.assertEqual(date.day, 1)
        
        # Invalid date format
        with self.assertRaises(Exception):
            parse_date("01/01/2022")


if __name__ == '__main__':
    unittest.main()