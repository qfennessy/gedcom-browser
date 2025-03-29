#!/usr/bin/env python3
"""
GEDCOM Browser
A tool to browse and explore GEDCOM 5.5.5 genealogical data files.
"""
import os
import sys
from typing import Dict, List, Optional

from gedcom_parser import GedcomError, GedcomParser, GedcomRecord


class GedcomBrowser:
    """Browser interface for GEDCOM data."""
    
    def __init__(self, gedcom_file: str, parser: Optional[GedcomParser] = None):
        """
        Initialize the browser with a GEDCOM file.
        
        Args:
            gedcom_file: Path to the GEDCOM file
            parser: Optional pre-configured parser, useful for custom settings
            
        Raises:
            GedcomError: If the file is invalid
        """
        self.parser = parser or GedcomParser()
        
        # Only parse if a new parser was created (otherwise assume it's already parsed)
        if parser is None:
            self.parser.parse_file(gedcom_file)
            
        self.current_context: Optional[GedcomRecord] = None
    
    def get_individuals(self) -> List[Dict[str, str]]:
        """
        Get a list of all individuals with basic information.
        
        Returns:
            List of dictionaries with name, id, birth, and death info
        """
        individuals = []
        
        for indi in self.parser.get_all_individuals():
            name = self._get_name(indi)
            birth = self._get_event_date(indi, 'BIRT')
            death = self._get_event_date(indi, 'DEAT')
            
            individuals.append({
                'id': indi.xref_id,
                'name': name,
                'birth': birth,
                'death': death
            })
        
        return individuals
    
    def get_individual_details(self, xref_id: str) -> Optional[Dict[str, any]]:
        """
        Get detailed information about an individual.
        
        Args:
            xref_id: XREF ID of the individual
            
        Returns:
            Dictionary with individual details or None if not found
        """
        indi = self.parser.get_individual(xref_id)
        if not indi:
            return None
        
        details = {
            'id': indi.xref_id,
            'name': self._get_name(indi),
            'events': self._get_events(indi),
            'attributes': self._get_attributes(indi),
            'families': self._get_families(indi),
            'notes': self._get_notes(indi),
            'sources': self._get_sources(indi)
        }
        
        return details
    
    def _get_name(self, indi: GedcomRecord) -> str:
        """Extract the name from an individual record."""
        for child in indi.children:
            if child.tag == 'NAME':
                return child.value
        return 'Unknown'
    
    def _get_event_date(self, indi: GedcomRecord, event_tag: str) -> str:
        """Extract the date from an event."""
        for child in indi.children:
            if child.tag == event_tag:
                for date_child in child.children:
                    if date_child.tag == 'DATE':
                        return date_child.value
        return ''
    
    def _get_events(self, indi: GedcomRecord) -> List[Dict[str, str]]:
        """Extract all events for an individual."""
        event_tags = ['BIRT', 'DEAT', 'BURI', 'CHR', 'BAPM', 'CREM', 'ADOP', 'GRAD', 'RETI']
        events = []
        
        for child in indi.children:
            if child.tag in event_tags:
                event = {'type': child.tag, 'date': '', 'place': ''}
                
                for detail in child.children:
                    if detail.tag == 'DATE':
                        event['date'] = detail.value
                    elif detail.tag == 'PLAC':
                        event['place'] = detail.value
                
                events.append(event)
        
        return events
    
    def _get_attributes(self, indi: GedcomRecord) -> List[Dict[str, str]]:
        """Extract all attributes for an individual."""
        attr_tags = ['OCCU', 'RESI', 'RELI', 'EDUC', 'NATI', 'TITL']
        attributes = []
        
        for child in indi.children:
            if child.tag in attr_tags:
                attr = {'type': child.tag, 'value': child.value, 'date': '', 'place': ''}
                
                for detail in child.children:
                    if detail.tag == 'DATE':
                        attr['date'] = detail.value
                    elif detail.tag == 'PLAC':
                        attr['place'] = detail.value
                
                attributes.append(attr)
        
        return attributes
    
    def _get_families(self, indi: GedcomRecord) -> Dict[str, List[Dict[str, str]]]:
        """Extract family relationships for an individual."""
        families = {
            'spouse': [],
            'parent': []
        }
        
        for child in indi.children:
            if child.tag == 'FAMS':  # Family where individual is spouse
                fam_id = child.value
                fam_record = self.parser.records.get(fam_id)
                
                if fam_record:
                    spouse_id = None
                    
                    # Find spouse
                    for fam_child in fam_record.children:
                        if fam_child.tag in ['HUSB', 'WIFE'] and fam_child.value != indi.xref_id:
                            spouse_id = fam_child.value
                            break
                    
                    if spouse_id and spouse_id in self.parser.records:
                        spouse = self.parser.records[spouse_id]
                        families['spouse'].append({
                            'id': fam_id,
                            'spouse_id': spouse_id,
                            'spouse_name': self._get_name(spouse)
                        })
            
            elif child.tag == 'FAMC':  # Family where individual is child
                fam_id = child.value
                fam_record = self.parser.records.get(fam_id)
                
                if fam_record:
                    parents = []
                    
                    for fam_child in fam_record.children:
                        if fam_child.tag in ['HUSB', 'WIFE']:
                            parent_id = fam_child.value
                            if parent_id in self.parser.records:
                                parent = self.parser.records[parent_id]
                                parents.append({
                                    'id': parent_id,
                                    'name': self._get_name(parent),
                                    'relation': 'Father' if fam_child.tag == 'HUSB' else 'Mother'
                                })
                    
                    families['parent'].append({
                        'id': fam_id,
                        'parents': parents
                    })
        
        return families
    
    def _get_notes(self, indi: GedcomRecord) -> List[str]:
        """Extract notes for an individual."""
        notes = []
        
        for child in indi.children:
            if child.tag == 'NOTE':
                notes.append(child.value)
        
        return notes
    
    def _get_sources(self, indi: GedcomRecord) -> List[Dict[str, str]]:
        """Extract source citations for an individual."""
        sources = []
        
        for child in indi.children:
            if child.tag == 'SOUR':
                source = {'id': child.value, 'citation': ''}
                
                for src_detail in child.children:
                    if src_detail.tag == 'PAGE':
                        source['citation'] = src_detail.value
                
                sources.append(source)
        
        return sources


def main():
    """Main entry point for the GEDCOM browser."""
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <gedcom_file>")
        sys.exit(1)
    
    gedcom_file = sys.argv[1]
    
    if not os.path.exists(gedcom_file):
        print(f"Error: File '{gedcom_file}' does not exist")
        sys.exit(1)
    
    try:
        browser = GedcomBrowser(gedcom_file)
        
        print(f"Successfully parsed GEDCOM file: {gedcom_file}")
        print(f"Found {len(browser.get_individuals())} individuals")
        
        # Here you would start an interactive browser or UI
        # For now, just print the first few individuals as a demo
        individuals = browser.get_individuals()
        if individuals:
            print("\nIndividuals:")
            for i, individual in enumerate(individuals[:5]):
                print(f"{i+1}. {individual['name']} ({individual['birth']} - {individual['death']})")
            
            if len(individuals) > 5:
                print(f"...and {len(individuals) - 5} more")
    
    except GedcomError as e:
        print(f"Error parsing GEDCOM file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()