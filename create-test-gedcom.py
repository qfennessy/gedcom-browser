#!/usr/bin/env python3
"""
GEDCOM Test File Generator
A tool to generate random GEDCOM files for testing.

Supports the following GEDCOM versions:
- GEDCOM 4.0 (--v40): Basic format with ASCII encoding
- GEDCOM 5.5.1 (--v551): Default format with ASCII encoding and FORM tag
- GEDCOM 5.5.5 (--v555): UTF-8 with BOM and stricter validation
- GEDCOM 7.0 (--v70): Latest version with UTF-8 encoding

Each version has appropriate headers and encoding to meet format specifications.
"""
import os
import sys
import argparse
import logging
import random
from datetime import datetime, timedelta
import uuid
from pathlib import Path
from faker import Faker
from typing import Dict, List, Set, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# GEDCOM header constants for different versions
GEDCOM_HEADER_40 = """0 HEAD
1 SOUR GEDCOM-GENERATOR
2 VERS 1.0
2 NAME GEDCOM Test Generator
1 DEST GEDCOM-BROWSER
1 DATE {current_date}
1 GEDC
2 VERS 4.0
1 CHAR ASCII"""

GEDCOM_HEADER_551 = """0 HEAD
1 SOUR GEDCOM-GENERATOR
2 VERS 1.0
2 NAME GEDCOM Test Generator
1 DEST GEDCOM-BROWSER
1 DATE {current_date}
1 GEDC
2 VERS 5.5.1
2 FORM LINEAGE-LINKED
1 CHAR ASCII"""

GEDCOM_HEADER_555 = """0 HEAD
1 SOUR GEDCOM-GENERATOR
2 VERS 1.0
2 NAME GEDCOM Test Generator
1 DEST GEDCOM-BROWSER
1 DATE {current_date}
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
1 CHAR UTF-8"""

GEDCOM_HEADER_70 = """0 HEAD
1 SOUR GEDCOM-GENERATOR
2 VERS 1.0
2 NAME GEDCOM Test Generator
1 DEST GEDCOM-BROWSER
1 DATE {current_date}
1 GEDC
2 VERS 7.0
1 CHAR UTF-8"""

GEDCOM_FOOTER = "0 TRLR"

# Valid GEDCOM tags for events/attributes
EVENT_TAGS = {
    "BIRT": "Birth",
    "DEAT": "Death",
    "BURI": "Burial",
    "CREM": "Cremation",
    "BAPM": "Baptism",
    "BARM": "Bar Mitzvah",
    "BASM": "Bas Mitzvah",
    "CHRA": "Adult Christening",
    "CHR": "Christening",
    "CONF": "Confirmation",
    "GRAD": "Graduation",
    "EMIG": "Emigration",
    "IMMI": "Immigration",
    "NATU": "Naturalization"
}

ATTRIBUTE_TAGS = {
    "CAST": "Caste",
    "EDUC": "Education",
    "NATI": "Nationality",
    "OCCU": "Occupation",
    "PROP": "Property",
    "RELI": "Religion",
    "RESI": "Residence",
    "TITL": "Title"
}

# Define relationship chance probabilities
RELATIONSHIP_CHANCES = {
    "marriage": 0.8,      # Chance of a person getting married
    "children": 0.75,     # Chance of a couple having children
    "divorce": 0.15,      # Chance of a marriage ending in divorce
    "remarriage": 0.4,    # Chance of remarrying after divorce/death of spouse
    "child_spacing": 2.5  # Average years between children
}

# Cultural naming patterns
CULTURAL_PATTERNS = {
    # East Asian - children typically take father's surname
    "asian": ["zh_CN", "zh_TW", "ja_JP", "ko_KR"],
    
    # Hispanic/Spanish - children often take both parents' surnames
    # Traditional: Father's surname + Mother's surname
    "hispanic": ["es_ES", "es_MX", "es_AR", "es_CO", "pt_BR"],
    
    # Nordic - some countries traditionally use patronymics
    # Not fully supported yet, but prepared for future enhancement
    "nordic": ["is_IS", "no_NO", "da_DK", "sv_SE"],
    
    # Default Western - children typically take father's surname
    "western": ["en_US", "en_GB", "fr_FR", "de_DE", "it_IT"]
}

# Event probabilities
EVENT_CHANCES = {
    "BIRT": 1.0,     # Everyone has a birth record
    "DEAT": 0.3,     # 30% chance of having a death record
    "BURI": 0.8,     # 80% of deaths have burial
    "BAPM": 0.4,     # 40% chance of baptism
    "CHR": 0.3,      # 30% chance of christening
    "CONF": 0.2,     # 20% chance of confirmation
    "GRAD": 0.5,     # 50% chance of graduation
    "EMIG": 0.2,     # 20% chance of emigration
    "IMMI": 0.2,     # 20% chance of immigration
    "NATU": 0.1      # 10% chance of naturalization
}

# Attribute probabilities
ATTRIBUTE_CHANCES = {
    "EDUC": 0.7,    # 70% chance of education record
    "NATI": 0.8,    # 80% chance of nationality record
    "OCCU": 0.9,    # 90% chance of occupation record
    "RELI": 0.6,    # 60% chance of religion record
    "RESI": 1.0     # Everyone has at least one residence
}


class Person:
    """Class to represent a person with GEDCOM attributes."""
    
    def __init__(self, faker, birth_date=None, death_date=None, gender=None, region=None, 
                 given_name=None, surname=None, cultural_background=None):
        """Initialize a person with random attributes."""
        self.id = f"I{uuid.uuid4().hex[:8].upper()}"
        self.faker = faker
        self.region = region
        self.cultural_background = cultural_background or self._determine_cultural_background(region)
        
        # Set gender, 50% chance of each by default
        self.gender = gender if gender is not None else random.choice(['M', 'F'])
        
        # Use provided name components or generate appropriate ones for gender
        if given_name:
            self.given_name = given_name
        else:
            if self.gender == 'M':
                self.given_name = faker.first_name_male()
            else:
                self.given_name = faker.first_name_female()
        
        # Use provided surname or generate one
        self.surname = surname or faker.last_name()
        
        # Set birth and death dates
        self.birth_date = birth_date or self._generate_date()
        self.death_date = death_date
        if self.death_date is None and random.random() < EVENT_CHANCES["DEAT"]:
            min_age = 18
            max_age = 95
            days_to_add = random.randint(min_age * 365, max_age * 365)
            self.death_date = self.birth_date + timedelta(days=days_to_add)
        
        # Events and attributes
        self.events = self._generate_events()
        self.attributes = self._generate_attributes()
        
        # Family relationships
        self.parent_family = None
        self.spouse_families = []
        
    def _determine_cultural_background(self, region):
        """Determine cultural background based on region."""
        if not region:
            return "western"  # Default
            
        for culture, regions in CULTURAL_PATTERNS.items():
            if region in regions:
                return culture
                
        return "western"  # Default to western naming conventions
    
    def _generate_date(self):
        """Generate a random date for the person."""
        # This will be overridden based on the date range from command line
        days = random.randint(0, 365 * 70)  # Up to 70 years ago
        return datetime.now() - timedelta(days=days)
    
    def _generate_events(self):
        """Generate random life events."""
        events = []
        
        # Birth is always included
        birth_place = self.faker.city() + ", " + self.faker.state() + ", " + self.faker.country()
        events.append({
            "tag": "BIRT",
            "date": self.birth_date.strftime("%d %b %Y").upper(),
            "place": birth_place
        })
        
        # Death if applicable
        if self.death_date:
            death_place = self.faker.city() + ", " + self.faker.state() + ", " + self.faker.country()
            events.append({
                "tag": "DEAT",
                "date": self.death_date.strftime("%d %b %Y").upper(),
                "place": death_place
            })
            
            # Burial likely follows death
            if random.random() < EVENT_CHANCES["BURI"]:
                burial_days = random.randint(1, 14)  # Burial typically within 2 weeks
                burial_date = self.death_date + timedelta(days=burial_days)
                events.append({
                    "tag": "BURI",
                    "date": burial_date.strftime("%d %b %Y").upper(),
                    "place": death_place  # Often same city as death
                })
        
        # Other life events
        for tag, chance in EVENT_CHANCES.items():
            if tag in ["BIRT", "DEAT", "BURI"]:
                continue  # Already handled
                
            if random.random() < chance:
                # Most events happen between age 0 and 50
                if self.death_date:
                    max_days = (self.death_date - self.birth_date).days
                else:
                    max_days = 365 * 50
                
                # Adjust for event type
                if tag in ["BAPM", "CHR"]:
                    # Typically happens in first 2 years
                    event_days = random.randint(30, 730)
                elif tag == "CONF":
                    # Typically happens between 12-16
                    event_days = random.randint(12 * 365, 16 * 365)
                elif tag == "GRAD":
                    # Typically happens between 18-25
                    event_days = random.randint(18 * 365, 25 * 365)
                elif tag in ["EMIG", "IMMI"]:
                    # Typically happens between 16-40
                    event_days = random.randint(16 * 365, 40 * 365)
                elif tag == "NATU":
                    # Typically happens 5-10 years after immigration
                    immi_events = [e for e in events if e["tag"] == "IMMI"]
                    if immi_events:
                        immi_date = datetime.strptime(immi_events[0]["date"], "%d %b %Y")
                        natu_days = random.randint(5 * 365, 10 * 365)
                        event_date = immi_date + timedelta(days=natu_days)
                        if self.death_date and event_date > self.death_date:
                            continue  # Skip if after death
                        events.append({
                            "tag": tag,
                            "date": event_date.strftime("%d %b %Y").upper(),
                            "place": self.faker.city() + ", " + self.faker.state() + ", " + self.faker.country()
                        })
                        continue
                    else:
                        continue  # Skip naturalization if no immigration
                else:
                    event_days = random.randint(0, max_days)
                
                event_date = self.birth_date + timedelta(days=event_days)
                if self.death_date and event_date > self.death_date:
                    continue  # Skip events after death
                
                events.append({
                    "tag": tag,
                    "date": event_date.strftime("%d %b %Y").upper(),
                    "place": self.faker.city() + ", " + self.faker.state() + ", " + self.faker.country()
                })
        
        return events
    
    def _generate_attributes(self):
        """Generate random attributes."""
        attributes = []
        
        for tag, chance in ATTRIBUTE_CHANCES.items():
            # For multiple instances of the same attribute (e.g., multiple residences)
            instances = 1
            if tag == "RESI":
                instances = random.randint(1, 4)  # 1-4 residences
            elif tag == "OCCU":
                instances = random.randint(1, 3)  # 1-3 occupations
            
            for _ in range(instances):
                if random.random() < chance:
                    # Attribute date typically happens between ages 16-70
                    min_age = 16 if tag not in ["RESI"] else 0  # Residence can be from birth
                    max_age = 70
                    
                    if self.death_date:
                        death_age_days = (self.death_date - self.birth_date).days
                        max_days = min(death_age_days, max_age * 365)
                    else:
                        max_days = max_age * 365
                    
                    attr_days = random.randint(min_age * 365, max(min_age * 365 + 1, max_days))
                    attr_date = self.birth_date + timedelta(days=attr_days)
                    
                    # Generate attribute value based on tag
                    if tag == "EDUC":
                        value = random.choice([
                            "High School", "College", "University", 
                            "Bachelor's Degree", "Master's Degree", "Doctorate"
                        ])
                    elif tag == "NATI":
                        value = self.faker.country()
                    elif tag == "OCCU":
                        value = self.faker.job()
                    elif tag == "RELI":
                        value = random.choice([
                            "Catholic", "Protestant", "Jewish", "Islamic", 
                            "Hindu", "Buddhist", "Orthodox", "None"
                        ])
                    elif tag == "RESI":
                        value = ""  # Residence doesn't have a value, just place
                    else:
                        value = self.faker.sentence(nb_words=3)
                    
                    attributes.append({
                        "tag": tag,
                        "date": attr_date.strftime("%d %b %Y").upper(),
                        "place": self.faker.city() + ", " + self.faker.state() + ", " + self.faker.country(),
                        "value": value
                    })
        
        return attributes
    
    def generate_child_surname(self, father=None, mother=None):
        """
        Generate an appropriate surname for a child based on cultural background.
        
        Different cultures have different naming conventions:
        - Western: typically father's surname
        - Hispanic/Spanish: often father's surname + mother's surname
        - East Asian: usually father's surname
        """
        if not father and not mother:
            # No parents, use a random surname
            return self.faker.last_name()
            
        # Default for many cultures: father's surname if available, otherwise mother's
        if self.cultural_background == "western" or self.cultural_background == "asian":
            if father:
                return father.surname
            elif mother:
                return mother.surname
            
        # Hispanic/Spanish naming conventions (simplified)
        elif self.cultural_background == "hispanic":
            if father and mother:
                # In Hispanic convention, typically: father's surname + mother's surname
                # With 80% probability use compound surname, 20% just father's
                if random.random() < 0.8:
                    return f"{father.surname}-{mother.surname}"
                else:
                    return father.surname
            elif father:
                return father.surname
            elif mother:
                return mother.surname
                
        # Nordic naming (simplified implementation for now)
        elif self.cultural_background == "nordic":
            if father:
                return father.surname
            elif mother:
                return mother.surname
                
        # Fallback for any other case
        if father:
            return father.surname
        elif mother:
            return mother.surname
        else:
            return self.faker.last_name()
            
    @classmethod
    def create_child(cls, faker, father, mother, birth_date, gender=None, region=None, cultural_background=None):
        """Create a child with appropriate surname based on parents' cultural background."""
        # Determine region and cultural background 
        # Prefer the specified region, otherwise use father's or mother's
        child_region = region or (father.region if father else (mother.region if mother else None))
        
        # Determine cultural background
        # First use the explicitly specified one, then try to get from parents, then infer from region
        if cultural_background:
            child_culture = cultural_background
        elif father and father.cultural_background:
            child_culture = father.cultural_background
        elif mother and mother.cultural_background:
            child_culture = mother.cultural_background
        else:
            child_culture = None  # Will be determined from region in the constructor
        
        # Create the child with no surname yet
        child = cls(faker=faker, birth_date=birth_date, gender=gender, region=child_region, 
                   cultural_background=child_culture)
        
        # Now set the surname based on cultural conventions
        child.surname = child.generate_child_surname(father, mother)
        
        return child

    def to_gedcom(self):
        """Convert person to GEDCOM format."""
        lines = [f"0 @{self.id}@ INDI"]
        
        # Name
        lines.append(f"1 NAME {self.given_name} /{self.surname}/")
        lines.append(f"2 GIVN {self.given_name}")
        lines.append(f"2 SURN {self.surname}")
        
        # Sex
        lines.append(f"1 SEX {self.gender}")
        
        # Events
        for event in self.events:
            lines.append(f"1 {event['tag']}")
            lines.append(f"2 DATE {event['date']}")
            if "place" in event:
                lines.append(f"2 PLAC {event['place']}")
        
        # Attributes
        for attr in self.attributes:
            lines.append(f"1 {attr['tag']} {attr.get('value', '')}")
            lines.append(f"2 DATE {attr['date']}")
            if "place" in attr:
                lines.append(f"2 PLAC {attr['place']}")
        
        # Family links
        if self.parent_family:
            lines.append(f"1 FAMC @{self.parent_family}@")
        
        for family_id in self.spouse_families:
            lines.append(f"1 FAMS @{family_id}@")
        
        return "\n".join(lines)


class Family:
    """Class to represent a family with GEDCOM attributes."""
    
    def __init__(self, faker, husband=None, wife=None):
        """Initialize a family with husband and wife."""
        self.id = f"F{uuid.uuid4().hex[:8].upper()}"
        self.faker = faker
        self.husband = husband
        self.wife = wife
        self.children = []
        self.events = self._generate_events()
    
    def _generate_events(self):
        """Generate family events like marriage and divorce."""
        events = []
        
        # Only generate marriage if both spouses exist
        if self.husband and self.wife:
            # Marriage typically happens when both are adults
            husband_adult_date = self.husband.birth_date + timedelta(days=18*365)
            wife_adult_date = self.wife.birth_date + timedelta(days=18*365)
            
            earliest_marriage = max(husband_adult_date, wife_adult_date)
            
            # Find the first death if any
            if self.husband.death_date and self.wife.death_date:
                latest_alive = min(self.husband.death_date, self.wife.death_date)
            elif self.husband.death_date:
                latest_alive = self.husband.death_date
            elif self.wife.death_date:
                latest_alive = self.wife.death_date
            else:
                latest_alive = datetime.now()
            
            # If marriage is possible (both reached adulthood before one died)
            if earliest_marriage < latest_alive:
                # Random marriage date between adulthood and first death
                days_range = (latest_alive - earliest_marriage).days
                if days_range > 0:
                    marriage_days = random.randint(0, days_range)
                    marriage_date = earliest_marriage + timedelta(days=marriage_days)
                    
                    # Add marriage event
                    marriage_place = self.faker.city() + ", " + self.faker.state() + ", " + self.faker.country()
                    events.append({
                        "tag": "MARR",
                        "date": marriage_date.strftime("%d %b %Y").upper(),
                        "place": marriage_place
                    })
                    
                    # Possible divorce (if both still alive and random chance)
                    if random.random() < RELATIONSHIP_CHANCES["divorce"]:
                        divorce_min_days = 365  # Minimum 1 year of marriage
                        divorce_max_days = (latest_alive - marriage_date).days
                        
                        if divorce_max_days > divorce_min_days:
                            divorce_days = random.randint(divorce_min_days, divorce_max_days)
                            divorce_date = marriage_date + timedelta(days=divorce_days)
                            
                            events.append({
                                "tag": "DIV",
                                "date": divorce_date.strftime("%d %b %Y").upper(),
                                "place": self.faker.city() + ", " + self.faker.state() + ", " + self.faker.country()
                            })
        
        return events
    
    def to_gedcom(self):
        """Convert family to GEDCOM format."""
        lines = [f"0 @{self.id}@ FAM"]
        
        # Add husband
        if self.husband:
            lines.append(f"1 HUSB @{self.husband.id}@")
        
        # Add wife
        if self.wife:
            lines.append(f"1 WIFE @{self.wife.id}@")
        
        # Add children
        for child in self.children:
            lines.append(f"1 CHIL @{child.id}@")
        
        # Add events
        for event in self.events:
            lines.append(f"1 {event['tag']}")
            lines.append(f"2 DATE {event['date']}")
            if "place" in event:
                lines.append(f"2 PLAC {event['place']}")
        
        return "\n".join(lines)


class GedcomGenerator:
    """Generate random GEDCOM files."""
    
    def __init__(self, start_date, end_date, num_people, num_generations, 
                 seed=None, region=None, version="5.5.1", culture=None):
        """Initialize the generator with parameters."""
        self.start_date = start_date
        self.end_date = end_date
        self.num_people = num_people
        self.num_generations = num_generations
        self.region = region
        self.version = version
        self.culture = culture
        
        # Set random seed if provided
        if seed is not None:
            random.seed(seed)
            
        # Initialize faker with region if specified
        if region:
            self.faker = Faker(region)
        else:
            self.faker = Faker()
            
        # If seed provided, set faker seed as well
        if seed is not None:
            self.faker.seed_instance(seed)
        
        # Storage for individuals and families
        self.individuals = []
        self.families = []
        
        # Track individuals by generation
        self.generations = {i: [] for i in range(num_generations)}
    
    def generate(self):
        """Generate the GEDCOM data."""
        # Calculate people per generation (approximately)
        people_per_gen = {}
        total_weight = sum(range(1, self.num_generations + 1))
        remaining = self.num_people
        
        # Allocate more people to more recent generations
        for gen in range(self.num_generations, 0, -1):
            if gen == 1:  # Last generation gets all remaining
                people_per_gen[gen - 1] = remaining
            else:
                weight = gen / total_weight
                count = int(self.num_people * weight)
                people_per_gen[gen - 1] = count
                remaining -= count
        
        # Generate individuals for each generation
        for gen in range(self.num_generations):
            self._generate_generation(gen, people_per_gen[gen])
            
        # Create families and relationships
        self._create_relationships()
        
        # Generate GEDCOM content
        gedcom_content = self._generate_gedcom()
        
        return gedcom_content
    
    def _generate_generation(self, generation, count):
        """Generate individuals for a specific generation."""
        logger.info(f"Generating generation {generation} with {count} people")
        
        # Calculate date range for this generation
        gen_span = (self.end_date - self.start_date).days
        gen_size = gen_span / self.num_generations
        
        gen_start = self.start_date + timedelta(days=int(generation * gen_size))
        gen_end = self.start_date + timedelta(days=int((generation + 1) * gen_size))
        
        # Generate individuals
        for _ in range(count):
            # Random birth date in this generation's range
            days = random.randint(0, (gen_end - gen_start).days)
            birth_date = gen_start + timedelta(days=days)
            
            # Create person with the specified culture if provided
            person = Person(
                self.faker, 
                birth_date=birth_date, 
                region=self.region,
                cultural_background=self.culture  # This will override region-based culture if provided
            )
            self.individuals.append(person)
            self.generations[generation].append(person)
    
    def _create_relationships(self):
        """Create family relationships between individuals."""
        # Start with the oldest generation and work forward
        for gen in range(self.num_generations - 1):
            current_gen = self.generations[gen]
            next_gen = self.generations[gen + 1]
            
            # Create marriages within the current generation
            available_males = [p for p in current_gen if p.gender == 'M' and not p.spouse_families]
            available_females = [p for p in current_gen if p.gender == 'F' and not p.spouse_families]
            
            # Shuffle for random matching
            random.shuffle(available_males)
            random.shuffle(available_females)
            
            # Create marriages
            num_marriages = min(len(available_males), len(available_females))
            marriages = int(num_marriages * RELATIONSHIP_CHANCES["marriage"])
            
            for i in range(marriages):
                husband = available_males[i]
                wife = available_females[i]
                
                # Create family
                family = Family(self.faker, husband, wife)
                self.families.append(family)
                
                # Update spouse references
                husband.spouse_families.append(family.id)
                wife.spouse_families.append(family.id)
                
                # Assign children from the next generation
                children_per_family = len(next_gen) / max(1, marriages)
                num_children = int(random.normalvariate(children_per_family, children_per_family / 3))
                num_children = max(0, min(num_children, len(next_gen)))
                
                if num_children > 0 and random.random() < RELATIONSHIP_CHANCES["children"]:
                    # Take the next batch of children
                    start_idx = int(i * children_per_family)
                    assigned_children = next_gen[start_idx:start_idx + num_children]
                    
                    for i, child in enumerate(assigned_children):
                        # Make sure child is younger than parents
                        if child.birth_date > husband.birth_date + timedelta(days=15*365) and \
                           child.birth_date > wife.birth_date + timedelta(days=15*365):
                            # Create a new child with appropriate surname based on parents
                            new_child = Person.create_child(
                                faker=self.faker,
                                father=husband,
                                mother=wife,
                                birth_date=child.birth_date,
                                gender=child.gender,
                                region=self.region,
                                cultural_background=self.culture
                            )
                            
                            # Copy ID and other properties from original child
                            new_child.id = child.id
                            new_child.death_date = child.death_date
                            new_child.events = child.events
                            new_child.attributes = child.attributes
                            
                            # Replace the original child in the individuals list
                            index = self.individuals.index(child)
                            self.individuals[index] = new_child
                            
                            # Replace in the generations list too
                            gen_index = self.generations[gen+1].index(child)
                            self.generations[gen+1][gen_index] = new_child
                            
                            # Add to family
                            family.children.append(new_child)
                            new_child.parent_family = family.id
                            
                            # Update the assigned_children list for consistent handling
                            assigned_children[i] = new_child
            
            # Look for unmarried individuals with children
            unmarried_with_children = [p for p in next_gen if not p.parent_family]
            
            # Assign some to single-parent families
            for child in unmarried_with_children:
                if random.random() < 0.2:  # 20% chance of being in a single-parent family
                    # Decide if single father or mother
                    if random.random() < 0.3:  # 30% chance of single father
                        unmarried_parents = [p for p in current_gen if p.gender == 'M' and not p.spouse_families]
                    else:  # 70% chance of single mother
                        unmarried_parents = [p for p in current_gen if p.gender == 'F' and not p.spouse_families]
                    
                    if unmarried_parents:
                        parent = random.choice(unmarried_parents)
                        
                        # Create a single-parent family
                        if parent.gender == 'M':
                            family = Family(self.faker, husband=parent)
                        else:
                            family = Family(self.faker, wife=parent)
                            
                        self.families.append(family)
                        parent.spouse_families.append(family.id)
                        
                        # Add child to family with appropriate surname
                        if child.birth_date > parent.birth_date + timedelta(days=15*365):
                            # Create new child with parent's surname following cultural convention
                            new_child = Person.create_child(
                                faker=self.faker,
                                father=parent if parent.gender == 'M' else None,
                                mother=parent if parent.gender == 'F' else None,
                                birth_date=child.birth_date,
                                gender=child.gender,
                                region=self.region,
                                cultural_background=self.culture
                            )
                            
                            # Copy ID and other properties from original child
                            new_child.id = child.id
                            new_child.death_date = child.death_date
                            new_child.events = child.events
                            new_child.attributes = child.attributes
                            
                            # Replace the original child
                            index = self.individuals.index(child)
                            self.individuals[index] = new_child
                            
                            # Replace in generations too
                            gen_index = self.generations[gen+1].index(child)
                            self.generations[gen+1][gen_index] = new_child
                            
                            # Add to family
                            family.children.append(new_child)
                            new_child.parent_family = family.id
    
    def _generate_gedcom(self):
        """Generate GEDCOM content."""
        lines = []
        
        # Add header based on version
        current_date = datetime.now().strftime("%d %b %Y").upper()
        
        if self.version == "4.0":
            lines.append(GEDCOM_HEADER_40.format(current_date=current_date))
        elif self.version == "5.5.1":
            lines.append(GEDCOM_HEADER_551.format(current_date=current_date))
        elif self.version == "5.5.5":
            lines.append(GEDCOM_HEADER_555.format(current_date=current_date))
        elif self.version == "7.0":
            lines.append(GEDCOM_HEADER_70.format(current_date=current_date))
        else:
            # Default to 5.5.1
            lines.append(GEDCOM_HEADER_551.format(current_date=current_date))
        
        # Add individuals
        for person in self.individuals:
            person_gedcom = person.to_gedcom()
            # Remove any empty lines that might be in the person's GEDCOM
            person_gedcom = "\n".join(line for line in person_gedcom.split("\n") if line.strip())
            lines.append(person_gedcom)
        
        # Add families
        for family in self.families:
            family_gedcom = family.to_gedcom()
            # Remove any empty lines that might be in the family's GEDCOM
            family_gedcom = "\n".join(line for line in family_gedcom.split("\n") if line.strip())
            lines.append(family_gedcom)
        
        # Add footer
        lines.append(GEDCOM_FOOTER)
        
        # Join all lines and ensure no empty lines
        return "\n".join(lines)
    
    def save_to_file(self, filename):
        """Save GEDCOM content to a file."""
        gedcom_content = self.generate()
        
        # Handle different encoding requirements based on version
        if self.version == "5.5.5" or self.version == "7.0":
            # GEDCOM 5.5.5 requires UTF-8 with BOM
            # GEDCOM 7.0 uses UTF-8 (we'll add BOM for consistency)
            with open(filename, 'wb') as f:
                # Add UTF-8 BOM
                f.write(b'\xef\xbb\xbf')
                # Write content as UTF-8
                f.write(gedcom_content.encode('utf-8'))
            
            logger.info(f"Generated GEDCOM {self.version} file with UTF-8 BOM saved to {filename}")
        else:
            # GEDCOM 4.0 and 5.5.1 typically use ASCII encoding without BOM
            with open(filename, 'w', encoding='ascii') as f:
                f.write(gedcom_content)
            
            logger.info(f"Generated GEDCOM {self.version} file with ASCII encoding saved to {filename}")
        
        logger.info(f"Contains {len(self.individuals)} individuals and {len(self.families)} families")


def parse_date(date_str):
    """Parse date string in format YYYY-MM-DD."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="Generate random GEDCOM test files")
    
    parser.add_argument('--start-date', type=parse_date, required=True,
                        help='Start date for the genealogy in YYYY-MM-DD format')
    parser.add_argument('--end-date', type=parse_date, required=True,
                        help='End date for the genealogy in YYYY-MM-DD format')
    parser.add_argument('--num-people', type=int, required=True,
                        help='Number of individuals to generate')
    parser.add_argument('--num-generations', type=int, required=True,
                        help='Number of generations to generate')
    parser.add_argument('--seed', type=int,
                        help='Random seed for reproducible generation')
    parser.add_argument('--region', type=str,
                        help='Country/region for names (e.g., "en_US", "fr_FR", "es_ES")')
    parser.add_argument('--culture', type=str, choices=['western', 'hispanic', 'asian', 'nordic'],
                        help='Cultural naming convention to use (default: based on region)')
    parser.add_argument('--output', type=str, default='random_gedcom.ged',
                        help='Output filename (default: random_gedcom.ged)')
    
    # GEDCOM version options
    version_group = parser.add_mutually_exclusive_group()
    version_group.add_argument('--v40', dest='v40', action='store_true', 
                               help='Generate GEDCOM 4.0 file (ASCII encoding)')
    version_group.add_argument('--v551', dest='v551', action='store_true', 
                               help='Generate GEDCOM 5.5.1 file (default)')
    version_group.add_argument('--v555', dest='v555', action='store_true', 
                               help='Generate GEDCOM 5.5.5 file (with UTF-8 BOM)')
    version_group.add_argument('--v70', dest='v70', action='store_true', 
                               help='Generate GEDCOM 7.0 file (UTF-8 encoding)')
    
    args = parser.parse_args()
    
    # Validate date range
    if args.start_date >= args.end_date:
        parser.error("Start date must be earlier than end date")
    
    # Validate numbers
    if args.num_people < 1:
        parser.error("Number of people must be at least 1")
    
    if args.num_generations < 1:
        parser.error("Number of generations must be at least 1")
    
    # Determine which GEDCOM version to generate
    gedcom_version = "5.5.1"  # Default to 5.5.1
    if args.v40:
        gedcom_version = "4.0"
    elif args.v551:
        gedcom_version = "5.5.1"
    elif args.v555:
        gedcom_version = "5.5.5"
    elif args.v70:
        gedcom_version = "7.0"
    
    # Generate the GEDCOM file
    generator = GedcomGenerator(
        start_date=args.start_date,
        end_date=args.end_date,
        num_people=args.num_people,
        num_generations=args.num_generations,
        seed=args.seed,
        region=args.region,
        version=gedcom_version,
        culture=args.culture
    )
    
    generator.save_to_file(args.output)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())