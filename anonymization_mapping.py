#!/usr/bin/env python3
"""
Mapping for anonymizing GEDCOM files.
This script provides consistent mappings for anonymizing names and places in GEDCOM files.
"""

NAME_MAPPINGS = {
    # Primary name in the example
    "Patrick": "John",
    "Quentin": "Williams",
    "Fennessy": "Fitzgerald",
    
    # Other common names in the files (for consistency)
    "Smith": "Miller",
    "Jones": "Baker",
    "Anderson": "Thompson",
    "Wilson": "Harris",
    "Taylor": "Walker",
    "Johnson": "Brown",
    "Williams": "Davis", 
    "Parker": "Lewis",
    "Thomas": "Martin",
    "Margaret": "Elizabeth",
    "Sarah": "Jennifer",
    "James": "Robert",
    "Jennifer": "Catherine",
    "Michael": "Christopher",
    "Emily": "Sophia", 
    "Daniel": "Matthew",
    "Robert": "William",
    "Elizabeth": "Olivia",
    "David": "Joseph",
}

PLACE_MAPPINGS = {
    # Cities
    "New York": "Metro City",
    "Boston": "Harbor City",
    "Chicago": "Laketown",
    "Los Angeles": "Coastal City",
    "Seattle": "Rainview",
    "Portland": "Greenvale",
    "San Francisco": "Bay City",
    "Denver": "Mountain View",
    "San Diego": "Beach City",
    "San Jose": "Valley Town",
    "Dallas": "Central City",
    "Austin": "Hill County",
    "Nashville": "Music Town",
    "Memphis": "River City",
    "MIT Cambridge": "University City",
    "Silicon Valley": "Tech Valley",
    
    # States
    "NY": "MC",
    "MA": "HC",
    "IL": "LT",
    "CA": "CC",
    "WA": "RV",
    "OR": "GV",
    "CA": "BC",
    "CO": "MV",
    "TX": "HC",
    "TN": "MT",
}

def anonymize_name(name):
    """
    Anonymize a personal name consistently.
    
    Args:
        name: The original name string
        
    Returns:
        The anonymized name
    """
    # Special case for the full name pattern in the example
    if "Patrick" in name and "Quentin" in name and "Fennessy" in name:
        return name.replace("Patrick Quentin Fennessy", "John Williams Fitzgerald")
    
    # Handle case insensitive replacements for Fennessy -> Fitzgerald specifically
    if "fennessy" in name.lower():
        # Case-preserving replacement
        result = ""
        idx = 0
        pattern = "fennessy"
        replacement = "Fitzgerald"
        pattern_lower = pattern.lower()
        
        while idx < len(name):
            if name[idx:idx+len(pattern_lower)].lower() == pattern_lower:
                # If pattern is found, replace it with the replacement
                result += replacement
                idx += len(pattern_lower)
            else:
                # Otherwise, add the current character to the result
                result += name[idx]
                idx += 1
        return result
    
    # Handle GEDCOM name format with slashes around surname (e.g., "John /Smith/")
    if "/" in name:
        # Extract parts of the name
        parts = name.split("/")
        if len(parts) >= 3:
            given_names = parts[0].strip()
            surname = parts[1].strip()
            rest = "/".join(parts[2:])
            
            # Anonymize given names and surname
            for original, replacement in NAME_MAPPINGS.items():
                given_names = given_names.replace(original, replacement)
                surname = surname.replace(original, replacement)
            
            return f"{given_names}/{surname}/{rest}"
    
    # Handle normal name format
    result = name
    for original, replacement in NAME_MAPPINGS.items():
        # Case insensitive replacement
        pattern = original
        if pattern.lower() in result.lower():
            # Simple case-preserving replacement
            pattern_lower = pattern.lower()
            pattern_idx = result.lower().find(pattern_lower)
            while pattern_idx != -1:
                result = result[:pattern_idx] + replacement + result[pattern_idx + len(pattern):]
                pattern_idx = result.lower().find(pattern_lower, pattern_idx + len(replacement))
    
    return result

def anonymize_place(place):
    """
    Anonymize a place name consistently.
    
    Args:
        place: The original place string
        
    Returns:
        The anonymized place
    """
    result = place
    for original, replacement in PLACE_MAPPINGS.items():
        result = result.replace(original, replacement)
    
    return result