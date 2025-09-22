# Standard library imports
import argparse
import copy
from dataclasses import dataclass
import random
import sys
from collections import Counter
from typing import Dict, List, Optional, Union, Tuple

# Third-party imports
import numpy as np
import pandas as pd
from tqdm.auto import tqdm

# Local imports
from utils import BYE_DICT, CITY_TO_TEAM, TEAM_DICT, TOTAL_DICT, clean_player_name


@dataclass
class Player:
    """A class to represent a Player with enhanced projection data"""
    name: str
    position: str
    salary: float
    projected_score: float
    bust_score: float
    boom_score: float
    bust_percentage: float
    boom_percentage: float
    team: str
    opponent: str
    game_info: str = ""
    dk_name: str = ""  # DraftKings name + ID for export

    @classmethod
    def from_espn_data(cls, player_df: Union[pd.DataFrame, pd.Series]) -> 'Player':
        """
        Create a Player instance from ESPN projection data
        
        Args:
            player_df: DataFrame row or Series containing player information
            
        Returns:
            Player instance
        
        Raises:
            ValueError: If required fields are missing
        """
        try:
            # Convert to series if DataFrame
            data = player_df.iloc[0] if isinstance(player_df, pd.DataFrame) else player_df

            # Handle both 'projected_points' (coarse mode) and 'projected_score' (fine mode)
            if "projected_points" in data:
                projected_score = float(data["projected_points"])
            elif "projected_score" in data:
                projected_score = float(data["projected_score"])
            else:
                raise KeyError("Neither 'projected_points' nor 'projected_score' found in data")

            # Get boom/bust data with fallback to 0 if not available
            bust_score = float(data.get("bust_score", 0))
            boom_score = float(data.get("boom_score", 0))
            bust_percentage = float(data.get("bust_percentage", 0))
            boom_percentage = float(data.get("boom_percentage", 0))

            return cls(
                name=data["player_name"],
                position=data["position"],
                salary=0.0,  # Will be set later from DraftKings data
                projected_score=projected_score,
                bust_score=bust_score,
                boom_score=boom_score,
                bust_percentage=bust_percentage,
                boom_percentage=boom_percentage,
                team=data["team"],
                opponent=data["opponent"],
                game_info="",  # Will be set later from DraftKings data
                dk_name=""  # Will be set later from DraftKings data
            )
        except KeyError as e:
            raise ValueError(f"Missing required field: {e}")

    @property
    def value(self) -> float:
        """Returns the value (points per thousand dollars) of a Player"""
        if self.salary > 0:
            return (self.projected_score / self.salary) * 1000
        return 0.0

    @property
    def risk_adjusted_score(self) -> float:
        """
        Returns a risk-adjusted score considering bust and boom scenarios
        
        Note: bust_percentage = probability of going BELOW bust_score
              boom_percentage = probability of going ABOVE boom_score
        
        If boom/bust data is not available (coarse mode), returns projected_score
        """
        # If boom/bust data is not available (all zeros), just return projected score
        if (self.bust_score == 0 and self.boom_score == 0 and 
            self.bust_percentage == 0 and self.boom_percentage == 0):
            return self.projected_score
        
        # Calculate expected value based on the probability distribution
        # For simplicity, we'll use a weighted average approach:
        # - If player goes below bust: use bust_score
        # - If player goes above boom: use boom_score  
        # - Otherwise: use projected_score (most likely scenario)
        
        # Probability of being in the "normal" range (between bust and boom)
        normal_probability = 100 - self.bust_percentage - self.boom_percentage
        
        return (self.bust_score * (self.bust_percentage / 100) + 
                self.projected_score * (normal_probability / 100) + 
                self.boom_score * (self.boom_percentage / 100))

    @property
    def upside_potential(self) -> float:
        """Returns the upside potential (boom score - projected score)"""
        # If boom data is not available (coarse mode), return 0
        if self.boom_score == 0:
            return 0.0
        return self.boom_score - self.projected_score

    def get_attribute(self, attr: str) -> float:
        """
        Get a specific attribute of the player
        
        Args:
            attr: The attribute to get ('value', 'projected_score', 'risk_adjusted_score', 'upside_potential')
            
        Returns:
            The requested attribute value
        """
        if attr == "projected_score":
            return self.projected_score
        elif attr == "value":
            return self.value
        elif attr == "risk_adjusted_score":
            return self.risk_adjusted_score
        elif attr == "upside_potential":
            return self.upside_potential
        raise ValueError(f"Invalid attribute: {attr}. Valid options are: value, projected_score, risk_adjusted_score, upside_potential")

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Player(name='{self.name}', position='{self.position}', salary={self.salary}, projected_score={self.projected_score})"


@dataclass
class Stack:
    """A class to represent a QB-WR/TE stack with enhanced analysis"""
    qb: Player
    wrte: Player

    def __hash__(self) -> int:
        """Make Stack hashable for use as dictionary key"""
        return hash((self.qb.name, self.wrte.name))

    def __eq__(self, other) -> bool:
        """Define equality for Stack objects"""
        if not isinstance(other, Stack):
            return False
        return self.qb.name == other.qb.name and self.wrte.name == other.wrte.name

    @property
    def salary(self) -> float:
        """Returns the total salary of the stack"""
        return self.qb.salary + self.wrte.salary

    @property
    def projected_score(self) -> float:
        """Returns the total projected score of the stack"""
        return self.qb.projected_score + self.wrte.projected_score

    @property
    def value(self) -> float:
        """Returns the total value of the stack"""
        return self.qb.value + self.wrte.value

    @property
    def risk_adjusted_score(self) -> float:
        """Returns the risk-adjusted score of the stack"""
        return self.qb.risk_adjusted_score + self.wrte.risk_adjusted_score

    @property
    def boom_score(self) -> float:
        """Returns the total boom score of the stack"""
        return self.qb.boom_score + self.wrte.boom_score

    @property
    def is_optimal_range(self) -> bool:
        """Returns True if stack salary is in optimal range ($10,000-$15,000)"""
        return 10000 <= self.salary <= 15000

    @property
    def stack_correlation(self) -> float:
        """Returns a correlation score based on team and position synergy"""
        # QB-WR stacks are generally more correlated than QB-TE
        base_correlation = 0.8 if self.wrte.position == "WR" else 0.6
        
        # Adjust based on boom percentage (probability of exceeding boom threshold)
        # Higher boom percentage = higher chance of both players having big games
        boom_adjustment = (self.qb.boom_percentage + self.wrte.boom_percentage) / 200
        
        return min(1.0, base_correlation + boom_adjustment)

    def get_attribute(self, attr: str) -> float:
        """
        Get a specific attribute of the stack
        
        Args:
            attr: The attribute to get ('value', 'projected_score', 'risk_adjusted_score', 'stack_correlation')
            
        Returns:
            float: The requested attribute value
        """
        attr = attr.lower()
        if attr == "value":
            return self.value
        elif attr == "projected_score":
            return self.projected_score
        elif attr == "risk_adjusted_score":
            return self.risk_adjusted_score
        elif attr == "stack_correlation":
            return self.stack_correlation
        return self.projected_score

    def __str__(self) -> str:
        return f"Stack(QB={self.qb.name}, {self.wrte.position}={self.wrte.name}, Score={self.projected_score:.2f}, Salary=${self.salary:,.0f})"

    def __repr__(self) -> str:
        return f"Stack(QB={self.qb.name}, {self.wrte.position}={self.wrte.name}, Score={self.projected_score:.2f})"


class LineUp:
    """A class to represent a DraftKings lineup with enhanced validation"""
    SALARY_CAP = 50000
    MAX_PLAYERS_PER_TEAM = 3

    def __init__(self, qb: Player, rb1: Player, rb2: Player, wr1: Player, wr2: Player, 
                 wr3: Player, te: Player, flex: Player, dst: Player):
        """Initialize a lineup with all required positions"""
        self.players = {
            "QB": qb,
            "RB1": rb1,
            "RB2": rb2,
            "WR1": wr1,
            "WR2": wr2,
            "WR3": wr3,
            "TE": te,
            "FLEX": flex,
            "DST": dst
        }
        self._salary = None
        self._total = None
        self._teams = None
        self._team_diversity_score = None

    def _clear_cache(self) -> None:
        """Clear all cached values when players are modified"""
        self._salary = None
        self._total = None
        self._teams = None
        self._team_diversity_score = None

    @property
    def salary(self) -> float:
        """Returns the total salary of the lineup"""
        if self._salary is None:
            self._salary = sum(player.salary for player in self.players.values())
        return self._salary

    @property
    def projected_score(self) -> float:
        """Returns the total projected score of the lineup"""
        if self._total is None:
            self._total = sum(player.projected_score for player in self.players.values())
        return self._total

    @property
    def risk_adjusted_score(self) -> float:
        """Returns the risk-adjusted score of the lineup"""
        return sum(player.risk_adjusted_score for player in self.players.values())

    @property
    def boom_score(self) -> float:
        """Returns the pure boom score of the lineup (sum of all players' boom scores)"""
        return sum(player.boom_score for player in self.players.values())

    @property
    def bust_score(self) -> float:
        """Returns the pure bust score of the lineup (sum of all players' bust scores)"""
        return sum(player.bust_score for player in self.players.values())

    @property
    def avg_boom_percentage(self) -> float:
        """Returns the average boom percentage across all players in the lineup"""
        return sum(player.boom_percentage for player in self.players.values()) / len(self.players)

    @property
    def avg_bust_percentage(self) -> float:
        """Returns the average bust percentage across all players in the lineup"""
        return sum(player.bust_percentage for player in self.players.values()) / len(self.players)

    @property
    def teams(self) -> set:
        """Returns the set of teams in the lineup"""
        if self._teams is None:
            self._teams = set(player.team for player in self.players.values())
        return self._teams

    @property
    def team_diversity_score(self) -> float:
        """Returns a score based on team diversity (6-7 teams is optimal, 5-8 small penalty, 4-9 larger penalty)"""
        if self._team_diversity_score is None:
            num_teams = len(self.teams)
            if num_teams < 4:
                self._team_diversity_score = 0.0  # Too concentrated
            elif num_teams == 4:
                self._team_diversity_score = 0.3  # Larger penalty
            elif num_teams == 5:
                self._team_diversity_score = 0.7  # Small penalty
            elif 6 <= num_teams <= 7:
                self._team_diversity_score = 1.0  # Optimal range
            elif num_teams == 8:
                self._team_diversity_score = 0.7  # Small penalty
            elif num_teams == 9:
                self._team_diversity_score = 0.3  # Larger penalty
            else:
                self._team_diversity_score = 0.0  # Too spread out
        return self._team_diversity_score

    @property
    def flex_position_quality(self) -> float:
        """Returns a score based on FLEX position quality (WR preferred)"""
        flex_player = self.players["FLEX"]
        if flex_player.position == "WR":
            return 1.0
        elif flex_player.position == "RB":
            return 0.7
        elif flex_player.position == "TE":
            return 0.6
        return 0.5

    @property
    def upside_potential_score(self) -> float:
        """Returns a score based on the lineup's boom potential (high upside focus)"""
        total_upside = 0.0
        total_boom_percentage = 0.0
        
        for player in self.players.values():
            # Calculate upside potential (boom score - projected score)
            # This represents the additional points possible if player hits boom scenario
            player_upside = player.boom_score - player.projected_score
            total_upside += player_upside
            
            # Sum boom percentages (probability of going ABOVE boom score)
            # Higher percentage = higher chance of exceeding boom threshold
            total_boom_percentage += player.boom_percentage
        
        # Normalize upside potential (average upside per player)
        avg_upside = total_upside / len(self.players)
        
        # Normalize boom percentage (average boom percentage)
        avg_boom_percentage = total_boom_percentage / len(self.players)
        
        # Combine upside potential and boom percentage for final score
        # Higher scores for lineups with:
        # 1. High upside potential (big gap between projected and boom)
        # 2. High boom percentages (higher probability of exceeding boom threshold)
        upside_score = (avg_upside / 10.0) * 0.7 + (avg_boom_percentage / 100.0) * 0.3
        
        return min(1.0, max(0.0, upside_score))  # Clamp between 0 and 1

    def duplicates(self) -> bool:
        """Returns True if there are duplicate players in the lineup"""
        names = [player.name for player in self.players.values()]
        return len(names) != len(set(names))

    def players_on_same_team(self, threshold=MAX_PLAYERS_PER_TEAM) -> bool:
        """Returns True if too many players are on the same team"""
        team_counts = Counter(player.team for player in self.players.values())
        return any(count > threshold for count in team_counts.values())

    def has_sub_4000_player(self) -> bool:
        """Returns True if lineup has at least one player at or below $4000 salary (excluding defense)"""
        for pos, player in self.players.items():
            if pos != "DST" and player.salary <= 4000:
                return True
        return False

    def is_valid(self) -> bool:
        """Returns True if the lineup meets all DraftKings requirements and quality thresholds"""
        return (self.salary <= self.SALARY_CAP and 
                not self.duplicates() and 
                not self.players_on_same_team() and
                self.has_sub_4000_player() and
                self.salary >= 48000 and  # Minimum salary utilization
                self.team_diversity_score >= 0.3)  # Team diversity requirement
    
    def is_valid_fast(self, total_salary: float, player_names: set, teams: set, team_counts: dict, has_sub_4000: bool) -> bool:
        """Fast validation using pre-computed values to avoid redundant calculations"""
        return (total_salary <= self.SALARY_CAP and 
                len(player_names) == 9 and  # No duplicates
                not any(count > self.MAX_PLAYERS_PER_TEAM for count in team_counts.values()) and
                has_sub_4000 and
                total_salary >= 48000 and  # Minimum salary utilization
                len(teams) >= 4)  # Team diversity requirement (simplified)

    def get_quality_score(self, optimize_by: str = "projected") -> float:
        """Returns a composite quality score for the lineup - prioritizing specified score type"""
        if not self.is_valid():
            return 0.0
        
        # Heavy penalty for insufficient salary utilization
        if self.salary < 48000:
            return 0.0  # Reject lineups below minimum salary
        
        # Choose which score to optimize by
        if optimize_by == "risk_adjusted":
            primary_score = self.risk_adjusted_score
        elif optimize_by == "boom_score":
            # Fall back to projected score if boom score is 0 (coarse mode data)
            primary_score = self.boom_score if self.boom_score > 0 else self.projected_score
        else:  # default to projected
            primary_score = self.projected_score
        
        # Primary: Chosen score (65% weight)
        primary_score_weight = primary_score * 0.65
        
        # Secondary: Salary utilization bonus (15% weight)
        # Reward lineups that use most of the salary cap, but not as heavily
        salary_utilization = min(1.0, self.salary / 50000)  # Normalize to 0-1
        salary_bonus = salary_utilization * 15  # Up to 15 points for full utilization
        
        # Tertiary: Salary efficiency (5% weight) - use primary score for efficiency calculation
        salary_efficiency = (primary_score / self.salary) * 10000 * 0.05
        
        # Quaternary: Pattern analysis bonuses (15% combined weight)
        diversity_bonus = self.team_diversity_score * 0.05
        flex_bonus = self.flex_position_quality * 0.05
        upside_bonus = self.upside_potential_score * 0.05
        
        return primary_score_weight + salary_bonus + salary_efficiency + diversity_bonus + flex_bonus + upside_bonus

    def to_dict(self, optimize_by: str = "projected") -> dict:
        """Convert lineup to dictionary for export"""
        return {
            "QB": self.players["QB"].dk_name if self.players["QB"].dk_name else self.players["QB"].name,
            "RB1": self.players["RB1"].dk_name if self.players["RB1"].dk_name else self.players["RB1"].name,
            "RB2": self.players["RB2"].dk_name if self.players["RB2"].dk_name else self.players["RB2"].name,
            "WR1": self.players["WR1"].dk_name if self.players["WR1"].dk_name else self.players["WR1"].name,
            "WR2": self.players["WR2"].dk_name if self.players["WR2"].dk_name else self.players["WR2"].name,
            "WR3": self.players["WR3"].dk_name if self.players["WR3"].dk_name else self.players["WR3"].name,
            "TE": self.players["TE"].dk_name if self.players["TE"].dk_name else self.players["TE"].name,
            "FLEX": self.players["FLEX"].dk_name if self.players["FLEX"].dk_name else self.players["FLEX"].name,
            "DST": self.players["DST"].dk_name if self.players["DST"].dk_name else self.players["DST"].name,
            "Salary": self.salary,
            "Projected_Score": self.projected_score,
            "Risk_Adjusted_Score": self.risk_adjusted_score,
            "Boom_Score": self.boom_score,
            "Bust_Score": self.bust_score,
            "Avg_Boom_Percentage": self.avg_boom_percentage,
            "Avg_Bust_Percentage": self.avg_bust_percentage,
            "Quality_Score": self.get_quality_score(optimize_by),
            "Teams": len(self.teams)
        }

    def __str__(self) -> str:
        return f"Lineup(Score={self.projected_score:.2f}, Salary=${self.salary:,.0f}, Teams={len(self.teams)})"

    def __repr__(self) -> str:
        return f"Lineup(Score={self.projected_score:.2f}, Salary=${self.salary:,.0f})"


class AdvancedLineupGenerator:
    """Advanced lineup generator incorporating pattern analysis learnings"""
    
    def __init__(self, projections_df: pd.DataFrame, dk_data: pd.DataFrame = None, week_folder: str = None, optimize_by: str = "projected"):
        """
        Initialize the lineup generator
        
        Args:
            projections_df: DataFrame with ESPN projection data
            dk_data: Optional DraftKings data for salary information
            week_folder: Path to the week folder for saving merged data
            optimize_by: Which score to optimize by ("projected", "risk_adjusted", or "boom_score")
        """
        self.projections_df = projections_df
        self.dk_data = dk_data
        self.week_folder = week_folder
        self.optimize_by = optimize_by
        self.players = self._load_players()
        
    def _load_players(self) -> Dict[str, List[Player]]:
        """Load players from projections data, organized by position"""
        players = {}
        
        if self.dk_data is None:
            # If no DraftKings data, include all players (for testing)
            for _, row in self.projections_df.iterrows():
                try:
                    player = Player.from_espn_data(row)
                    if player.position not in players:
                        players[player.position] = []
                    players[player.position].append(player)
                except Exception as e:
                    print(f"Error loading player {row.get('player_name', 'Unknown')}: {e}")
                    continue
            print(f"✓ Loaded {sum(len(pos_players) for pos_players in players.values())} players (no DK data)")
            return players
        
        # Create a clean version of both dataframes for merging
        espn_clean = self.projections_df.copy()
        
        # Handle position mapping for ESPN to DraftKings
        espn_clean['position_clean'] = espn_clean['position'].replace({
            'D/ST': 'DST',
            'WR, CB': 'WR'
        })
        
        # Clean names using comprehensive cleaning function
        espn_clean['name_clean'] = espn_clean['player_name'].apply(clean_player_name)
        # Special handling for D/ST positions - remove "D/ST" suffix after general cleaning
        dst_mask = espn_clean['position'] == 'D/ST'
        espn_clean.loc[dst_mask, 'name_clean'] = espn_clean.loc[dst_mask, 'name_clean'].str.replace(' d/st', '', case=False)
        
        dk_clean = self.dk_data.copy()
        dk_clean['name_clean'] = dk_clean['Name'].apply(clean_player_name)
        dk_clean['position_clean'] = dk_clean['Position']
        
        # Merge the dataframes on cleaned names AND positions
        merged_df = pd.merge(espn_clean, dk_clean, on=['name_clean', 'position_clean'], how='inner')
        
        print(f"✓ Found {len(merged_df)} matching players between ESPN and DraftKings")
        
        # Save merged data for debugging
        if len(merged_df) > 0:
            # Create a clean merged CSV with relevant columns
            merged_export = merged_df[[
                'player_name',  # ESPN player name
                'Name + ID',    # DraftKings name + ID
                'team',         # ESPN team
                'Salary',       # DraftKings salary
                'projected_score', 'bust_score', 'boom_score',  # ESPN projections
                'bust_percentage', 'boom_percentage',           # ESPN percentages
                'position',     # ESPN position
                'opponent',     # ESPN opponent
                'Game Info'     # DraftKings game info
            ]].copy()
            
            # Rename columns for clarity
            merged_export.columns = [
                'Player_Name', 'DK_Name_ID', 'Team', 'Salary', 
                'Projected_Score', 'Bust_Score', 'Boom_Score',
                'Bust_Percentage', 'Boom_Percentage', 'Position', 
                'Opponent', 'Game_Info'
            ]
            
            # Save to the week folder
            import os
            if self.week_folder:
                merged_filename = os.path.join(self.week_folder, 'merged_player_data.csv')
            else:
                merged_filename = 'merged_player_data.csv'
            merged_export.to_csv(merged_filename, index=False)
            print(f"✓ Saved merged player data to: {merged_filename}")
        
        # Create Player objects from merged data
        for _, row in merged_df.iterrows():
            try:
                player = Player.from_espn_data(row)
                player.salary = float(row['Salary'])
                if 'Game Info' in row:
                    player.game_info = row['Game Info']
                if 'Name + ID' in row:
                    player.dk_name = row['Name + ID']
                
                if player.position not in players:
                    players[player.position] = []
                players[player.position].append(player)
                
            except Exception as e:
                print(f"Error creating player from merged data: {e}")
                continue
        
        total_loaded = sum(len(pos_players) for pos_players in players.values())
        total_espn = len(self.projections_df)
        skipped = total_espn - total_loaded
        
        print(f"✓ Loaded {total_loaded} players with valid salary data")
        if skipped > 0:
            print(f"⚠️  Skipped {skipped} players without DraftKings salary data")
        
        # Perform player pool validation
        self._validate_player_pool(dk_clean, merged_df)
        
        return players
    
    def _validate_player_pool(self, dk_data: pd.DataFrame, merged_data: pd.DataFrame) -> None:
        """
        Validate that key players are included in the merged data based on salary thresholds.
        Uses DKSalaries as the source of truth and checks for missing players.
        """
        print("\n" + "="*60)
        print("PLAYER POOL VALIDATION")
        print("="*60)
        
        # Define salary thresholds for each position
        salary_thresholds = {
            'QB': 5000,
            'RB': 4500,
            'WR': 4000,
            'TE': 3000,
            'DST': 0  # Will check for at least 10 DSTs regardless of salary
        }
        
        missing_players = {}
        validation_results = {}
        
        for position, threshold in salary_thresholds.items():
            # Get all players from DKSalaries that meet the salary threshold
            if position == 'DST':
                dk_position_players = dk_data[dk_data['Position'] == position]
                total_dst = len(dk_position_players)
                validation_results[position] = {
                    'total_available': total_dst,
                    'threshold_met': total_dst >= 10,
                    'required': 10
                }
            else:
                dk_position_players = dk_data[
                    (dk_data['Position'] == position) & 
                    (dk_data['Salary'] >= threshold)
                ]
                total_meeting_threshold = len(dk_position_players)
                validation_results[position] = {
                    'total_available': total_meeting_threshold,
                    'threshold': threshold,
                    'threshold_met': total_meeting_threshold > 0
                }
            
            # Get merged players for this position
            if position == 'DST':
                merged_position_players = merged_data[merged_data['position_clean'] == position]
            else:
                merged_position_players = merged_data[
                    (merged_data['position_clean'] == position) & 
                    (merged_data['Salary'] >= threshold)
                ]
            
            merged_count = len(merged_position_players)
            
            # Find missing players
            if position == 'DST':
                dk_player_names = set(dk_position_players['name_clean'].tolist())
                merged_player_names = set(merged_position_players['name_clean'].tolist())
                missing_names = dk_player_names - merged_player_names
                
                if missing_names:
                    missing_players[position] = []
                    for _, player in dk_position_players.iterrows():
                        if player['name_clean'] in missing_names:
                            missing_players[position].append({
                                'name': player['Name'],
                                'salary': player['Salary'],
                                'clean_name': player['name_clean']
                            })
            else:
                dk_player_names = set(dk_position_players['name_clean'].tolist())
                merged_player_names = set(merged_position_players['name_clean'].tolist())
                missing_names = dk_player_names - merged_player_names
                
                if missing_names:
                    missing_players[position] = []
                    for _, player in dk_position_players.iterrows():
                        if player['name_clean'] in missing_names:
                            missing_players[position].append({
                                'name': player['Name'],
                                'salary': player['Salary'],
                                'clean_name': player['name_clean']
                            })
            
            # Update validation results
            validation_results[position]['merged_count'] = merged_count
            validation_results[position]['missing_count'] = len(missing_players.get(position, []))
        
        # Print validation results
        for position, results in validation_results.items():
            print(f"\n{position} VALIDATION:")
            if position == 'DST':
                print(f"  Total DSTs available: {results['total_available']}")
                print(f"  Required minimum: {results['required']}")
                print(f"  Successfully merged: {results['merged_count']}")
                print(f"  Missing: {results['missing_count']}")
                
                if results['missing_count'] > 0:
                    print(f"  ⚠️  Missing DSTs:")
                    for player in missing_players[position]:
                        print(f"    - {player['name']} (${player['salary']})")
                else:
                    print(f"  ✅ All DSTs successfully merged")
                    
                if not results['threshold_met']:
                    print(f"  ⚠️  WARNING: Less than {results['required']} DSTs available in DKSalaries")
            else:
                print(f"  Salary threshold: ${results['threshold']}")
                print(f"  Players meeting threshold: {results['total_available']}")
                print(f"  Successfully merged: {results['merged_count']}")
                print(f"  Missing: {results['missing_count']}")
                
                if results['missing_count'] > 0:
                    print(f"  ⚠️  Missing {position}s:")
                    for player in missing_players[position]:
                        print(f"    - {player['name']} (${player['salary']})")
                else:
                    print(f"  ✅ All {position}s above ${results['threshold']} successfully merged")
        
        # Overall summary
        total_missing = sum(results['missing_count'] for results in validation_results.values())
        print(f"\n" + "="*60)
        print(f"VALIDATION SUMMARY:")
        print(f"Total missing players: {total_missing}")
        
        if total_missing == 0:
            print("✅ All key players successfully merged!")
        else:
            print(f"⚠️  {total_missing} key players missing from merged data")
            print("Consider reviewing name matching logic or ESPN projections data")
        
        print("="*60 + "\n")

    
    def find_optimal_stacks(self, min_salary: int = 10000, max_salary: int = 15000) -> List[Stack]:
        """
        Find optimal QB-WR/TE stacks using the 4-stack strategy:
        - 2 stacks with highest projected points
        - 2 stacks with best value (points per dollar)
        
        Args:
            min_salary: Minimum stack salary
            max_salary: Maximum stack salary
            
        Returns:
            List of 4 optimal stacks
        """
        stacks = []
        
        # Get QBs and WR/TEs
        qbs = self.players.get('QB', [])
        wrs = self.players.get('WR', [])
        tes = self.players.get('TE', [])
        
        # Create all possible QB-WR combinations
        for qb in qbs:
            for wr in wrs:
                if qb.team == wr.team:  # Same team stack
                    stack = Stack(qb, wr)
                    if min_salary <= stack.salary <= max_salary:
                        stacks.append(stack)
        
        # Create QB-TE combinations (less common but still valuable)
        for qb in qbs:
            for te in tes:
                if qb.team == te.team:  # Same team stack
                    stack = Stack(qb, te)
                    if min_salary <= stack.salary <= max_salary:
                        stacks.append(stack)
        
        if not stacks:
            return []
        
        # Sort by projected score for highest points stacks
        stacks_by_points = sorted(stacks, key=lambda s: s.boom_score if self.optimize_by == "boom_score" else s.projected_score, reverse=True)
        
        # Sort by value (points per dollar) for best value stacks
        stacks_by_value = sorted(stacks, key=lambda s: s.value, reverse=True)
        
        # Select 2 highest projected point stacks
        top_points_stacks = stacks_by_points[:2]
        
        # Select 2 best value stacks (avoiding duplicates)
        top_value_stacks = []
        for stack in stacks_by_value:
            if stack not in top_points_stacks and len(top_value_stacks) < 2:
                top_value_stacks.append(stack)
        
        # Combine the stacks
        optimal_stacks = top_points_stacks + top_value_stacks
        
        # If we don't have 4 unique stacks, fill with additional high-value stacks
        if len(optimal_stacks) < 4:
            remaining_stacks = [s for s in stacks if s not in optimal_stacks]
            remaining_stacks.sort(key=lambda s: s.value, reverse=True)
            optimal_stacks.extend(remaining_stacks[:4-len(optimal_stacks)])
        
        return optimal_stacks[:4]
    
    def generate_lineup_from_stack(self, stack: Stack, num_lineups: int = 1) -> List[LineUp]:
        """
        Generate lineups starting from a given stack using continuous improvement strategy
        
        Args:
            stack: The QB-WR/TE stack to build around
            num_lineups: Number of lineups to generate
            
        Returns:
            List of generated lineups
        """
        lineups = []
        attempts = 0
        max_attempts = 500000  # Generate many attempts to find the best lineups
        
        # Pre-filter players by position - prioritize the specified score type, then salary (for better utilization)
        if self.optimize_by == "risk_adjusted":
            score_attr = "risk_adjusted_score"
        elif self.optimize_by == "boom_score":
            score_attr = "boom_score"
        else:  # default to projected
            score_attr = "projected_score"
        
        # Pre-compute and cache player lists to avoid repeated sorting
        all_rbs = self.players.get('RB', [])
        all_wrs = self.players.get('WR', [])
        all_tes = self.players.get('TE', [])
        all_dsts = self.players.get('D/ST', [])
        
        # Pre-sort and filter candidates once
        rb_candidates = sorted([p for p in all_rbs if p.name != stack.qb.name and p.name != stack.wrte.name], 
                              key=lambda p: (getattr(p, score_attr), p.salary), reverse=True)[:30]
        wr_candidates = sorted([p for p in all_wrs if p.name != stack.qb.name and p.name != stack.wrte.name], 
                              key=lambda p: (getattr(p, score_attr), p.salary), reverse=True)[:30]
        te_candidates = sorted([p for p in all_tes if p.name != stack.qb.name and p.name != stack.wrte.name], 
                              key=lambda p: (getattr(p, score_attr), p.salary), reverse=True)[:20]
        dst_candidates = sorted(all_dsts, 
                               key=lambda p: (getattr(p, score_attr), p.salary), reverse=True)[:15]
        
        # Pre-compute top pools to avoid repeated sorting in the loop
        # Top 20 RBs by projected score
        top_rb_by_points = sorted(rb_candidates, key=lambda p: p.projected_score, reverse=True)[:20]
        # Top 20 RBs by value ratio
        top_rb_by_value = sorted(rb_candidates, key=lambda p: p.projected_score / p.salary, reverse=True)[:20]
        # Combine and deduplicate by player name
        top_rb_pool = []
        seen_names = set()
        for player in top_rb_by_points + top_rb_by_value:
            if player.name not in seen_names:
                top_rb_pool.append(player)
                seen_names.add(player.name)
        # Fallback to all candidates if pool is too small
        if len(top_rb_pool) < 5:
            top_rb_pool = rb_candidates
        
        # Top 20 WRs by projected score
        top_wr_by_points = sorted(wr_candidates, key=lambda p: p.projected_score, reverse=True)[:20]
        # Top 20 WRs by value ratio
        top_wr_by_value = sorted(wr_candidates, key=lambda p: p.projected_score / p.salary, reverse=True)[:20]
        # Combine and deduplicate by player name
        top_wr_pool = []
        seen_names = set()
        for player in top_wr_by_points + top_wr_by_value:
            if player.name not in seen_names:
                top_wr_pool.append(player)
                seen_names.add(player.name)
        # Fallback to all candidates if pool is too small
        if len(top_wr_pool) < 5:
            top_wr_pool = wr_candidates
        
        # Top 20 TEs by projected score
        top_te_by_points = sorted(te_candidates, key=lambda p: p.projected_score, reverse=True)[:20]
        # Top 20 TEs by value ratio
        top_te_by_value = sorted(te_candidates, key=lambda p: p.projected_score / p.salary, reverse=True)[:20]
        # Combine and deduplicate by player name
        top_te_pool = []
        seen_names = set()
        for player in top_te_by_points + top_te_by_value:
            if player.name not in seen_names:
                top_te_pool.append(player)
                seen_names.add(player.name)
        # Fallback to all candidates if pool is too small
        if len(top_te_pool) < 3:
            top_te_pool = te_candidates
        
        # Get opponent team from stack QB
        stack_opponent = stack.qb.opponent
        
        # Filter out DSTs playing against stack QB's team
        filtered_dst_candidates = [dst for dst in dst_candidates if dst.team != stack_opponent]
        
        # Top 20 DSTs by projected score
        top_dst_by_points = sorted(filtered_dst_candidates, key=lambda p: p.projected_score, reverse=True)[:20]
        # Top 20 DSTs by value ratio 
        top_dst_by_value = sorted(filtered_dst_candidates, key=lambda p: p.projected_score / p.salary, reverse=True)[:20]
        # Combine and deduplicate by player name
        top_dst_pool = []
        seen_names = set()
        for player in top_dst_by_points + top_dst_by_value:
            if player.name not in seen_names:
                top_dst_pool.append(player)
                seen_names.add(player.name)
        # Fallback to all filtered candidates if pool is too small
        if len(top_dst_pool) < 3:
            top_dst_pool = filtered_dst_candidates
        
        # Use a more flexible approach: generate random numbers on-demand but with optimized random generation
        # This avoids the mismatch between pre-computed indices and actual iteration needs
        with tqdm(total=max_attempts, desc=f"Stack {stack.qb.name} + {stack.wrte.name}") as pbar:
            while attempts < max_attempts:
                # Generate random selections efficiently (still much faster than sorting)
                rb1, rb2 = random.sample(top_rb_pool, 2)
                wr1, wr2, wr3 = random.sample(top_wr_pool, 3)
                te = random.choice(top_te_pool)
                dst = random.choice(top_dst_pool)
                
                # Pre-compute FLEX candidates more efficiently
                # Create sets for faster lookup
                used_wr_names = {wr1.name, wr2.name, wr3.name}
                used_rb_names = {rb1.name, rb2.name}
                
                # Determine FLEX position (prefer WR but allow RB/TE)
                flex_candidates = []
                if stack.wrte.position == "WR":
                    # If stack has WR, use TE as FLEX or add another WR
                    flex_candidates.append(te)
                    flex_candidates.extend([p for p in top_wr_pool if p.name not in used_wr_names])
                else:
                    # If stack has TE, use WR as FLEX
                    flex_candidates.extend([p for p in top_wr_pool if p.name not in used_wr_names])
                
                # Add RB options for FLEX
                flex_candidates.extend([p for p in top_rb_pool if p.name not in used_rb_names])
                
                # Add TE options for FLEX if not already included
                if stack.wrte.position != "TE":
                    flex_candidates.extend([p for p in top_te_pool if p.name != te.name])
                
                # Use random selection for FLEX (still efficient since candidates list is small)
                flex = random.choice(flex_candidates[:10]) if flex_candidates else te
                
                # Create lineup - ensure stack WR/TE is included
                if stack.wrte.position == "WR":
                    # If stack has WR, ensure it's included in WR positions
                    if stack.wrte.name not in [wr1.name, wr2.name, wr3.name]:
                        # Replace the lowest scoring WR with the stack WR
                        if wr3.projected_score <= wr2.projected_score and wr3.projected_score <= wr1.projected_score:
                            wr3 = stack.wrte
                        elif wr2.projected_score <= wr1.projected_score:
                            wr2 = stack.wrte
                        else:
                            wr1 = stack.wrte
                else:
                    # If stack has TE, use it as TE
                    te = stack.wrte
                
                lineup = LineUp(stack.qb, rb1, rb2, wr1, wr2, wr3, te, flex, dst)
                
                # Fast validation checks first (most likely to fail)
                # Use the lineup's actual salary calculation to ensure consistency
                if lineup.salary > LineUp.SALARY_CAP:
                    continue
                
                # Quick minimum salary check
                if lineup.salary < 48000:
                    continue
                
                # Check for sub-$4000 player (excluding defense)
                has_sub_4000 = any(p.salary <= 4000 for p in [stack.qb, rb1, rb2, wr1, wr2, wr3, te, flex])
                if not has_sub_4000:
                    continue
                
                # Check for duplicates (fast set comparison)
                player_names = {stack.qb.name, rb1.name, rb2.name, wr1.name, wr2.name, wr3.name, te.name, flex.name, dst.name}
                if len(player_names) != 9:  # Should have 9 unique names
                    continue
                
                # Check team diversity (count unique teams)
                teams = {stack.qb.team, rb1.team, rb2.team, wr1.team, wr2.team, wr3.team, te.team, flex.team, dst.team}
                if len(teams) < 4:  # Too concentrated
                    continue
                
                # Check for too many players on same team
                from collections import Counter
                team_counts = Counter([stack.qb.team, rb1.team, rb2.team, wr1.team, wr2.team, wr3.team, te.team, flex.team, dst.team])
                if any(count > LineUp.MAX_PLAYERS_PER_TEAM for count in team_counts.values()):
                    continue
                
                # If we get here, lineup passed quick validation
                # Now check for duplicates with existing lineups (more expensive check)
                if not any(self._lineups_equal(l, lineup) for l in lineups):
                    attempts += 1
                    pbar.update(1)
                    
                    # Continuous improvement strategy
                    if len(lineups) < num_lineups:
                        # If we haven't filled our quota yet, just add the lineup
                        lineups.append(lineup)
                    else:
                        # We have our quota, check if this lineup is better than the worst one
                        worst_lineup = min(lineups, key=lambda l: l.projected_score)
                        if lineup.projected_score > worst_lineup.projected_score:
                            # Replace the worst lineup with this better one
                            lineups.remove(worst_lineup)
                            lineups.append(lineup)
                
                # Continue to next iteration regardless of validation result
        
        # Sort lineups by quality score (best first)
        lineups.sort(key=lambda l: l.get_quality_score(self.optimize_by), reverse=True)
        return lineups
    
    def generate_multiple_lineups(self, num_lineups: int = 20, stacks_per_lineup: int = 1) -> List[LineUp]:
        """
        Generate multiple lineups using the 4-stack strategy with equal representation
        
        Args:
            num_lineups: Final number of lineups to return (must be divisible by 4)
            stacks_per_lineup: Number of stacks to use per lineup (usually 1)
            
        Returns:
            List of generated lineups with equal stack representation
        """
        print("🔍 Applying sub-$4000 player requirement: All lineups must include at least 1 player at or below $4000 salary (excluding defense)")
        
        # Find optimal stacks using 4-stack strategy
        optimal_stacks = self.find_optimal_stacks()
        
        if not optimal_stacks:
            print("No optimal stacks found!")
            return []
        
        # Ensure we have exactly 4 stacks
        if len(optimal_stacks) != 4:
            print(f"Warning: Expected 4 stacks, found {len(optimal_stacks)}")
            if len(optimal_stacks) < 4:
                return []
        
        print(f"Found {len(optimal_stacks)} optimal stacks:")
        print("Top 2 by Projected Points:")
        for i, stack in enumerate(optimal_stacks[:2]):
            print(f"  {i+1}. {stack} (Value: {stack.value:.2f})")
        
        print("Top 2 by Value (Points per Dollar):")
        for i, stack in enumerate(optimal_stacks[2:4]):
            print(f"  {i+1}. {stack} (Value: {stack.value:.2f})")
        
        # Calculate lineups per stack to ensure equal representation
        lineups_per_stack = num_lineups // 4
        if num_lineups % 4 != 0:
            print(f"Warning: {num_lineups} is not divisible by 4. Using {lineups_per_stack * 4} lineups instead.")
            num_lineups = lineups_per_stack * 4
        
        print(f"Generating {num_lineups} lineups total ({lineups_per_stack} per stack)...")
        
        # Generate lineups for each stack
        all_lineups = []
        stack_lineups = {}  # Track lineups by stack
        
        for i, stack in enumerate(optimal_stacks):
            print(f"Generating lineups for Stack {i+1}: {stack}")
            # Generate more lineups than needed to ensure we get enough quality ones
            generated_for_stack = self.generate_lineup_from_stack(stack, lineups_per_stack * 3)
            
            # Sort by quality and take the best ones for this stack
            generated_for_stack.sort(key=lambda l: l.get_quality_score(self.optimize_by), reverse=True)
            stack_lineups[stack] = generated_for_stack[:lineups_per_stack]
            all_lineups.extend(stack_lineups[stack])
        
        print(f"Generated {len(all_lineups)} total lineups ({lineups_per_stack} per stack)")
        
        # Verify equal representation
        print("\nStack Representation:")
        for i, stack in enumerate(optimal_stacks):
            count = len(stack_lineups[stack])
            print(f"  Stack {i+1}: {count} lineups")
        
        # Sort all lineups by quality for final ordering
        all_lineups.sort(key=lambda l: l.get_quality_score(self.optimize_by), reverse=True)
        
        # Analyze quality progression
        print("\nQuality Analysis:")
        
        # Determine which score to display based on optimization target
        if self.optimize_by == "risk_adjusted":
            score_attr = "risk_adjusted_score"
            score_label = "Risk_Adjusted_Score"
        elif self.optimize_by == "boom_score":
            score_attr = "boom_score"
            score_label = "Boom_Score"
        else:  # default to projected
            score_attr = "projected_score"
            score_label = "Projected_Score"
        
        for i in range(0, min(20, len(all_lineups)), 5):
            if i < len(all_lineups):
                lineup = all_lineups[i]
                score_value = getattr(lineup, score_attr)
                print(f"  #{i+1}: {score_label}={score_value:.1f}, Salary=${lineup.salary:,.0f}, Quality={lineup.get_quality_score(self.optimize_by):.3f}")
        
        # Show quality improvement analysis
        if len(all_lineups) >= 2:
            best_score = getattr(all_lineups[0], score_attr)
            worst_score = getattr(all_lineups[-1], score_attr)
            improvement = best_score - worst_score
            print(f"{score_label} range: {worst_score:.1f} - {best_score:.1f} (Improvement: {improvement:.1f} points)")
        
        return all_lineups
    
    def optimize_lineups(self, lineups: List[LineUp]) -> List[LineUp]:
        """
        Optimize lineups by improving individual positions while maintaining constraints
        
        Args:
            lineups: List of lineups to optimize
            
        Returns:
            List of optimized lineups
        """
        optimized_lineups = []
        
        for i, lineup in enumerate(lineups):
            print(f"Optimizing lineup {i+1}/{len(lineups)}...")
            
            # Try to improve each position
            best_lineup = lineup
            best_score = lineup.get_quality_score(self.optimize_by)
            
            # Try different FLEX options - prioritize projected score
            current_flex = lineup.players["FLEX"]
            flex_candidates = []
            
            # Add WR candidates for FLEX
            flex_candidates.extend([p for p in self.players.get('WR', []) 
                                  if p.name not in [lineup.players[pos].name for pos in ['WR1', 'WR2', 'WR3']]])
            
            # Add RB candidates for FLEX
            flex_candidates.extend([p for p in self.players.get('RB', []) 
                                  if p.name not in [lineup.players[pos].name for pos in ['RB1', 'RB2']]])
            
            # Add TE candidates for FLEX
            flex_candidates.extend([p for p in self.players.get('TE', []) 
                                  if p.name != lineup.players['TE'].name])
            
            # Sort by the specified score type first, then salary (for better utilization)
            if self.optimize_by == "risk_adjusted":
                score_attr = "risk_adjusted_score"
            elif self.optimize_by == "boom_score":
                score_attr = "boom_score"
            else:  # default to projected
                score_attr = "projected_score"
            
            flex_candidates.sort(key=lambda p: (getattr(p, score_attr), p.salary), reverse=True)
            
            for candidate in flex_candidates[:10]:  # Try top 10 candidates
                test_lineup = copy.deepcopy(lineup)
                test_lineup.players["FLEX"] = candidate
                test_lineup._clear_cache()  # Clear cache after modifying players
                
                if test_lineup.is_valid() and test_lineup.get_quality_score(self.optimize_by) > best_score:
                    best_lineup = test_lineup
                    best_score = test_lineup.get_quality_score(self.optimize_by)
            
            # Try to optimize other positions for projected score (but preserve stack)
            best_lineup = self._optimize_lineup_for_projected_score(best_lineup)
            
            # Try to upgrade salary utilization (but preserve stack)
            best_lineup = self._upgrade_lineup_salary(best_lineup)
            
            optimized_lineups.append(best_lineup)
        
        return optimized_lineups

    def _check_ownerships(self, lineups: List[LineUp], ownership_threshold: float) -> List[str]:
        """
        Check which players are over the ownership threshold
        
        Args:
            lineups: List of lineups to check
            ownership_threshold: Maximum percentage of lineups a player can be in
            
        Returns:
            List of player names that are oversubscribed
        """
        # count the number of times each player is in the list of lineups
        player_counts = {}
        for lineup in lineups:
            for player in lineup.players.values():
                player_counts[player.name] = player_counts.get(player.name, 0) + 1

        # find the players that are over the ownership threshold
        lineup_threshold = int(ownership_threshold * len(lineups))
        oversubscribed_players = []
        for player, count in player_counts.items():
            if count > lineup_threshold:
                oversubscribed_players.append(player)
        
        return oversubscribed_players

    def optimize_ownership(self, lineups: List[LineUp], ownership_threshold:float = 0.66) -> List[LineUp]:
        """
        Make sure there are no players that are over owned based on the ownership threshold.

        Take the following steps:
        1. Count the number of lineups that each player is in.
        2. If a player is in more than the ownership threshold, add them to a list of 'oversubscribed' players.
        3. Then loop back through the lineups, starting with the 'worst' lineup, and try to replace the oversubscribed player with the next best player that is not in the oversubscribed list. Be sure that the pool of replacement players makes the lineup still valid.
        4. After adding a new player, check the ownership again to make sure there is not a new player now that is over the ownership threshold.
        5. Repeat steps 3 and 4 until there are no oversubscribed players left.

        Args:
            lineups: List of lineups to optimize
            ownership_threshold: The ownership threshold to use

        Returns:
            List of optimized lineups
        
        Example:
        If there are 20 lineups and the ownership threshold is 0.6, and the lineup has 3 players that are over the ownership threshold, then the function will replace the 3 players with the next best players that are not over the ownership threshold.
        If there are no players that are over the ownership threshold, then the function will return the original lineups.
        If there are no replacement players that are not over the ownership threshold, then the function will return the original lineups.

        """

        
        lineup_threshold = int(ownership_threshold * len(lineups))

        # sort lineups by the total optimize_by score
        if self.optimize_by == "boom_score":
            lineups.sort(key=lambda x: x.boom_score, reverse=False)
            score_name = "boom_score"
        elif self.optimize_by == "risk_adjusted":
            lineups.sort(key=lambda x: x.risk_adjusted_score, reverse=False)
            score_name = "risk_adjusted_score"
        else:  # projected
            lineups.sort(key=lambda x: x.projected_score, reverse=False)
            score_name = "projected_score"
        
         # print out count of each player in the lineups
        player_counts = {}
        for lineup in lineups:
            for player in lineup.players.values():
                player_counts[player.name] = player_counts.get(player.name, 0) + 1
        for player, count in player_counts.items():
            print(f"{player}: {count}")
        
        # replace the oversubscribed players with the next best players that are not over the ownership threshold
        for lineup in lineups:
            replacements = []  # Store replacements to apply after iteration
            oversubscribed_players = self._check_ownerships(lineups, ownership_threshold)
            for position, player in lineup.players.items():
                if player.name in oversubscribed_players:
                    # calculate the salary of the lineup without the oversubscribed player
                    salary_without_player = lineup.salary - player.salary
                    available_salary = 50000 - salary_without_player  # Remaining salary for replacement

                    # create a pool of players that are within the available salary range and the same position
                    pool = []
                    if position == "FLEX":
                        # For FLEX, include RB, WR, and TE that fit within salary constraints
                        for pos in ["RB", "WR", "TE"]:
                            pool.extend([p for p in self.players.get(pos, []) 
                                       if p.salary <= available_salary 
                                       and p.name not in oversubscribed_players 
                                       and p.name != player.name])
                    elif position == "DST":
                        # Get QB's opponent team
                        qb_opponent = lineup.players['QB'].opponent
                        # Filter out DSTs playing against QB's team and ensure salary fits
                        pool.extend([p for p in self.players.get('D/ST', []) 
                                   if p.salary <= available_salary 
                                   and p.team != qb_opponent 
                                   and p.name not in oversubscribed_players 
                                   and p.name != player.name])
                    else:
                        # need to remove the number from the position if its there, e.g. RB1 should just be RB
                        position_clean = position.replace("1", "").replace("2", "").replace("3", "")
                        pool = [p for p in self.players.get(position_clean, []) 
                               if p.salary <= available_salary 
                               and p.name not in oversubscribed_players 
                               and p.name != player.name]
                    
                    # sort the pool by the specified score type
                    if self.optimize_by == "boom_score":
                        pool.sort(key=lambda p: p.boom_score, reverse=True)
                    elif self.optimize_by == "risk_adjusted":
                        pool.sort(key=lambda p: p.risk_adjusted_score, reverse=True)
                    else:  # projected
                        pool.sort(key=lambda p: p.projected_score, reverse=True)
                    
                    # find the next best player that is not over the ownership threshold
                    if len(pool) > 0:
                        replacement_player = pool[0]
                        replacements.append((position, replacement_player))
                    else:
                        print(f"No replacement player found for {player.name} - available salary: {available_salary}, position: {position}")
            
            # Apply all replacements after iteration is complete
            for position, replacement_player in replacements:
                print(f"Replacing {lineup.players[position].name} with {replacement_player.name}")
                lineup.players[position] = replacement_player
                
        # print out count of each player in the lineups
        player_counts = {}
        for lineup in lineups:
            for player in lineup.players.values():
                player_counts[player.name] = player_counts.get(player.name, 0) + 1
        for player, count in player_counts.items():
            print(f"{player}: {count}")

        # return the lineups sorted by the specified score type
        if self.optimize_by == "boom_score":
            lineups.sort(key=lambda x: x.boom_score, reverse=True)
        elif self.optimize_by == "risk_adjusted":
            lineups.sort(key=lambda x: x.risk_adjusted_score, reverse=True)
        else:  # projected
            lineups.sort(key=lambda x: x.projected_score, reverse=True)
        
        return lineups

    def _optimize_lineup_for_projected_score(self, lineup: LineUp) -> LineUp:
        """Optimize lineup by trying to maximize the specified score type within salary constraints"""
        best_lineup = lineup
        
        # Determine which score to optimize by
        if self.optimize_by == "risk_adjusted":
            best_score = lineup.risk_adjusted_score
            score_attr = "risk_adjusted_score"
        elif self.optimize_by == "boom_score":
            best_score = lineup.boom_score
            score_attr = "boom_score"
        else:  # default to projected
            best_score = lineup.projected_score
            score_attr = "projected_score"
        
        # Try to improve each position with higher score players
        # Only optimize RB and DST positions to preserve stack integrity
        positions_to_optimize = ['RB1', 'RB2', 'DST']
        
        for pos in positions_to_optimize:
            current_player = lineup.players[pos]
            current_score = getattr(current_player, score_attr)
            
            # Get candidates for this position
            if pos.startswith('RB'):
                candidates = [p for p in self.players.get('RB', []) 
                            if p.name not in [lineup.players['RB1'].name, lineup.players['RB2'].name]]
            elif pos.startswith('WR'):
                candidates = [p for p in self.players.get('WR', []) 
                            if p.name not in [lineup.players['WR1'].name, lineup.players['WR2'].name, lineup.players['WR3'].name]]
            elif pos == 'TE':
                candidates = [p for p in self.players.get('TE', []) 
                            if p.name != lineup.players['TE'].name]
            elif pos == 'DST':
                candidates = [p for p in self.players.get('D/ST', []) 
                            if p.name != lineup.players['DST'].name]
            else:
                continue
            
            # Sort by the specified score type
            candidates.sort(key=lambda p: getattr(p, score_attr), reverse=True)
            
            # Try top candidates
            for candidate in candidates[:5]:
                candidate_score = getattr(candidate, score_attr)
                if candidate_score <= current_score:
                    break  # No improvement possible
                
                test_lineup = copy.deepcopy(best_lineup)
                test_lineup.players[pos] = candidate
                test_lineup._clear_cache()  # Clear cache after modifying players
                
                if test_lineup.is_valid():
                    # Prefer higher score, but also consider salary utilization
                    test_score = getattr(test_lineup, score_attr)
                    if test_score > best_score:
                        best_lineup = test_lineup
                        best_score = test_score
                    elif (test_score == best_score and 
                          test_lineup.salary > best_lineup.salary):
                        # If same score, prefer higher salary utilization
                        best_lineup = test_lineup
        
        return best_lineup
    
    def _upgrade_lineup_salary(self, lineup: LineUp) -> LineUp:
        """Try to upgrade players to higher-salary options when budget allows"""
        best_lineup = lineup
        target_salary = 50000  # Aim for full utilization
        
        # If we're already at target, no need to upgrade
        if lineup.salary >= target_salary:
            return lineup
        
        # Calculate how much salary we can add
        available_salary = target_salary - lineup.salary
        
        # Try to upgrade each position with higher-salary players
        # Only upgrade RB, FLEX, and DST positions to preserve stack integrity
        positions_to_upgrade = ['RB1', 'RB2', 'FLEX', 'DST']
        
        for pos in positions_to_upgrade:
            current_player = lineup.players[pos]
            current_salary = current_player.salary
            
            # Get candidates for this position
            if pos.startswith('RB'):
                candidates = [p for p in self.players.get('RB', []) 
                            if p.name not in [lineup.players['RB1'].name, lineup.players['RB2'].name]]
            elif pos.startswith('WR'):
                candidates = [p for p in self.players.get('WR', []) 
                            if p.name not in [lineup.players['WR1'].name, lineup.players['WR2'].name, lineup.players['WR3'].name]]
            elif pos == 'TE':
                candidates = [p for p in self.players.get('TE', []) 
                            if p.name != lineup.players['TE'].name]
            elif pos == 'FLEX':
                # FLEX can be any position not already used
                candidates = []
                candidates.extend([p for p in self.players.get('WR', []) 
                                 if p.name not in [lineup.players['WR1'].name, lineup.players['WR2'].name, lineup.players['WR3'].name]])
                candidates.extend([p for p in self.players.get('RB', []) 
                                 if p.name not in [lineup.players['RB1'].name, lineup.players['RB2'].name]])
                candidates.extend([p for p in self.players.get('TE', []) 
                                 if p.name != lineup.players['TE'].name])
            elif pos == 'DST':
                candidates = [p for p in self.players.get('D/ST', []) 
                            if p.name != lineup.players['DST'].name]
            else:
                continue
            
            # Sort by salary (descending) to find upgrades
            candidates.sort(key=lambda p: p.salary, reverse=True)
            
            # Try to find a higher-salary upgrade that fits in budget
            for candidate in candidates:
                salary_increase = candidate.salary - current_salary
                
                # Check if this upgrade fits in our available budget
                if salary_increase <= available_salary:
                    test_lineup = copy.deepcopy(best_lineup)
                    test_lineup.players[pos] = candidate
                    test_lineup._clear_cache()  # Clear cache after modifying players
                    
                    if test_lineup.is_valid():
                        # Only upgrade if the specified score type doesn't decrease significantly
                        if self.optimize_by == "risk_adjusted":
                            candidate_score = candidate.risk_adjusted_score
                            current_score = current_player.risk_adjusted_score
                        elif self.optimize_by == "boom_score":
                            candidate_score = candidate.boom_score
                            current_score = current_player.boom_score
                        else:  # default to projected
                            candidate_score = candidate.projected_score
                            current_score = current_player.projected_score
                        
                        if candidate_score >= current_score * 0.9:  # Allow 10% decrease for salary upgrade
                            best_lineup = test_lineup
                            available_salary -= salary_increase
                            break  # Move to next position
        
        return best_lineup
    
    def _lineups_equal(self, lineup1: LineUp, lineup2: LineUp) -> bool:
        """Check if two lineups are essentially the same - optimized version"""
        # Quick check: if salaries are different, lineups are different
        if lineup1.salary != lineup2.salary:
            return False
        
        # Check if all players are the same using set comparison (faster)
        names1 = {lineup1.players[pos].name for pos in ['QB', 'RB1', 'RB2', 'WR1', 'WR2', 'WR3', 'TE', 'FLEX', 'DST']}
        names2 = {lineup2.players[pos].name for pos in ['QB', 'RB1', 'RB2', 'WR1', 'WR2', 'WR3', 'TE', 'FLEX', 'DST']}
        
        return names1 == names2
    
    def print_lineup_summary(self, lineups: List[LineUp]) -> None:
        """Print a summary of the generated lineups"""
        if not lineups:
            print("No lineups generated!")
            return
        
        print(f"\n{'='*80}")
        print("LINEUP GENERATION SUMMARY")
        print(f"{'='*80}")
        print(f"Total Lineups: {len(lineups)}")
        
        # Show the appropriate score type based on optimization target
        if self.optimize_by == "risk_adjusted":
            avg_score = sum(l.risk_adjusted_score for l in lineups)/len(lineups)
            score_label = "Average Risk Adjusted Score"
        elif self.optimize_by == "boom_score":
            avg_score = sum(l.boom_score for l in lineups)/len(lineups)
            score_label = "Average Boom Score"
        else:  # default to projected
            avg_score = sum(l.projected_score for l in lineups)/len(lineups)
            score_label = "Average Projected Score"
        
        print(f"{score_label}: {avg_score:.2f}")
        print(f"Average Salary: ${sum(l.salary for l in lineups)/len(lineups):,.0f}")
        print(f"Average Team Diversity: {sum(len(l.teams) for l in lineups)/len(lineups):.1f}")
        print(f"Average Quality Score: {sum(l.get_quality_score(self.optimize_by) for l in lineups)/len(lineups):.3f}")
        
        # Top 5 lineups
        print(f"\n{'='*80}")
        print("TOP 5 LINEUPS")
        print(f"{'='*80}")
        
        for i, lineup in enumerate(lineups[:5]):
            print(f"\n{i+1}. {lineup}")
            print(f"   QB: {lineup.players['QB'].name} ({lineup.players['QB'].team})")
            print(f"   RB: {lineup.players['RB1'].name} ({lineup.players['RB1'].team}) | {lineup.players['RB2'].name} ({lineup.players['RB2'].team})")
            print(f"   WR: {lineup.players['WR1'].name} ({lineup.players['WR1'].team}) | {lineup.players['WR2'].name} ({lineup.players['WR2'].team}) | {lineup.players['WR3'].name} ({lineup.players['WR3'].team})")
            print(f"   TE: {lineup.players['TE'].name} ({lineup.players['TE'].team})")
            print(f"   FLEX: {lineup.players['FLEX'].name} ({lineup.players['FLEX'].team}) - {lineup.players['FLEX'].position}")
            print(f"   DST: {lineup.players['DST'].name} ({lineup.players['DST'].team})")
            # Show the appropriate score type based on optimization target
            if self.optimize_by == "risk_adjusted":
                score_value = lineup.risk_adjusted_score
                score_label = "Risk_Adjusted_Score"
            elif self.optimize_by == "boom_score":
                score_value = lineup.boom_score
                score_label = "Boom_Score"
            else:  # default to projected
                score_value = lineup.projected_score
                score_label = "Projected_Score"
            
            print(f"   {score_label}: {score_value:.2f} | Salary: ${lineup.salary:,.0f} | Teams: {len(lineup.teams)} | Quality: {lineup.get_quality_score(self.optimize_by):.3f}")
    
    def export_lineups(self, lineups: List[LineUp], filename: str = "generated_lineups.csv") -> None:
        """Export lineups to CSV file"""
        if not lineups:
            print("No lineups to export!")
            return
        
        df = pd.DataFrame([lineup.to_dict(self.optimize_by) for lineup in lineups])
        df.to_csv(filename, index=False)
        print(f"Exported {len(lineups)} lineups to {filename}")


def main():
    """Main function to run the advanced lineup generator"""
    parser = argparse.ArgumentParser(description="Advanced DFS Lineup Generator")
    parser.add_argument("--week", type=int, required=True, help="Week number (e.g., 1, 2, 3)")
    parser.add_argument("--num-lineups", type=int, default=20, help="Number of lineups to generate (default: 20)")
    parser.add_argument("--output", default="generated_lineups.csv", help="Output CSV filename")
    parser.add_argument("--projections", help="Path to ESPN projections CSV (optional, will auto-detect)")
    parser.add_argument("--dk-data", help="Path to DraftKings data CSV (optional, will auto-detect)")
    parser.add_argument("--optimize-by", choices=["projected", "risk_adjusted", "boom_score"], default="projected", 
                       help="Optimize lineups based on projected_score, risk_adjusted_score, or boom_score (default: projected)")
    
    args = parser.parse_args()
    
    # Determine week folder path
    week_folder = f"2025/WEEK{args.week}"
    
    # Auto-detect files if not provided
    projections_path = args.projections
    dk_data_path = args.dk_data
    
    if not projections_path:
        projections_path = f"{week_folder}/espn_fantasy_projections.csv"
    
    if not dk_data_path:
        # Find DraftKings salary file
        import glob
        dk_files = glob.glob(f"{week_folder}/DK-Salaries*.csv")
        if dk_files:
            dk_data_path = dk_files[0]  # Use the first matching file
        else:
            # Try alternative naming pattern
            dk_files = glob.glob(f"{week_folder}/DKSalaries*.csv")
            if dk_files:
                dk_data_path = dk_files[0]
    
    # Load data
    print(f"Loading data for Week {args.week}...")
    print(f"Week folder: {week_folder}")
    
    try:
        print(f"Loading projections from: {projections_path}")
        projections_df = pd.read_csv(projections_path)
        print(f"✓ Loaded {len(projections_df)} players from projections")
    except FileNotFoundError:
        print(f"❌ Error: Could not find projections file at {projections_path}")
        return
    
    dk_data = None
    if dk_data_path:
        try:
            print(f"Loading DraftKings data from: {dk_data_path}")
            dk_data = pd.read_csv(dk_data_path)
            print(f"✓ Loaded {len(dk_data)} players from DraftKings data")
        except FileNotFoundError:
            print(f"⚠️  Warning: Could not find DraftKings file at {dk_data_path}")
            print("Continuing without salary data...")
    else:
        print("⚠️  No DraftKings salary file found. Using projections only...")
    
    # Initialize generator
    generator = AdvancedLineupGenerator(projections_df, dk_data, week_folder, args.optimize_by)
    
    # Check for boom score optimization with coarse data (simple check)
    if args.optimize_by == "boom_score":
        # Quick check: just look at the first few rows to see if boom scores are 0
        sample_boom_scores = projections_df["boom_score"].head(10)
        if all(score == 0 for score in sample_boom_scores):
            print("⚠️  WARNING: All boom scores are 0 (coarse mode data).")
            print("   Optimizing by boom_score will fall back to using projected scores instead.")
            print("   Consider using --optimize-by projected for better results with coarse data.")
    
    # Generate lineups
    print(f"Generating {args.num_lineups} lineups...")
    lineups = generator.generate_multiple_lineups(args.num_lineups)
    
    if not lineups:
        print("Failed to generate any lineups!")
        return
    
    # Optimize lineups
    print("Optimizing lineups...")
    optimized_lineups = generator.optimize_lineups(lineups)
    
    # optimze ownership
    print("Optimizing ownership...")
    optimized_lineups = generator.optimize_ownership(optimized_lineups)
    
    # Print summary
    generator.print_lineup_summary(optimized_lineups)
    
    # Export results
    output_path = f"{week_folder}/{args.output}"
    generator.export_lineups(optimized_lineups, output_path)


if __name__ == "__main__":
    main()
