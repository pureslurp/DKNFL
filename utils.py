BYE_DICT = {
        'Commanders' : 14,
        'Buccaneers' : 11,
        'Seahawks' : 10,
        '49ers' : 9,
        'Chargers' : 5,
        'Steelers' : 9,
        'Cardinals' : 11,
        'Eagles' : 5,
        'Jets' : 12,
        'Giants' : 11,
        'Saints' : 12,
        'Patriots' : 14,
        'Vikings' : 6,
        'Dolphins' : 6,
        'Raiders' : 10,
        'Rams' : 6,
        'Chiefs' : 6,
        'Jaguars' : 12,
        'Colts' : 14,
        'Texans' : 14,
        'Titans' : 5,
        'Packers' : 10,
        'Lions' : 5,
        'Broncos' : 14,
        'Cowboys' : 7,
        'Browns' : 10,
        'Bengals' : 12,
        'Bears' : 7,
        'Panthers' : 11,
        'Bills' : 13,
        'Ravens' : 14,
        'Falcons' : 12
        }

TEAM_DICT = {'TB' : 'Buccaneers',
             'SEA' : 'Seahawks',
             'SF' : '49ers',
             'LAC' : 'Chargers',
             'PIT' : 'Steelers',
             'ARI' : 'Cardinals',
             'PHI' : 'Eagles',
             'NYJ' : 'Jets',
             'NYG' : 'Giants',
             'NO' : 'Saints',
             'NE' : 'Patriots',
             'MIN' : 'Vikings',
             'MIA' : 'Dolphins',
             'LV' : 'Raiders',
             'LAR' : 'Rams',
             'KC' : 'Chiefs',
             'JAX' : 'Jaguars',
             'IND' : 'Colts',
             'TEN' : 'Titans',
             'GB' : 'Packers',
             'DET' : 'Lions',
             'DEN' : 'Broncos',
             'DAL' : 'Cowboys',
             'CLE' : 'Browns',
             'CIN' : 'Bengals',
             'CHI' : 'Bears',
             'CAR' : 'Panthers',
             'BUF' : 'Bills',
             'BAL' : 'Ravens',
             'ATL' : 'Falcons',
             'WAS' : 'Commanders',
             'HOU' : 'Texans'
    }

CITY_TO_TEAM = {
             'Tampa Bay' : 'Buccaneers',
             'Seattle' : 'Seahawks',
             'San Francisco' : '49ers',
             'LA Chargers' : 'Chargers',
             'Pittsburgh' : 'Steelers',
             'Arizona' : 'Cardinals',
             'Philadelphia' : 'Eagles',
             'NY Jets' : 'Jets',
             'NY Giants' : 'Giants',
             'New Orleans' : 'Saints',
             'New England' : 'Patriots',
             'Minnesota' : 'Vikings',
             'Miami' : 'Dolphins',
             'Las Vegas' : 'Raiders',
             'LA Rams' : 'Rams',
             'Kansas City' : 'Chiefs',
             'Jacksonville' : 'Jaguars',
             'Indianapolis' : 'Colts',
             'Tennessee' : 'Titans',
             'Green Bay' : 'Packers',
             'Detroit' : 'Lions',
             'Denver' : 'Broncos',
             'Dallas' : 'Cowboys',
             'Cleveland' : 'Browns',
             'Cincinnati' : 'Bengals',
             'Chicago' : 'Bears',
             'Carolina' : 'Panthers',
             'Buffalo' : 'Bills',
             'Baltimore' : 'Ravens',
             'Atlanta' : 'Falcons',
             'Washington' : 'Commanders',
             'Houston' : 'Texans'
}

TOTAL_DICT = {
    "forward": "Proj DFS Total",
    "backward": "Act DFS Total"
}

import pandas as pd
import re

def clean_player_name(name: str) -> str:
    """
    Comprehensive player name cleaning function that handles:
    1. Basic text cleaning and normalization
    2. Regex-based pattern matching for abbreviated names
    3. Specific player name mappings from various sources
    
    Args:
        name (str): Raw player name
        
    Returns:
        str: Cleaned and standardized player name
    """
    if pd.isna(name) or not name:
        return ""
    
    name = str(name).strip()
    
    # Remove ID numbers in parentheses
    name = re.sub(r'\s*\([^)]*\)', '', name)
    
    # Handle abbreviated names where the full name is followed by abbreviation
    # Examples: 
    # "A.J. BrownA.  Brow" -> "A.J. Brown"
    # "Amon-Ra St. BrownA. St.  Brow" -> "Amon-Ra St. Brown"
    
    # Look for pattern where a name is followed by abbreviated version with dots and spaces
    abbreviated_pattern = r'([A-Za-z\-\.\s]+?)([A-Z]\.\s+[A-Za-z]+)$'
    match = re.search(abbreviated_pattern, name)
    if match:
        full_part = match.group(1).strip()
        # Check if the full part looks like a complete name (has space or hyphen)
        if ' ' in full_part or '-' in full_part:
            name = full_part
    
    # Alternative pattern: Look for cases where name ends with single letters and spaces
    if not match:
        single_letter_pattern = r'([A-Za-z\-\.\s]+?)([A-Z]\.?\s+[A-Za-z]+)$'
        alt_match = re.search(single_letter_pattern, name)
        if alt_match:
            full_part = alt_match.group(1).strip()
            if ' ' in full_part or '-' in full_part:
                name = full_part
    
    # Remove extra spaces and normalize
    name = re.sub(r'\s+', ' ', name.strip())
    
    # Handle HTML entities and special characters
    name = name.replace('\xa0', ' ')  # Replace non-breaking spaces
    
    # Apply specific player name mappings
    name_mappings = {
        "Travis Etienne": "Travis Etienne Jr.",
        "Michael Pittman": "Michael Pittman Jr.",
        "Kenneth Walker": "Kenneth Walker III",
        "Jeff Wilson": "Jeff Wilson Jr.",
        "Brian Robinson": "Brian Robinson Jr.",
        "Odell Beckham": "Odell Beckham Jr.",
        "Gardner Minshew": "Gardner Minshew II",
        "Melvin Gordon": "Melvin Gordon III",
        "Tony Jones": "Tony Jones Jr.",
        "Pierre Strong": "Pierre Strong Jr.",
        "Larry Rountree": "Larry Rountree III",
        "Amon-Ra St.": "Amon-Ra St. Brown",
        "Amon-Ra St.BrownA. S": "Amon-Ra St. Brown",
        "Amon-Ra St. BrownA. St. Brow": "Amon-Ra St. Brown",
        "D.K. Metcalf": "DK Metcalf",
        "D.J. Moore": "DJ Moore",
        "Nathaniel Dell": "Tank Dell",
        "Josh Palmer": "Joshua Palmer",
        "Cartavious Bigsby": "Tank Bigsby",
        "Damario Douglas": "DeMario Douglas",
        "Re'Mahn Davis": "Ray Davis",
        "Gabriel Davis": "Gabe Davis",
        "Chigoziem Okonkwo": "Chig Okonkwo",
        "John Mundt": "Johnny Mundt",
        "Mar'Keise Irving": "Bucky Irving"
    }
    
    # Apply name mapping if exists
    if name in name_mappings:
        name = name_mappings[name]
    
    return name

def normalize_team_name(team_name: str) -> str:
    """
    Normalize team names to consistent format
    
    Args:
        team_name (str): Raw team name
        
    Returns:
        str: Normalized team name
    """
    if pd.isna(team_name) or not team_name:
        return ""
    
    team_name = str(team_name).strip()
    
    # Use existing mappings
    if team_name in TEAM_DICT:
        return TEAM_DICT[team_name]
    elif team_name in CITY_TO_TEAM:
        return CITY_TO_TEAM[team_name]
    
    return team_name