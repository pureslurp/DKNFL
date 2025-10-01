#!/usr/bin/env python3
"""
Script to analyze how each position performs against specific teams.
Generates CSV files showing average points given up by each team to each position.
"""

import pandas as pd
import os
import argparse
import glob
from collections import defaultdict
import re
from utils import clean_player_name

def extract_opponent_from_game_info(game_info):
    """
    Extract opponent team from Game Info field.
    Format: "TEAM1@TEAM2 DATE TIME" or "TEAM1@TEAM2"
    Returns the opponent team abbreviation.
    """
    if pd.isna(game_info) or not game_info:
        return None
    
    # Extract team abbreviations from game info
    # Format: "CIN@CLE 09/07/2025 01:00PM ET" -> ["CIN", "CLE"]
    match = re.match(r'([A-Z]{2,3})@([A-Z]{2,3})', game_info)
    if match:
        return match.group(2)  # Return the second team (opponent)
    return None

def get_opponent_team(player_team, game_info):
    """
    Determine the opponent team for a given player.
    """
    if pd.isna(game_info) or not game_info:
        return None
    
    # Extract both teams from game info
    match = re.match(r'([A-Z]{2,3})@([A-Z]{2,3})', game_info)
    if match:
        team1, team2 = match.groups()
        # Return the team that's not the player's team
        if player_team == team1:
            return team2
        elif player_team == team2:
            return team1
    return None

def load_nfl_schedule():
    """
    Load the NFL schedule to determine team matchups for each week.
    Returns a dictionary: {week: {team: opponent}}
    """
    schedule_file = "2025/nfl_schedule.csv"
    if not os.path.exists(schedule_file):
        print(f"Warning: {schedule_file} not found")
        return {}
    
    df = pd.read_csv(schedule_file)
    schedule = {}
    
    for _, row in df.iterrows():
        week = int(row['Week'])
        home_team = row['Home'].strip()
        away_team = row['Away'].strip()
        
        if week not in schedule:
            schedule[week] = {}
        
        # Map both directions
        schedule[week][home_team] = away_team
        schedule[week][away_team] = home_team
    
    return schedule

def find_player_team_from_other_weeks(player_name, current_week, base_dir="2025"):
    """
    Find which team a player plays for by checking other weeks' DKSalaries files.
    """
    # Get all available weeks
    all_weeks = []
    for item in os.listdir(base_dir):
        if item.startswith('WEEK') and os.path.isdir(os.path.join(base_dir, item)):
            week_num = int(item.replace('WEEK', ''))
            if week_num != current_week:  # Skip current week
                all_weeks.append(week_num)
    
    all_weeks.sort()
    
    # Check each week's DKSalaries file
    for week_num in all_weeks:
        week_path = os.path.join(base_dir, f'WEEK{week_num}')
        dk_files = [f for f in os.listdir(week_path) if f.startswith('DKSalaries') and f.endswith('.csv')]
        
        if dk_files:
            dk_file = os.path.join(week_path, dk_files[0])
            try:
                dk_df = pd.read_csv(dk_file)
                
                # Clean the player name for matching
                clean_name = clean_player_name(player_name)
                
                # Check if player exists in this week's DKSalaries
                for _, row in dk_df.iterrows():
                    dk_name = row['Name'].strip()
                    dk_clean_name = clean_player_name(dk_name)
                    
                    if clean_name == dk_clean_name or player_name == dk_name:
                        return row['TeamAbbrev'].strip()
            except Exception as e:
                print(f"Warning: Error reading {dk_file}: {e}")
                continue
    
    return None

def find_player_info_from_other_weeks(player_name, current_week, base_dir="2025"):
    """
    Find team and position for a player by checking other weeks' DKSalaries files.
    Returns (team, position) or (None, None) if not found.
    """
    # Get all available weeks
    all_weeks = []
    for item in os.listdir(base_dir):
        if item.startswith('WEEK') and os.path.isdir(os.path.join(base_dir, item)):
            week_num = int(item.replace('WEEK', ''))
            if week_num != current_week:  # Skip current week
                all_weeks.append(week_num)
    
    all_weeks.sort()
    
    # Check each week's DKSalaries file
    for week_num in all_weeks:
        week_path = os.path.join(base_dir, f'WEEK{week_num}')
        dk_files = [f for f in os.listdir(week_path) if f.startswith('DKSalaries') and f.endswith('.csv')]
        
        if dk_files:
            dk_file = os.path.join(week_path, dk_files[0])
            try:
                dk_df = pd.read_csv(dk_file)
                
                # Clean the player name for matching
                clean_name = clean_player_name(player_name)
                
                # Check if player exists in this week's DKSalaries
                for _, row in dk_df.iterrows():
                    dk_name = row['Name'].strip()
                    dk_clean_name = clean_player_name(dk_name)
                    
                    if clean_name == dk_clean_name or player_name == dk_name:
                        return row['TeamAbbrev'].strip(), row['Position'].strip()
            except Exception as e:
                print(f"Warning: Error reading {dk_file}: {e}")
                continue
    
    return None, None

def get_team_abbreviation_mapping():
    """
    Create a mapping from full team names to abbreviations.
    """
    return {
        'Arizona Cardinals': 'ARI',
        'Atlanta Falcons': 'ATL', 
        'Baltimore Ravens': 'BAL',
        'Buffalo Bills': 'BUF',
        'Carolina Panthers': 'CAR',
        'Chicago Bears': 'CHI',
        'Cincinnati Bengals': 'CIN',
        'Cleveland Browns': 'CLE',
        'Dallas Cowboys': 'DAL',
        'Denver Broncos': 'DEN',
        'Detroit Lions': 'DET',
        'Green Bay Packers': 'GB',
        'Houston Texans': 'HOU',
        'Indianapolis Colts': 'IND',
        'Jacksonville Jaguars': 'JAX',
        'Kansas City Chiefs': 'KC',
        'Las Vegas Raiders': 'LV',
        'Los Angeles Chargers': 'LAC',
        'Los Angeles Rams': 'LAR',
        'Miami Dolphins': 'MIA',
        'Minnesota Vikings': 'MIN',
        'New England Patriots': 'NE',
        'New Orleans Saints': 'NO',
        'New York Giants': 'NYG',
        'New York Jets': 'NYJ',
        'Philadelphia Eagles': 'PHI',
        'Pittsburgh Steelers': 'PIT',
        'San Francisco 49ers': 'SF',
        'Seattle Seahawks': 'SEA',
        'Tampa Bay Buccaneers': 'TB',
        'Tennessee Titans': 'TEN',
        'Washington Commanders': 'WAS'
    }

def load_week_data(week_path):
    """
    Load and process data for a specific week with enhanced team mapping.
    Returns dict with opponent -> position -> points data.
    """
    # Extract week number from path
    week_num = int(os.path.basename(week_path).replace('WEEK', ''))
    
    # Load NFL schedule
    schedule = load_nfl_schedule()
    team_mapping = get_team_abbreviation_mapping()
    
    # Find DKSalaries file
    dk_files = glob.glob(os.path.join(week_path, "DKSalaries*.csv"))
    if not dk_files:
        print(f"Warning: No DKSalaries file found in {week_path}")
        return {}
    
    dk_file = dk_files[0]
    
    # Find box_score_debug file
    box_score_file = os.path.join(week_path, "box_score_debug.csv")
    if not os.path.exists(box_score_file):
        print(f"Warning: No box_score_debug.csv found in {week_path}")
        return {}
    
    try:
        # Load DKSalaries data
        dk_df = pd.read_csv(dk_file)
        print(f"Loaded DKSalaries data: {len(dk_df)} players")
        
        # Load box score data
        box_df = pd.read_csv(box_score_file)
        print(f"Loaded box score data: {len(box_df)} players")
        
        # Create mapping from name to points using clean_player_name
        name_to_points = {}
        for _, row in box_df.iterrows():
            name = row['Name'].strip()
            points = row['DFS Total']
            # Use the clean_player_name function to handle name variations
            clean_name = clean_player_name(name)
            name_to_points[clean_name] = points
            # Also keep original name as fallback
            name_to_points[name] = points
        
        # Create mapping of players in DKSalaries to their teams
        dk_players = {}
        for _, row in dk_df.iterrows():
            name = row['Name'].strip()
            team = row['TeamAbbrev'].strip()
            position = row['Position'].strip()
            game_info = row['Game Info']
            
            if position == 'DST':
                continue
                
            clean_name = clean_player_name(name)
            dk_players[clean_name] = {
                'team': team,
                'position': position,
                'game_info': game_info
            }
            # Also store original name
            dk_players[name] = {
                'team': team,
                'position': position,
                'game_info': game_info
            }
        
        # Process all players from box score
        all_player_data = []
        processed_players = set()
        
        for _, row in box_df.iterrows():
            name = row['Name'].strip()
            points = row['DFS Total']
            
            # Skip if no points or already processed
            if points <= 0 or name in processed_players:
                continue
                
            processed_players.add(name)
            clean_name = clean_player_name(name)
            
            # Try to find team info
            player_team = None
            position = None
            opponent = None
            
            # First, try to find in current week's DKSalaries
            if clean_name in dk_players:
                player_info = dk_players[clean_name]
                player_team = player_info['team']
                position = player_info['position']
                opponent = get_opponent_team(player_team, player_info['game_info'])
            elif name in dk_players:
                player_info = dk_players[name]
                player_team = player_info['team']
                position = player_info['position']
                opponent = get_opponent_team(player_team, player_info['game_info'])
            else:
                # Player not in current week's DKSalaries, try to find team and position from other weeks
                player_team, position = find_player_info_from_other_weeks(name, week_num)
                
                if player_team and week_num in schedule:
                    # Find opponent using schedule
                    for full_team_name, abbrev in team_mapping.items():
                        if abbrev == player_team:
                            if full_team_name in schedule[week_num]:
                                opponent = team_mapping.get(schedule[week_num][full_team_name], schedule[week_num][full_team_name])
                            break
            
            if player_team and opponent and position and position != 'UNKNOWN':
                all_player_data.append({
                    'name': name,
                    'position': position,
                    'opponent': opponent,
                    'points': points
                })
                print(f"Added {name} ({position}) vs {opponent}: {points} points")
            else:
                print(f"Warning: Could not determine team/opponent for {name}")
        
        # Now filter to top performers per position per opponent
        opponent_data = defaultdict(lambda: defaultdict(list))
        
        # Group by opponent and position
        grouped_data = defaultdict(lambda: defaultdict(list))
        for player in all_player_data:
            grouped_data[player['opponent']][player['position']].append(player)
        
        # Apply top performer filtering
        for opponent, positions in grouped_data.items():
            for position, players in positions.items():
                # Sort by points descending
                players.sort(key=lambda x: x['points'], reverse=True)
                
                # Apply position-specific limits
                if position == 'QB':
                    # Top 1 QB
                    top_players = players[:1]
                elif position == 'RB':
                    # All RBs (for total points calculation)
                    top_players = players
                elif position == 'WR':
                    # Top 3 WRs
                    top_players = players[:3]
                elif position == 'TE':
                    # Top 1 TE
                    top_players = players[:1]
                else:
                    # For any other positions, take all
                    top_players = players
                
                # Add to final data
                for player in top_players:
                    opponent_data[opponent][position].append(player['points'])
                    print(f"Selected {player['name']} ({position}) vs {opponent}: {player['points']} points")
        
        return dict(opponent_data)
        
    except Exception as e:
        print(f"Error processing {week_path}: {e}")
        return {}

def calculate_totals(week_data_list, is_single_week=False):
    """
    Calculate total points given up by each team to each position.
    For single week: sum all points
    For multiple weeks: average the weekly sums
    """
    if is_single_week:
        # Single week: sum all points
        team_position_points = defaultdict(lambda: defaultdict(list))
        
        for week_data in week_data_list:
            for team, positions in week_data.items():
                for position, points_list in positions.items():
                    team_position_points[team][position].extend(points_list)
        
        # Calculate totals for all positions
        results = {}
        for team, positions in team_position_points.items():
            team_results = {}
            for position, points_list in positions.items():
                if points_list:
                    total_points = sum(points_list)
                    team_results[position] = round(total_points, 2)
                else:
                    team_results[position] = 0.0
            results[team] = team_results
        
        return results
    else:
        # Multiple weeks: calculate weekly sums, then average them
        weekly_totals = []
        
        for week_data in week_data_list:
            week_totals = {}
            for team, positions in week_data.items():
                team_totals = {}
                for position, points_list in positions.items():
                    if points_list:
                        total_points = sum(points_list)
                        team_totals[position] = total_points
                    else:
                        team_totals[position] = 0.0
                week_totals[team] = team_totals
            weekly_totals.append(week_totals)
        
        # Calculate averages across weeks
        results = {}
        all_teams = set()
        for week_total in weekly_totals:
            all_teams.update(week_total.keys())
        
        for team in all_teams:
            team_results = {}
            # Get all positions for this team
            all_positions = set()
            for week_total in weekly_totals:
                if team in week_total:
                    all_positions.update(week_total[team].keys())
            
            for position in all_positions:
                position_values = []
                for week_total in weekly_totals:
                    if team in week_total and position in week_total[team]:
                        position_values.append(week_total[team][position])
                
                if position_values:
                    avg_points = sum(position_values) / len(position_values)
                    team_results[position] = round(avg_points, 2)
                else:
                    team_results[position] = 0.0
            
            results[team] = team_results
        
        return results

def create_output_csv(results, output_path):
    """
    Create CSV with team vs position performance data.
    """
    # Get all unique teams and positions
    all_teams = sorted(results.keys())
    all_positions = set()
    for team_data in results.values():
        all_positions.update(team_data.keys())
    all_positions = sorted(all_positions)
    
    # Create DataFrame
    data = []
    for team in all_teams:
        row = {'Team': team}
        for position in all_positions:
            row[position] = results[team].get(position, 0.0)
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Reorder columns to have QBs, WRs, RBs, TEs first (exclude DST)
    position_order = ['QB', 'WR', 'RB', 'TE']
    other_positions = [pos for pos in all_positions if pos not in position_order and pos != 'DST']
    column_order = ['Team'] + position_order + other_positions
    
    # Only include columns that exist
    column_order = [col for col in column_order if col in df.columns]
    df = df[column_order]
    
    # Save to CSV
    df.to_csv(output_path, index=False)
    print(f"Results saved to {output_path}")
    print(f"Processed {len(all_teams)} teams and {len(all_positions)} positions")
    
    return df

def main():
    parser = argparse.ArgumentParser(description='Analyze position performance against teams')
    parser.add_argument('--week', type=int, 
                       help='Specific week to analyze (if not provided, analyzes all weeks)')
    parser.add_argument('--output-dir', type=str, default='2025',
                       help='Output directory (default: 2025)')
    
    args = parser.parse_args()
    
    if args.week is not None:
        # Analyze specific week only
        if args.week < 1:
            print("Error: Week must be 1 or greater")
            return
        
        weeks_to_analyze = [args.week]
        print(f"Analyzing week: {weeks_to_analyze}")
        output_week_dir = f"{args.output_dir}/WEEK{args.week}"
        output_filename = f"position_vs_team_week{args.week}.csv"
    else:
        # Analyze all weeks
        print("Analyzing all available weeks...")
        # Find all available week directories
        week_dirs = []
        for i in range(1, 25):  # Check up to week 24
            week_dir = f"{args.output_dir}/WEEK{i}"
            if os.path.exists(week_dir):
                week_dirs.append(i)
        
        if not week_dirs:
            print("Error: No week directories found")
            return
        
        weeks_to_analyze = week_dirs
        print(f"Found weeks: {weeks_to_analyze}")
        output_week_dir = args.output_dir
        output_filename = "position_vs_team_all_weeks.csv"
    
    # Load data for each week
    week_data_list = []
    for week_num in weeks_to_analyze:
        week_path = f"{args.output_dir}/WEEK{week_num}"
        if os.path.exists(week_path):
            print(f"\nProcessing {week_path}...")
            week_data = load_week_data(week_path)
            if week_data:
                week_data_list.append(week_data)
        else:
            print(f"Warning: {week_path} does not exist")
    
    if not week_data_list:
        print("Error: No valid week data found")
        return
    
    # Calculate totals (or averages for multiple weeks)
    if args.week is not None:
        print(f"\nCalculating totals for week {args.week}...")
        results = calculate_totals(week_data_list, is_single_week=True)
    else:
        print(f"\nCalculating averages from {len(week_data_list)} weeks...")
        results = calculate_totals(week_data_list, is_single_week=False)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_week_dir, exist_ok=True)
    
    # Save results
    output_path = os.path.join(output_week_dir, output_filename)
    df = create_output_csv(results, output_path)
    
    # Print summary
    print(f"\nSummary:")
    if args.week is not None:
        print(f"Analyzed week {args.week} data")
    else:
        print(f"Analyzed {len(weeks_to_analyze)} weeks of data")
    print(f"Found {len(results)} teams")
    print(f"Output saved to: {output_path}")
    
    # Show sample of results
    print(f"\nSample results:")
    print(df.head(10))

if __name__ == "__main__":
    main()
