# Standard library imports
import argparse
import copy
from dataclasses import dataclass
import random
import sys
from collections import Counter
from typing import Dict, List, Optional, Union

# Third-party imports
import numpy as np
import pandas as pd
from tqdm.auto import tqdm

# Local imports
from utils import BYE_DICT, CITY_TO_TEAM, TEAM_DICT, TOTAL_DICT



@dataclass
class Player:
    """A class to represent a Player"""
    name: str
    position: str
    salary: float
    score: float
    game_info: str
    team: str

    @classmethod
    def from_dataframe(cls, player_df: Union[pd.DataFrame, pd.Series]) -> 'Player':
        """
        Create a Player instance from a DataFrame or Series
        
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

            # Get score from either projected or actual
            score = (data.get("Proj DFS Total") if "Proj DFS Total" in data
                    else data.get("Act DFS Total"))
            
            if score is None:
                raise ValueError("Neither projected nor actual score found")

            return cls(
                name=data["Name + ID"],
                position=data["Position"],
                salary=float(data["Salary"]),
                score=float(score),
                game_info=data["Game Info"],
                team=data["TeamAbbrev"]
            )
        except KeyError as e:
            raise ValueError(f"Missing required field: {e}")

    @property
    def value(self) -> float:
        """Returns the value (points per thousand dollars) of a Player"""
        return (self.score / self.salary) * 1000

    @property
    def opponent(self) -> str:
        """Returns the opposing team of a Player"""
        home, away = self.game_info.split(" ")[0].split("@")
        return away if home == self.team else home

    def get_attribute(self, attr: str) -> float:
        """
        Get a specific attribute of the player
        
        Args:
            attr: The attribute to get ('value', 'score', or 'point')
            
        Returns:
            The requested attribute value
        """
        if attr in ["score", "point"]:
            return self.score
        elif attr == "value":
            return self.value
        raise ValueError(f"Invalid attribute: {attr}. Valid options are: value, score, point")

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Player(name='{self.name}', position='{self.position}', salary={self.salary}, score={self.score})"

class LineUp:
    """A class to represent a DraftKings lineup"""
    SALARY_CAP = 50000
    MAX_PLAYERS_PER_TEAM = 3

    def __init__(self, qb: Player, rb1: Player, rb2: Player, wr1: Player, wr2: Player, 
                 wr3: Player, te: Player, flex: Player, dst: Player):
        self._players = {
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
        # Cache frequently accessed values
        self._salary = None
        self._total = None
        self._names = None

    @classmethod
    def from_dataframe(cls, row: pd.Series) -> 'LineUp':
        """
        Create a LineUp instance from a DataFrame row
        
        Args:
            row: DataFrame row containing lineup data
            
        Returns:
            LineUp: New lineup instance
        """
        def get_player(value):
            """Helper function to handle both Player objects and raw data"""
            if isinstance(value, Player):
                return value
            return Player.from_dataframe(value)

        return cls(
            get_player(row["QB"]),
            get_player(row["RB1"]),
            get_player(row["RB2"]),
            get_player(row["WR1"]),
            get_player(row["WR2"]),
            get_player(row["WR3"]),
            get_player(row["TE"]),
            get_player(row["FLEX"]),
            get_player(row["DST"])
        )

    @property
    def players(self):
        """Getter for players dictionary"""
        return self._players

    @players.setter
    def players(self, value):
        """Setter for players dictionary that invalidates cached values"""
        self._players = value
        self._invalidate_cache()

    def _invalidate_cache(self):
        """Invalidates all cached values"""
        self._salary = None
        self._total = None
        self._names = None

    def update_player(self, position: str, player: Player):
        """Updates a single player and invalidates cache"""
        self._players[position] = player
        self._invalidate_cache()

    def replace_player(
    self, 
    player_name: str, 
    position: str, 
    df: pd.DataFrame,
    current_exposures: dict = None,
    max_exposure: float = 0.66
    ) -> Optional['LineUp']:
        """
        Attempt to replace a player in this lineup with a similar player
        
        Args:
            player_name: Name of player to replace
            position: Position to replace at
            df: Player pool DataFrame
            current_exposures: Dictionary of current player exposures
            max_exposure: Maximum allowed exposure
            
        Returns:
            Optional[LineUp]: New lineup if successful, None if no valid replacement found
        """
        # Get position-specific DataFrame
        if position == "FLEX":
            pos_df = position_df(df, "FLEX").copy()
        else:
            pos_df = df[df["Position"] == position.replace("1", "").replace("2", "").replace("3", "")].copy()
        
        # Calculate target salary range
        current_salary = next(
            p.salary for p in self.players.values() 
            if str(p) == player_name
        )
        salary_buffer = 500
        
        # Filter potential replacements
        replacements = pos_df[
            (pos_df["Salary"] >= current_salary - salary_buffer) &
            (pos_df["Salary"] <= current_salary + salary_buffer) &
            (pos_df["Name + ID"] != player_name)
        ]
        
        # Sort replacements by projected points (descending)
        replacements = replacements.sort_values(by="Proj DFS Total", ascending=False)
        
        # Try each potential replacement
        for _, row in replacements.iterrows():
            new_player = Player.from_dataframe(row)
            new_player_name = str(new_player)
            
            # Skip if replacement would create new exposure problems
            if (current_exposures is not None and 
                new_player_name in current_exposures and 
                current_exposures[new_player_name] >= max_exposure * 0.8):  # Use 80% of max as buffer
                continue
                
            new_lineup = copy.deepcopy(self)
            new_lineup.update_player(position, new_player)
            
            if (new_lineup.salary <= 50000 and 
                not new_lineup.duplicates() and 
                not new_lineup.players_on_same_team()):
                return new_lineup
        
        return None

    @property
    def salary(self):
        """Returns the sum of the LineUp's total salary"""
        if self._salary is None:
            self._salary = sum(player.salary for player in self._players.values())
        return self._salary

    @property
    def total(self):
        """Returns the sum of the LineUp's total projected score"""
        if self._total is None:
            self._total = sum(player.score for player in self._players.values())
        return self._total

    @property
    def names(self):
        """Returns a list of Players in the LineUp"""
        if self._names is None:
            self._names = [player.name for player in self._players.values()]
        return self._names

    def duplicates(self) -> bool:
        """Checks the LineUp for duplicates"""
        return len(self.names) != len(set(self.names))

    def to_dict(self) -> dict:
        """Exports the LineUp with salary and total points to a dictionary"""
        result = self.players.copy()
        result.update({
            "Salary": self.salary,
            "TotalPoints": self.total
        })
        return result

    def players_on_same_team(self, threshold=MAX_PLAYERS_PER_TEAM) -> bool:
        """Returns if there are multiple players on the same team in the same lineup"""
        team_counts = {}
        for player in self._players.values():
            team_counts[player.team] = team_counts.get(player.team, 0) + 1
            if team_counts[player.team] > threshold:
                return True
        return False

    def get_lowest_sal_player(self) -> tuple[Player, str]:
        """Returns the player with the lowest salary (excluding defense)"""
        min_salary = float('inf')
        low_player = None
        low_player_pos = None
        
        for pos, player in self._players.items():
            if pos != "DST" and player.salary < min_salary:
                min_salary = player.salary
                low_player = player
                low_player_pos = pos
        
        return low_player, low_player_pos

    def optimize(self, df: pd.DataFrame, wrt: Player) -> 'LineUp':
        """
        Attempt to optimize a lineup by replacing players with higher-scoring alternatives within budget
        """
        for pos, player in self._players.items():
            if player.position == "QB" or player.name == wrt.name:
                continue

            remaining_budget = self.SALARY_CAP - self.salary
            salary_range = min(500, remaining_budget)

            # Filter dataframe for potential replacements
            df_filt = df[df["Roster Position"].str.contains(pos)]
            df_filt = df_filt[
                (df_filt["Salary"] < player.salary + salary_range) & 
                (df_filt["Salary"] > player.salary - 500)
            ]

            # Try to find better players
            for _, candidate in df_filt.iterrows():
                new_player = Player.from_dataframe(candidate)
                if (new_player.score > player.score and 
                    new_player.name not in self.names):
                    print(f"Replacing {player.name} with {new_player.name}")
                    self.update_player(pos, new_player)
                    break

        # Try to upgrade lowest salary player
        low_player, low_pos = self.get_lowest_sal_player()
        remaining_budget = self.SALARY_CAP - self.salary
        
        df_filt = df[df["Roster Position"].str.contains(low_player.position)]
        df_filt = df_filt[
            (df_filt["Salary"] < low_player.salary + remaining_budget) & 
            (df_filt["Salary"] > low_player.salary)
        ]

        for _, candidate in df_filt.iterrows():
            new_player = Player.from_dataframe(candidate)
            if (new_player.score > low_player.score and 
                new_player.name not in self.names):
                print(f"Replacing {low_player.name} with {new_player.name}")
                self.update_player(low_pos, new_player)
                break

        return self

    def __len__(self) -> int:
        return len(self._players)

    def __str__(self) -> str:
        return f'Lineup: {self._players}'
    

@dataclass
class Stack:
    """A class to represent a QB-WR/TE stack"""
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

    def __post_init__(self):
        """Initialize the stack dictionary and cached values"""
        self.stack = {
            "QB": self.qb,
            "WR/TE": self.wrte
        }
        # Cache for computed values
        self._salary = None
        self._total = None
        self._value = None
        self._df = None

    @property
    def salary(self) -> float:
        """Returns the total salary of the stack"""
        if self._salary is None:
            self._salary = self.stack["QB"].salary + self.stack["WR/TE"].salary
        return self._salary

    @property
    def total(self) -> float:
        """Returns the total projected score of the stack"""
        if self._total is None:
            self._total = self.stack["QB"].score + self.stack["WR/TE"].score
        return self._total

    @property
    def value(self) -> float:
        """Returns the total value of the stack"""
        if self._value is None:
            self._value = self.stack["QB"].value + self.stack["WR/TE"].value
        return self._value

    def get_attribute(self, attr: str) -> float:
        """
        Get a specific attribute of the stack
        
        Args:
            attr: The attribute to get ('value', 'total', or other)
            
        Returns:
            float: The requested attribute value
        """
        attr = attr.lower()
        if attr == "value":
            return self.value
        return self.total

    @property
    def summary_df(self) -> pd.DataFrame:
        """Returns a DataFrame summarizing the stack's statistics"""
        if self._df is None:
            self._df = pd.DataFrame({
                "Name": [self.stack["QB"].name, self.stack["WR/TE"].name, "Total"],
                "Salary": [self.stack["QB"].salary, self.stack["WR/TE"].salary, self.salary],
                "Score": [self.stack["QB"].score, self.stack["WR/TE"].score, self.total],
                "Value": [self.stack["QB"].value, self.stack["WR/TE"].value, self.value]
            })
        return self._df

    def __str__(self) -> str:
        """String representation of the stack"""
        return str(self.summary_df)

    def __repr__(self) -> str:
        """Detailed string representation of the stack"""
        return f"Stack(QB={self.qb.name}, WR/TE={self.wrte.name}, Total Score={self.total:.2f})"

@dataclass
class LineUps:
    """A class to manage a collection of DraftKings lineups"""
    lineups: List[LineUp]
    
    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> 'LineUps':
        """Create LineUps instance from a DataFrame"""
        lineups = []
        for _, row in df.iterrows():
            lineups.append(LineUp.from_dataframe(row))
        return cls(lineups)
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert lineups to DataFrame"""
        return pd.DataFrame([lineup.to_dict() for lineup in self.lineups])
    
    def optimize(self, df: pd.DataFrame, stacks: list[Stack]) -> 'LineUps':
        """Optimize all lineups"""
        print("\nOptimizing lineups...")
        stack_size = len(self.lineups) // len(stacks)
        
        optimized_lineups = []
        for i, lineup in enumerate(self.lineups):
            stack_index = i // stack_size
            if stack_index < len(stacks):
                try:
                    optimized = lineup.optimize(df, stacks[stack_index].wrte)
                    optimized_lineups.append(optimized)
                except Exception as e:
                    print(f"Error optimizing lineup {i}: {e}")
                    optimized_lineups.append(lineup)
            
            if (i + 1) % 5 == 0:
                print(f"Optimized {i + 1}/{len(self.lineups)} lineups")
                
        return LineUps(optimized_lineups)
    
    def check_exposures(self, max_exposure: float = 0.66) -> dict:
        """Check exposure percentages for all players"""
        exposures = {}
        total_lineups = len(self.lineups)
        
        # Count all players across all positions
        all_players = []
        for lineup in self.lineups:
            all_players.extend(str(player) for player in lineup.players.values())
            
        # Calculate exposures
        player_counts = Counter(all_players)
        for player, count in player_counts.items():
            exposures[player] = count / total_lineups
            
        return exposures
    
    def reduce_exposure(self, df: pd.DataFrame, stacks: list[Stack], max_exposure: float = 0.66) -> 'LineUps':
        """Reduce over-exposed players while maintaining lineup quality"""
        self.lineups.sort(key=lambda x: x.total)
        max_iterations = 50
        iteration = 0
        
        while iteration < max_iterations:
            # Check current exposures
            exposures = self.check_exposures()
            over_exposed = {
                player: exp for player, exp in exposures.items() 
                if exp > max_exposure
            }
            
            if not over_exposed:
                print("\nAll player exposures are within limits")
                break
                
            print(f"\nIteration {iteration + 1}: Reducing exposure for:")
            for player, exposure in over_exposed.items():
                print(f"{player}: {exposure:.1%}")
            
            changes_made = False
            # Try to fix over-exposed players
            for player_name in over_exposed:
                # Find lineups containing this player
                for i, lineup in enumerate(self.lineups):
                    for pos, player in lineup.players.items():
                        if str(player) == player_name:
                            new_lineup = lineup.replace_player(
                                player_name,
                                pos,
                                df,
                                current_exposures=exposures,
                                max_exposure=max_exposure
                            )
                            if new_lineup:
                                self.lineups[i] = new_lineup
                                changes_made = True
                                break
                    
                    if changes_made:
                        break
            
            if not changes_made:
                print("\nWarning: Could not reduce exposure further without creating new problems")
                break
                
            iteration += 1
            
        if iteration == max_iterations:
            print("\nWarning: Reached maximum iterations, some players may still be over-exposed")
            
        return self
    
    def sort_by_points(self) -> 'LineUps':
        """Sort lineups by total points in descending order"""
        self.lineups.sort(key=lambda x: x.total, reverse=True)
        return self
    
    def print_summary(self) -> None:
        """Print summary of all lineups"""
        print("\nLineup Summary:")
        print(f"Total Lineups: {len(self.lineups)}")
        print(f"Average Points: {sum(l.total for l in self.lineups)/len(self.lineups):.2f}")
        print(f"Point Range: {min(l.total for l in self.lineups):.2f} - {max(l.total for l in self.lineups):.2f}")
        
        # Print exposure summary
        print("\nPlayer Exposures:")
        exposures = self.check_exposures()
        for player, exp in sorted(exposures.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"{player}: {exp:.1%}")
    
    def __len__(self) -> int:
        return len(self.lineups)
    
    def __getitem__(self, idx) -> LineUp:
        return self.lineups[idx]

def qb_wr_stack(df: pd.DataFrame, team: str) -> list[Stack]:
    '''
    Given a team, return list of possible QB-WR/TE stacks
    
    Args:
        df: DataFrame containing player data
        team: Team abbreviation to create stacks for
        
    Returns:
        list[Stack]: List of all possible QB-WR/TE stacks for the team
        
    Raises:
        Exception: If unable to find required players for stacks
    '''
    # Filter for team players
    team_df = df[df['TeamAbbrev'] == team]
    qb_wr_te_df = team_df[
        (team_df["Position"] == "QB") | 
        (team_df["Position"] == "WR") | 
        (team_df["Position"] == "TE")
    ]

    # Validation checks
    if len(qb_wr_te_df) < 3:
        raise Exception(
            f"Unable to pull data for {team}, please verify props have been "
            "populated for members of that team."
        )

    qb_df = qb_wr_te_df[qb_wr_te_df["Position"] == "QB"]
    if len(qb_df) < 1:
        raise Exception(
            f"Unable to find a QB for {team}, please verify props have been "
            "populated for members of that team."
        )

    wrte_df = qb_wr_te_df[
        (qb_wr_te_df["Position"] == "WR") | 
        (qb_wr_te_df["Position"] == "TE")
    ]
    if len(wrte_df) < 1:
        raise Exception(
            f"Unable to find a WR/TE for {team}, please verify props have been "
            "populated for members of that team."
        )

    # Create all possible stacks
    stacks = []
    for _, qb_row in qb_df.iterrows():
        qb = Player.from_dataframe(qb_row)
        
        for _, wrte_row in wrte_df.iterrows():
            wrte = Player.from_dataframe(wrte_row)
            stacks.append(Stack(qb, wrte))

    return stacks


def find_best_stack(df: pd.DataFrame, attr: str = "point", second_best: bool = False, limit:int=14500) -> Stack:
    """
    Find the best or second-best stack based on total points or value
    
    Args:
        df: DataFrame containing player data
        attr: Attribute to use for comparison ('point' or 'value')
        second_best: If True, returns the second-best stack instead of the best
        
    Returns:
        Stack: The best (or second-best) performing stack
        
    Raises:
        ValueError: If no valid stacks are found
    """
    # Store all stacks and their scores
    stack_scores = []
    
    for team in df["TeamAbbrev"].unique():
        try:
            team_stacks = qb_wr_stack(df, team)
        except Exception as e:
            print(f"Warning: {str(e)}")
            continue
            
        for stack in team_stacks:
            score = stack.get_attribute(attr)
            if stack.salary < limit:
                stack_scores.append((stack, score))
    
    if not stack_scores:
        raise ValueError("No valid stacks found")
    
    # Sort stacks by score in descending order
    stack_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Return second-best if requested and available
    if second_best and len(stack_scores) > 1:
        return stack_scores[1][0]
    
    # Otherwise return the best stack
    return stack_scores[0][0]

def position_df(df: pd.DataFrame, pos: str):
    "a function that returns a filtered dataframe by position"
    if pos != "FLEX":
        new_df = df[df["Position"] == pos]
        new_df.reset_index(drop=True, inplace=True)
    else:
        new_df = df[(df["Position"] == "WR") | (df["Position"] == "RB")]
        new_df.reset_index(drop=True, inplace=True)
    return new_df

def find_name(data: str):
    '''Make NFL.com team naming the same as DK team naming'''
    data = data.split('  ')
    return data[1]

def points_for(data: float):
    '''find each teams average points for'''
    # 1 – 6 Points Allowed +7 Pts
    # 7 – 13 Points Allowed +4 Pts
    # 14 – 20 Points Allowed +1 Pt
    # 21 – 27 Points Allowed +0 Pts
    # 28 – 34 Points Allowed -1 Pt
    # 35+ Points Allowed -4 Pts
    if data < 7:
        points = 7
    elif data > 6 and data < 14:
        points = 4
    elif data > 13 and data < 21:
        points = 1
    elif data > 20 and data < 28:
        points = 0
    elif data > 27 and data < 35:
        points = -1
    else:
        points = -4
    return points

def calc_df_INT_Pts(data, WEEK):
    '''calculate defensive INT per game as DFS points'''
    if BYE_DICT[find_name(data[0])] < WEEK:
        Int_Pt_Est = (data["INT"] * 2) / (WEEK - 2)
    else:
        Int_Pt_Est = (data["INT"] * 2) / (WEEK - 1)
    return Int_Pt_Est 

def calc_Sack_Pts(data, WEEK):
    '''calculate sacks per game as DFS points'''
    if BYE_DICT[find_name(data[0])] < WEEK:
        Sck_Pt_Est = (data["Sck"]) / (WEEK - 2)
    else:
        Sck_Pt_Est = (data["Sck"]) / (WEEK - 1)
    return Sck_Pt_Est   

def calc_Fum_Pts(data, WEEK):
    '''calculate fumbles per game as DFS points'''
    if BYE_DICT[find_name(data[0])] < WEEK:
        Fum_Pt_Est = (data["Rush FUM"] * 2) / (WEEK - 2)
    else:
        Fum_Pt_Est = (data["Rush FUM"] * 2) / (WEEK - 1)
    return Fum_Pt_Est 




def generate_line_up_from_stack(df: pd.DataFrame, stacks: list[Stack], NoL: int = 6) -> LineUps:
    """
    Generate lineups based on multiple stacks
    
    Args:
        df: DataFrame containing all players and info
        stacks: List of Stack objects to build lineups around
        NoL: Number of lineups to generate per stack
        
    Returns:
        pd.DataFrame: DataFrame with all generated lineups sorted by highest projected scores
    """
    all_lineups = []
    
    for stack in stacks:
        print(f"\nGenerating lineups for stack:")
        print(stack)
        
        # Set up initial stack players
        qb = stack.qb
        opp_team = qb.opponent
        
        # Handle WR/TE stack player
        if stack.wrte.position == "WR":
            wr1 = stack.wrte
            te_df = position_df(df, "TE").copy()
            te_df.loc[:, 'value'] = te_df['Proj DFS Total'] / te_df['Salary']
            te_df = te_df.sort_values(by='value', ascending=False)
            te = Player.from_dataframe(te_df.iloc[0:1])
        else:
            te = stack.wrte
            wr_df = position_df(df, "WR").copy()
            wr_df.loc[:, 'value'] = wr_df['Proj DFS Total'] / wr_df['Salary']
            wr_df = wr_df.sort_values(by='value', ascending=False)
            wr1 = Player.from_dataframe(wr_df.iloc[0:1])

        # Pre-filter and sort positions by points per dollar (value)
        rb_df = position_df(df, "RB").copy()
        rb_df.loc[:, 'value'] = rb_df['Proj DFS Total'] / rb_df['Salary']
        rb_df = rb_df.sort_values(by='value', ascending=False).head(20)

        wr_df = position_df(df, "WR").copy()
        wr_df.loc[:, 'value'] = wr_df['Proj DFS Total'] / wr_df['Salary']
        wr_df = wr_df.sort_values(by='value', ascending=False).head(20)

        flex_df = position_df(df, "FLEX").copy()
        flex_df.loc[:, 'value'] = flex_df['Proj DFS Total'] / flex_df['Salary']
        flex_df = flex_df.sort_values(by='value', ascending=False).head(20)

        # Handle DST separately
        dst_df = df[df["Position"] == "DST"].copy()
        dst_df = dst_df[dst_df["TeamAbbrev"] != opp_team]
        dst_df.loc[:, 'value'] = dst_df['Proj DFS Total'] / dst_df['Salary']
        dst_df = dst_df.sort_values(by='value', ascending=False).head(10)
        dst_df.reset_index(drop=True, inplace=True)

        stack_lineups = 0
        with tqdm(total=NoL, desc="Generating lineups") as pbar:
            # Systematic lineup generation
            for rb1_idx in range(len(rb_df)):
                rb1 = Player.from_dataframe(rb_df.iloc[rb1_idx:rb1_idx+1])
                
                for rb2_idx in range(rb1_idx + 1, len(rb_df)):
                    rb2 = Player.from_dataframe(rb_df.iloc[rb2_idx:rb2_idx+1])
                    
                    for wr2_idx in range(len(wr_df)):
                        wr2 = Player.from_dataframe(wr_df.iloc[wr2_idx:wr2_idx+1])
                        
                        for wr3_idx in range(wr2_idx + 1, len(wr_df)):
                            wr3 = Player.from_dataframe(wr_df.iloc[wr3_idx:wr3_idx+1])
                            
                            for flex_idx in range(len(flex_df)):
                                flex = Player.from_dataframe(flex_df.iloc[flex_idx:flex_idx+1])
                                
                                for dst_idx in range(len(dst_df)):
                                    dst = Player.from_dataframe(dst_df.iloc[dst_idx:dst_idx+1])
                                    
                                    # Create and validate lineup
                                    lineup = LineUp(qb, rb1, rb2, wr1, wr2, wr3, te, flex, dst)
                                    
                                    if (lineup.salary <= 50000 and 
                                        not lineup.duplicates() and 
                                        not lineup.players_on_same_team()):
                                        
                                        all_lineups.append(lineup)
                                        stack_lineups += 1
                                        pbar.update(1)
                                        
                                        if stack_lineups >= NoL:
                                            break
                                
                                if stack_lineups >= NoL:
                                    break
                            
                            if stack_lineups >= NoL:
                                break
                        
                        if stack_lineups >= NoL:
                            break
                    
                    if stack_lineups >= NoL:
                        break
                
                if stack_lineups >= NoL:
                    break
    
    lineups = LineUps(all_lineups)

    # Optimize and reduce exposure
    lineups = (lineups
              .optimize(df, stacks)
              .reduce_exposure(df, stacks)
              .sort_by_points())
    
    return lineups

def find_opponent(data: pd.Series) -> str:
    """
    Extract opponent team from game information
    
    Args:
        data: Series containing game and team information with fields:
              - 'Game Info': format "AWAY@HOME date time"
              - 'TeamAbbrev': current team abbreviation
              
    Returns:
        str: Opponent team abbreviation
        
    Raises:
        ValueError: If game info format is invalid
    """
    try:
        # Extract game info and team abbreviation
        game_info = data['Game Info']
        team_abbrev = data['TeamAbbrev']
        
        # Extract teams from game info
        game_teams = game_info.split(' ')[0]  # Get "AWAY@HOME" part
        away_team, home_team = game_teams.split('@')
        
        # Determine opponent
        if team_abbrev == home_team:
            opponent = away_team
        elif team_abbrev == away_team:
            opponent = home_team
        else:
            raise ValueError(f"Team {team_abbrev} not found in game {game_info}")
            
        # Convert to standardized team abbreviation if needed
        return TEAM_DICT.get(opponent, opponent)
        
    except (IndexError, ValueError) as e:
        raise ValueError(f"Invalid game info format: {game_info}") from e


def fix_name(data):
    if data == "Travis Etienne":
        return "Travis Etienne Jr."
    elif data == "Michael Pittman":
        return "Michael Pittman Jr."
    elif data == "Kenneth Walker":
        return "Kenneth Walker III"
    elif data == "Jeff Wilson":
        return "Jeff Wilson Jr."
    elif data == "Brian Robinson":
        return "Brian Robinson Jr."
    elif data == "Odell Beckham":
        return "Odell Beckham Jr."
    elif data == "Gardner Minshew":
        return "Gardner Minshew II"
    elif data == "Melvin Gordon":
        return "Melvin Gordon III"
    elif data == "Tony Jones":
        return "Tony Jones Jr."
    elif data == "Pierre Strong":
        return "Pierre Strong Jr."
    elif data == "Larry Rountree":
        return "Larry Rountree III"
    elif data == "Amon-Ra St." or data == "Amon-Ra St.BrownA. S":
        return "Amon-Ra St. Brown"
    elif data == "D.K. Metcalf":
        return "DK Metcalf"
    elif data == "D.J. Moore":
        return "DJ Moore"
    elif data == "Nathaniel Dell":
        return "Tank Dell"
    elif data == "Josh Palmer":
        return "Joshua Palmer"
    elif data == "Cartavious Bigsby":
        return "Tank Bigsby"
    elif data == "Damario Douglas":
        return "DeMario Douglas"
    elif data == "Re'Mahn Davis":
        return "Ray Davis"
    elif data == "Gabriel Davis":
        return "Gabe Davis"
    elif data == "Chigoziem Okonkwo":
        return "Chig Okonkwo"
    elif data == "John Mundt":
        return "Johnny Mundt"
    elif data == "Mar'Keise Irving":
        return "Bucky Irving"
    else:
        return data
    
def fetch_nfl_stats() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fetch NFL statistics from various sources"""
    try:
        passing = pd.read_html('https://www.nfl.com/stats/team-stats/offense/passing/2024/reg/all')[0]
        rushing = pd.read_html('https://www.nfl.com/stats/team-stats/offense/rushing/2024/reg/all')[0]
        points = pd.read_html("https://www.teamrankings.com/nfl/stat/points-per-game")[0]
        return passing, rushing, points
    except Exception as e:
        raise ValueError(f"Failed to fetch NFL stats: {e}")

def process_defensive_stats(passing: pd.DataFrame, rushing: pd.DataFrame, points: pd.DataFrame) -> pd.DataFrame:
    """Process and combine defensive statistics"""
    # Merge passing and rushing stats
    defense_stats = pd.merge(
        passing, 
        rushing, 
        how='left', 
        on='Team'
    )
    
    # Process team names and merge points
    points["Opp"] = points["Team"].apply(lambda x: CITY_TO_TEAM[x])
    defense_stats['Opp'] = defense_stats['Team'].apply(find_name)
    defense_stats = pd.merge(defense_stats, points, how='left', on='Opp')
    
    return defense_stats

def calculate_defense_points(defense_stats: pd.DataFrame, week: int) -> pd.DataFrame:
    """Calculate defensive fantasy points"""
    defense_stats = defense_stats.assign(
        INT_Pts=lambda x: x.apply(lambda row: calc_df_INT_Pts(row, week), axis=1),
        Sack_Pts=lambda x: x.apply(lambda row: calc_Sack_Pts(row, week), axis=1),
        Fum_Pts=lambda x: x.apply(lambda row: calc_Fum_Pts(row, week), axis=1),
        Pts_Scored=lambda x: x["2024"].apply(points_for)
    )
    
    # Calculate total points and scale
    defense_stats['Total'] = (defense_stats['INT_Pts'] + 
                            defense_stats['Sack_Pts'] + 
                            defense_stats['Fum_Pts'] + 
                            defense_stats['Pts_Scored'])
    
    defense_stats = defense_stats.sort_values(by='Total', ascending=True)
    defense_stats['Scale'] = np.linspace(-5, 5, len(defense_stats))
    
    return defense_stats

def process_defense_pool(dk_pool: pd.DataFrame, defense_stats: pd.DataFrame) -> pd.DataFrame:
    """Process defense pool with calculated statistics"""
    defense_pool = dk_pool[dk_pool['Position'] == 'DST'].copy()
    
    # Process defense pool
    defense_pool = (defense_pool
                   .drop(['ID'], axis=1)
                   .assign(Opp=lambda x: x.apply(find_opponent, axis=1)))
    
    # Merge with defense stats
    defense_pool = pd.merge(defense_pool, defense_stats, how='left', on='Opp')
    
    return defense_pool

def calculate_dfs_total(defense_pool: pd.DataFrame) -> pd.DataFrame:
    """Calculate final DFS total for defenses"""
    max_avg_points = defense_pool['AvgPointsPerGame'].max()
    defense_pool['DFS Total'] = ((defense_pool['AvgPointsPerGame'] / max_avg_points) * 8 + 
                                defense_pool['Scale'])
    
    # Select and clean final columns
    final_columns = ["Name", "DFS Total"]
    return defense_pool[final_columns]

def defense(dk_pool: pd.DataFrame, week: int) -> pd.DataFrame:
    """
    Process defensive statistics and calculate DFS totals
    
    Args:
        dk_pool: DataFrame containing DraftKings pool data
        week: Current NFL week
        
    Returns:
        DataFrame containing defensive DFS totals
    """
    try:
        # Fetch stats
        passing, rushing, points = fetch_nfl_stats()
        
        # Process defensive stats
        defense_stats = process_defensive_stats(passing, rushing, points)
        
        # Calculate defense points
        defense_stats = calculate_defense_points(defense_stats, week)
        
        # Process defense pool
        defense_pool = process_defense_pool(dk_pool, defense_stats)
        
        # Save debug information
        # defense_pool.to_csv(f'2024/Week{week}/defense_debug.csv')
        
        # Calculate final DFS totals
        return calculate_dfs_total(defense_pool)
        
    except Exception as e:
        print(f"Error processing defense data: {e}")
        raise

def process_player_data(dk_pool: pd.DataFrame, dk_stat: pd.DataFrame, week: int, args: argparse.Namespace, path: str) -> pd.DataFrame:
    """Process and clean player data for DFS analysis"""
    
    # Clean and combine data
    dk_stat["Name"] = dk_stat["Name"].apply(fix_name)
    dk_defense = defense(dk_pool, week)
    dk_stat = pd.concat([dk_stat, dk_defense], ignore_index=True)
    
    # Merge datasets
    df_main = pd.merge(dk_pool, dk_stat, how='left', on='Name')
    
    # Handle totals and missing values
    if args.test not in TOTAL_DICT:
        raise ValueError(f"Invalid test type: {args.test}. Must be one of {list(TOTAL_DICT.keys())}")
        
    df_main[TOTAL_DICT[args.test]] = df_main['DFS Total'].replace('', np.nan)
    df_main.dropna(subset=[TOTAL_DICT[args.test]], inplace=True)
    
    # Save forward-looking data if requested
    if args.test == "forward":
        df_main.to_csv(f"{path}dashboard.csv")
    
    # Filter and process by position
    position_filters = {
        'DEF': df_main["Position"] == "DST",
        'QB': df_main["Position"] == "QB",
        'TE': (df_main["Position"] == "TE") & (df_main["Salary"] > 3400),
        'Other': (df_main["Position"].isin(["RB", "WR"])) & (df_main["Salary"] > 3100)
    }
    
    # Apply filters and combine
    filtered_frames = [
        df_main[position_filters['QB']],  # QBs
        df_main[position_filters['TE']],  # TEs above salary threshold
        df_main[position_filters['DEF']],  # Defense
        df_main[position_filters['Other']]  # Other positions above salary threshold
    ]
    
    # Combine filtered data
    df_main = pd.concat(filtered_frames)
    
    # Final calculations
    df_main.drop(["AvgPointsPerGame"], axis=1, inplace=True)
    df_main["Value"] = (df_main[TOTAL_DICT[args.test]] / df_main["Salary"]) * 1000
    
    return df_main


def main(argv):
    argParser = argparse.ArgumentParser()
    argParser.add_argument("week", type=int, help="NFL Week")
    argParser.add_argument("-t", 
                           "--test", 
                           type=str, 
                           help="Predict future week or check past week", 
                           choices=("forward", "backtest"), 
                           default="forward")
    args = argParser.parse_args()
    WEEK = args.week
    path = f'2024/Week{WEEK}/'
    csv = f'{path}/DKSalaries-Week{WEEK}.csv'
    dk_pool = pd.read_csv(csv)

    if args.test == "forward":
        dk_stat = pd.read_csv(f"{path}NFL_PROJ_DFS.csv")
        csv_name = f"dk_lineups_week{WEEK}.csv"
    else:
        dk_stat = pd.read_csv(f"{path}box_score_debug.csv")
        csv_name = f"dk_lineups_week{WEEK}_backtest.csv"
    
    dfMain = process_player_data(dk_pool, dk_stat, WEEK, args, path)

    best_stack_points = find_best_stack(dfMain)
    best_stack_value = find_best_stack(dfMain, attr="value")
    second_best_stack_points = find_best_stack(dfMain, second_best=True)
    second_best_stack_value = find_best_stack(dfMain, attr="value", second_best=True)
    stack_list = [best_stack_points, best_stack_value, second_best_stack_points, second_best_stack_value]
    # Generate lineups
    lineups = generate_line_up_from_stack(dfMain, stack_list)
    
    # Print summary
    lineups.print_summary()
    
    # Convert to DataFrame for export
    dk_lineups = lineups.to_dataframe()

    dk_lineups.sort_values(by="TotalPoints", ascending=False, inplace=True, ignore_index=True)
    dk_lineups.to_csv(f"{path}{csv_name}")

if __name__ == "__main__":
    main(sys.argv[1:])