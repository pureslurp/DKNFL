#!/usr/bin/env python3
"""
Optimal Lineup Analysis for 2024 NFL DFS Data

This script finds the optimal lineup for each week using actual scores and analyzes:
1. Lineup construction patterns
2. Stack costs and composition
3. Position spending distribution
4. Team diversity in lineups
5. Defense selection patterns
6. Salary allocation trends
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict, Counter
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

# DraftKings lineup constraints
DK_SALARY_CAP = 50000
DK_POSITIONS = {
    'QB': 1,
    'RB': 2, 
    'WR': 3,
    'TE': 1,
    'FLEX': 1,  # Can be RB/WR/TE
    'DST': 1
}

@dataclass
class Player:
    """Player data structure for analysis"""
    name: str
    position: str
    salary: int
    actual_score: float
    team: str
    opponent: str
    
    @property
    def value_ratio(self) -> float:
        """Points per $1000 salary"""
        return (self.actual_score / self.salary) * 1000

@dataclass
class OptimalLineup:
    """Optimal lineup for a given week"""
    week: int
    players: List[Player]
    total_score: float
    total_salary: int
    
    @property
    def qb(self) -> Optional[Player]:
        """Get QB from lineup"""
        for player in self.players:
            if player.position == 'QB':
                return player
        return None
    
    @property
    def rbs(self) -> List[Player]:
        """Get RBs from lineup"""
        return [p for p in self.players if p.position == 'RB']
    
    @property
    def wrs(self) -> List[Player]:
        """Get WRs from lineup"""
        return [p for p in self.players if p.position == 'WR']
    
    @property
    def te(self) -> Optional[Player]:
        """Get TE from lineup"""
        for player in self.players:
            if player.position == 'TE':
                return player
        return None
    
    @property
    def flex(self) -> Optional[Player]:
        """Get FLEX player from lineup"""
        # DraftKings lineup: QB(1) + RB(2) + WR(3) + TE(1) + FLEX(1) + DST(1) = 9 players total
        # FLEX is the extra player beyond minimum requirements
        
        # Get all skill position players (non-QB, non-DST)
        skill_players = [p for p in self.players if p.position in ['RB', 'WR', 'TE']]
        
        # Count positions
        rb_count = len([p for p in skill_players if p.position == 'RB'])
        wr_count = len([p for p in skill_players if p.position == 'WR'])
        te_count = len([p for p in skill_players if p.position == 'TE'])
        
        # Find the extra player beyond minimum requirements
        if rb_count > 2:
            # Extra RB is FLEX - find the 3rd RB
            rbs = [p for p in skill_players if p.position == 'RB']
            return rbs[2]  # Third RB
        elif wr_count > 3:
            # Extra WR is FLEX - find the 4th WR
            wrs = [p for p in skill_players if p.position == 'WR']
            return wrs[3]  # Fourth WR
        elif te_count > 1:
            # Extra TE is FLEX - find the 2nd TE
            tes = [p for p in skill_players if p.position == 'TE']
            return tes[1]  # Second TE
        
        return None
    
    @property
    def dst(self) -> Optional[Player]:
        """Get DST from lineup"""
        for player in self.players:
            if player.position == 'DST':
                return player
        return None
    
    @property
    def teams(self) -> List[str]:
        """Get all teams in lineup"""
        return [p.team for p in self.players]
    
    @property
    def unique_teams(self) -> List[str]:
        """Get unique teams in lineup"""
        return list(set(self.teams))
    
    @property
    def team_count(self) -> int:
        """Number of unique teams"""
        return len(self.unique_teams)
    
    @property
    def qb_wr_stacks(self) -> List[Tuple[Player, Player]]:
        """Get QB-WR stacks from lineup"""
        stacks = []
        qb = self.qb
        if qb:
            for wr in self.wrs:
                if qb.team == wr.team:
                    stacks.append((qb, wr))
        return stacks
    
    @property
    def qb_te_stacks(self) -> List[Tuple[Player, Player]]:
        """Get QB-TE stacks from lineup"""
        stacks = []
        qb = self.qb
        te = self.te
        if qb and te and qb.team == te.team:
            stacks.append((qb, te))
        return stacks
    
    @property
    def all_stacks(self) -> List[Tuple[Player, Player]]:
        """Get all QB-WR/TE stacks"""
        return self.qb_wr_stacks + self.qb_te_stacks
    
    @property
    def stack_count(self) -> int:
        """Number of stacks in lineup"""
        return len(self.all_stacks)
    
    @property
    def stack_salary(self) -> int:
        """Total salary of all stacks"""
        stack_players = set()
        for qb, wr_te in self.all_stacks:
            stack_players.add(qb)
            stack_players.add(wr_te)
        return sum(p.salary for p in stack_players)
    
    @property
    def defense_opponent_conflict(self) -> bool:
        """Check if DST is playing against any player in lineup"""
        dst = self.dst
        if not dst:
            return False
        
        for player in self.players:
            if player != dst and player.team == dst.opponent:
                return True
        return False
    
    @property
    def position_spending(self) -> Dict[str, int]:
        """Get salary spent on each position"""
        spending = defaultdict(int)
        for player in self.players:
            spending[player.position] += player.salary
        return dict(spending)
    
    def get_position_players(self, position: str) -> List[Player]:
        """Get all players for a specific position"""
        if position == 'FLEX':
            flex_player = self.flex
            return [flex_player] if flex_player else []
        return [p for p in self.players if p.position == position]

class OptimalLineupAnalyzer:
    """Analyzer for optimal lineup construction patterns"""
    
    def __init__(self, data_path: str = "2024"):
        self.data_path = Path(data_path)
        self.optimal_lineups = {}
        
    def load_week_data(self, week: int) -> pd.DataFrame:
        """Load and merge DraftKings salaries with actual scores for a given week"""
        week_dir = self.data_path / f"WEEK{week}"
        
        if not week_dir.exists():
            print(f"Week {week} directory not found: {week_dir}")
            return pd.DataFrame()
        
        # Check for available salary files (prioritize sunday versions)
        dk_file_sunday = week_dir / f"DKSalaries-Week{week}_sunday.csv"
        dk_file_regular = week_dir / f"DKSalaries-Week{week}.csv"
        
        # Also check for lowercase "week" version (like Week 12)
        dk_file_sunday_lower = week_dir / f"DKSalaries-week{week}_sunday.csv"
        dk_file_regular_lower = week_dir / f"DKSalaries-week{week}.csv"
        
        # Determine which file to use (prioritize sunday versions)
        if dk_file_sunday.exists():
            dk_file = dk_file_sunday
            file_type = "sunday"
        elif dk_file_sunday_lower.exists():
            dk_file = dk_file_sunday_lower
            file_type = "sunday (lowercase)"
        elif dk_file_regular.exists():
            dk_file = dk_file_regular
            file_type = "regular"
        elif dk_file_regular_lower.exists():
            dk_file = dk_file_regular_lower
            file_type = "regular (lowercase)"
        else:
            print(f"No DraftKings salaries file found for Week {week}")
            return pd.DataFrame()
        
        dk_df = pd.read_csv(dk_file)
        print(f"Loaded Week {week} {file_type} DraftKings salaries: {len(dk_df)} players")
        
        # Load ACTUAL scores from box_score_debug.csv
        box_score_file = week_dir / "box_score_debug.csv"
        if box_score_file.exists():
            box_score_df = pd.read_csv(box_score_file)
            print(f"Loaded box scores: {len(box_score_df)} players")
            
            # Merge actual scores with DraftKings data
            merged_df = dk_df.copy()
            
            # Create a mapping of player names to actual scores
            score_mapping = {}
            for _, row in box_score_df.iterrows():
                player_name = row['Name']
                actual_score = row['DFS Total']
                score_mapping[player_name] = actual_score
            
            # Update scores: use actual scores for offensive players, keep AvgPointsPerGame for DSTs
            for idx, row in merged_df.iterrows():
                player_name = row['Name']
                position = row['Position']
                
                if position in ['DST', 'DEF']:
                    # Keep the AvgPointsPerGame for DSTs since they're not in box scores
                    merged_df.at[idx, 'AvgPointsPerGame'] = row['AvgPointsPerGame']
                elif player_name in score_mapping:
                    # Use actual score for offensive players
                    merged_df.at[idx, 'AvgPointsPerGame'] = score_mapping[player_name]
                # If player not found in box scores, keep original AvgPointsPerGame (projection)
            
            print(f"Merged data: {len(merged_df)} players")
            return merged_df
        else:
            print(f"Box score file not found: {box_score_file}")
            print("Using DraftKings projections only")
            return dk_df
    
    def create_player_objects(self, merged_df: pd.DataFrame) -> List[Player]:
        """Create Player objects from merged DataFrame"""
        players = []
        
        for _, row in merged_df.iterrows():
            try:
                # Get the actual score from AvgPointsPerGame (which now contains actual scores for offensive players, projections for DSTs)
                if 'AvgPointsPerGame' in row and pd.notna(row['AvgPointsPerGame']):
                    actual_score = float(row['AvgPointsPerGame'])
                else:
                    continue  # Skip players without scores
                
                # Extract opponent from Game Info
                opponent = self.extract_opponent(row['Game Info'], row['TeamAbbrev'])
                
                player = Player(
                    name=row['Name + ID'],
                    position=row['Position'],
                    salary=int(row['Salary']),
                    actual_score=actual_score,
                    team=row['TeamAbbrev'],
                    opponent=opponent
                )
                players.append(player)
            except (KeyError, ValueError, TypeError) as e:
                print(f"Error creating player from row: {e}")
                continue
        
        return players
    
    def extract_opponent(self, game_info: str, team: str) -> str:
        """Extract opponent team from game info"""
        if pd.isna(game_info) or pd.isna(team):
            return ""
        try:
            teams = game_info.split(' ')[0].split('@')
            if len(teams) == 2:
                return teams[1] if teams[0] == team else teams[0]
        except:
            pass
        return ""
    
    def find_optimal_lineup_advanced(self, players: List[Player]) -> Optional[OptimalLineup]:
        """Find optimal lineup using stack-first approach with high-scoring players"""
        # Filter players by position
        qbs = [p for p in players if p.position in ['QB', 'QB/FLEX']]
        rbs = [p for p in players if p.position in ['RB', 'RB/FLEX']]
        wrs = [p for p in players if p.position in ['WR', 'WR/FLEX']]
        tes = [p for p in players if p.position in ['TE', 'TE/FLEX']]
        dsts = [p for p in players if p.position in ['DST', 'DEF']]
        
        print(f"Position counts - QB: {len(qbs)}, RB: {len(rbs)}, WR: {len(wrs)}, TE: {len(tes)}, DST: {len(dsts)}")
        
        if not all([qbs, rbs, wrs, tes, dsts]):
            print("Missing players for required positions")
            return None
        
        # Sort by actual score (not value ratio) to prioritize high scorers
        qbs.sort(key=lambda x: x.actual_score, reverse=True)
        rbs.sort(key=lambda x: x.actual_score, reverse=True)
        wrs.sort(key=lambda x: x.actual_score, reverse=True)
        tes.sort(key=lambda x: x.actual_score, reverse=True)
        dsts.sort(key=lambda x: x.actual_score, reverse=True)
        
        print(f"Top 5 QBs by score: {[f'{qb.name} ({qb.actual_score:.1f})' for qb in qbs[:5]]}")
        print(f"Top 5 RBs by score: {[f'{rb.name} ({rb.actual_score:.1f})' for rb in rbs[:5]]}")
        print(f"Top 5 WRs by score: {[f'{wr.name} ({wr.actual_score:.1f})' for wr in wrs[:5]]}")
        
        best_lineup = None
        best_score = 0
        attempts = 0
        max_attempts = 50000
        
        print(f"Searching for optimal lineup with stacking priority...")
        
        # Strategy: Start with high-scoring QBs and build stacks around them
        for qb in qbs[:10]:  # Try top 10 QBs
            qb_team = qb.team
            remaining_salary = DK_SALARY_CAP - qb.salary
            
            # Find WRs and TEs from the same team for stacking
            qb_wrs = [wr for wr in wrs if wr.team == qb_team]
            qb_tes = [te for te in tes if te.team == qb_team]
            
            # Try different stack combinations
            stack_combinations = []
            
            # QB + WR stack
            for wr in qb_wrs[:5]:  # Top 5 WRs from QB's team
                stack_combinations.append(('WR', wr))
            
            # QB + TE stack  
            for te in qb_tes[:3]:  # Top 3 TEs from QB's team
                stack_combinations.append(('TE', te))
            
            # If no stack available, still try the QB
            if not stack_combinations:
                stack_combinations.append((None, None))
            
            for stack_type, stack_player in stack_combinations:
                attempts += 1
                if attempts > max_attempts:
                    break
                
                # Calculate remaining salary after stack
                stack_salary = qb.salary
                stack_score = qb.actual_score
                stack_players = [qb]
                
                if stack_player:
                    stack_salary += stack_player.salary
                    stack_score += stack_player.actual_score
                    stack_players.append(stack_player)
                
                remaining_after_stack = DK_SALARY_CAP - stack_salary
                
                # Fill remaining positions with highest scorers that fit
                # RBs (need 2)
                available_rbs = [rb for rb in rbs if rb not in stack_players]
                rb_combinations = []
                
                for i, rb1 in enumerate(available_rbs[:15]):
                    for rb2 in available_rbs[i+1:15]:
                        if rb1.salary + rb2.salary <= remaining_after_stack:
                            rb_combinations.append((rb1, rb2))
                            if len(rb_combinations) >= 20:  # Limit combinations
                                break
                    if len(rb_combinations) >= 20:
                        break
                
                if not rb_combinations:
                    continue
                
                for rb1, rb2 in rb_combinations:
                    rb_salary = rb1.salary + rb2.salary
                    rb_score = rb1.actual_score + rb2.actual_score
                    remaining_after_rb = remaining_after_stack - rb_salary
                    
                    # WRs (need 3, but one might be in stack)
                    needed_wrs = 3
                    if stack_type == 'WR':
                        needed_wrs = 2
                    
                    available_wrs = [wr for wr in wrs if wr not in stack_players + [rb1, rb2]]
                    wr_combinations = []
                    
                    if needed_wrs == 2:
                        for i, wr1 in enumerate(available_wrs[:10]):
                            for wr2 in available_wrs[i+1:10]:
                                if wr1.salary + wr2.salary <= remaining_after_rb:
                                    wr_combinations.append((wr1, wr2))
                                    if len(wr_combinations) >= 10:
                                        break
                            if len(wr_combinations) >= 10:
                                break
                    else:  # needed_wrs == 3
                        for i, wr1 in enumerate(available_wrs[:8]):
                            for j, wr2 in enumerate(available_wrs[i+1:8]):
                                for wr3 in available_wrs[j+1:8]:
                                    if wr1.salary + wr2.salary + wr3.salary <= remaining_after_rb:
                                        wr_combinations.append((wr1, wr2, wr3))
                                        if len(wr_combinations) >= 10:
                                            break
                                if len(wr_combinations) >= 10:
                                    break
                            if len(wr_combinations) >= 10:
                                break
                    
                    if not wr_combinations:
                        continue
                    
                    for wr_combo in wr_combinations:
                        if len(wr_combo) == 2:
                            wr1, wr2 = wr_combo
                            wr3 = None
                            wr_salary = wr1.salary + wr2.salary
                            wr_score = wr1.actual_score + wr2.actual_score
                        else:
                            wr1, wr2, wr3 = wr_combo
                            wr_salary = wr1.salary + wr2.salary + wr3.salary
                            wr_score = wr1.actual_score + wr2.actual_score + wr3.actual_score
                        
                        remaining_after_wr = remaining_after_rb - wr_salary
                        
                        # TE (if not in stack)
                        if stack_type == 'TE':
                            te = stack_player
                            te_salary = te.salary
                            te_score = te.actual_score
                        else:
                            excluded_players = stack_players + [rb1, rb2, wr1, wr2]
                            if wr3:
                                excluded_players.append(wr3)
                            available_tes = [te for te in tes if te not in excluded_players]
                            if not available_tes:
                                continue
                            
                            # Find the second TE
                            te = None
                            te_salary = 0
                            te_score = 0
                            for potential_te in available_tes[:5]:
                                if potential_te.salary <= remaining_after_wr:
                                    te = potential_te
                                    te_salary = te.salary
                                    te_score = te.actual_score
                                    break
                            
                            if not te:
                                continue
                        
                        remaining_after_te = remaining_after_wr - te_salary
                        
                        # FLEX (can be RB/WR/TE, but not already selected)
                        excluded_players = stack_players + [rb1, rb2, wr1, wr2, te]
                        if wr3:
                            excluded_players.append(wr3)
                        flex_pool = [p for p in rbs + wrs + tes if p not in excluded_players]
                        
                        if not flex_pool:
                            continue
                        
                        # Find best FLEX that fits
                        flex = None
                        flex_salary = 0
                        flex_score = 0
                        for potential_flex in flex_pool[:10]:
                            if potential_flex.salary <= remaining_after_te:
                                flex = potential_flex
                                flex_salary = flex.salary
                                flex_score = flex.actual_score
                                break
                        
                        if not flex:
                            continue
                        
                        remaining_after_flex = remaining_after_te - flex_salary
                        
                        # DST (avoid playing against lineup players)
                        opponent_teams = [qb.team, rb1.team, rb2.team, wr1.team, wr2.team, te.team, flex.team]
                        if wr3:
                            opponent_teams.append(wr3.team)
                        available_dsts = [d for d in dsts if d.opponent not in opponent_teams]
                        
                        if not available_dsts:
                            available_dsts = dsts  # Fallback to all DSTs
                        
                        # Find best DST that fits
                        dst = None
                        dst_salary = 0
                        dst_score = 0
                        for potential_dst in available_dsts[:5]:
                            if potential_dst.salary <= remaining_after_flex:
                                dst = potential_dst
                                dst_salary = dst.salary
                                dst_score = dst.actual_score
                                break
                        
                        if not dst:
                            continue
                        
                        # Calculate total
                        total_salary = stack_salary + rb_salary + wr_salary + te_salary + flex_salary + dst_salary
                        total_score = stack_score + rb_score + wr_score + te_score + flex_score + dst_score
                        
                        # Validate lineup
                        all_players = stack_players + [rb1, rb2, wr1, wr2]
                        if wr3:
                            all_players.append(wr3)
                        all_players.extend([te, flex, dst])
                        
                        # Check for duplicates
                        player_names = [p.name for p in all_players]
                        if len(set(player_names)) != len(player_names):
                            continue
                        
                        # Check team diversity (at least 3 different teams)
                        teams = [p.team for p in all_players]
                        if len(set(teams)) < 3:
                            continue
                        
                        # Check if this is the best lineup so far
                        if total_score > best_score:
                            best_score = total_score
                            best_lineup = OptimalLineup(
                                week=0,  # Will be set later
                                players=all_players,
                                total_score=total_score,
                                total_salary=total_salary
                            )
                            print(f"New best lineup found! Score: {best_score:.2f}, Salary: {total_salary}, Stack: {qb.name} + {stack_player.name if stack_player else 'None'}")
        
        if best_lineup:
            print(f"Optimal lineup found after {attempts} attempts")
            print(f"Final score: {best_lineup.total_score:.2f}, Salary: {best_lineup.total_salary}")
        else:
            print(f"No valid lineup found after {attempts} attempts")
            
        return best_lineup

    def find_optimal_lineup_simple(self, players: List[Player]) -> Optional[OptimalLineup]:
        """Find optimal lineup using simple but effective approach with stacking priority"""
        # Filter players by position
        qbs = [p for p in players if p.position in ['QB', 'QB/FLEX']]
        rbs = [p for p in players if p.position in ['RB', 'RB/FLEX']]
        wrs = [p for p in players if p.position in ['WR', 'WR/FLEX']]
        tes = [p for p in players if p.position in ['TE', 'TE/FLEX']]
        dsts = [p for p in players if p.position in ['DST', 'DEF']]
        
        print(f"Position counts - QB: {len(qbs)}, RB: {len(rbs)}, WR: {len(wrs)}, TE: {len(tes)}, DST: {len(dsts)}")
        
        if not all([qbs, rbs, wrs, tes, dsts]):
            print("Missing players for required positions")
            return None
        
        # Sort by actual score
        qbs.sort(key=lambda x: x.actual_score, reverse=True)
        rbs.sort(key=lambda x: x.actual_score, reverse=True)
        wrs.sort(key=lambda x: x.actual_score, reverse=True)
        tes.sort(key=lambda x: x.actual_score, reverse=True)
        dsts.sort(key=lambda x: x.actual_score, reverse=True)
        
        print(f"Top 5 QBs by score: {[f'{qb.name} ({qb.actual_score:.1f})' for qb in qbs[:5]]}")
        print(f"Top 5 RBs by score: {[f'{rb.name} ({rb.actual_score:.1f})' for rb in rbs[:5]]}")
        print(f"Top 5 WRs by score: {[f'{wr.name} ({wr.actual_score:.1f})' for wr in wrs[:5]]}")
        
        best_lineup = None
        best_score = 0
        attempts = 0
        max_attempts = 100000
        
        print(f"Searching for optimal lineup with stacking priority...")
        
        # Strategy: Try different QB-WR/TE stacks first, then fill with best available players
        for qb in qbs[:8]:  # Try top 8 QBs
            qb_team = qb.team
            remaining_salary = DK_SALARY_CAP - qb.salary
            
            # Find potential stack partners
            qb_wrs = [wr for wr in wrs if wr.team == qb_team][:3]  # Top 3 WRs from QB's team
            qb_tes = [te for te in tes if te.team == qb_team][:2]  # Top 2 TEs from QB's team
            
            # Try different stack combinations
            stack_options = []
            
            # No stack
            stack_options.append((None, None))
            
            # QB + WR stacks
            for wr in qb_wrs:
                stack_options.append(('WR', wr))
            
            # QB + TE stacks
            for te in qb_tes:
                stack_options.append(('TE', te))
            
            for stack_type, stack_player in stack_options:
                attempts += 1
                if attempts > max_attempts:
                    break
                
                # Calculate stack cost and score
                stack_salary = qb.salary
                stack_score = qb.actual_score
                stack_players = [qb]
                
                if stack_player:
                    stack_salary += stack_player.salary
                    stack_score += stack_player.actual_score
                    stack_players.append(stack_player)
                
                remaining_after_stack = DK_SALARY_CAP - stack_salary
                
                # Fill remaining positions with best available players
                # Start with highest scoring players and work down
                
                # RBs (need 2)
                available_rbs = [rb for rb in rbs if rb not in stack_players]
                if len(available_rbs) < 2:
                    continue
                
                # Try different RB combinations
                rb_combinations = []
                for i, rb1 in enumerate(available_rbs[:10]):
                    for rb2 in available_rbs[i+1:10]:
                        if rb1.salary + rb2.salary <= remaining_after_stack:
                            rb_combinations.append((rb1, rb2))
                            if len(rb_combinations) >= 15:
                                break
                    if len(rb_combinations) >= 15:
                        break
                
                if not rb_combinations:
                    continue
                
                for rb1, rb2 in rb_combinations:
                    rb_salary = rb1.salary + rb2.salary
                    rb_score = rb1.actual_score + rb2.actual_score
                    remaining_after_rb = remaining_after_stack - rb_salary
                    
                    # WRs (need 3, but one might be in stack)
                    needed_wrs = 3
                    if stack_type == 'WR':
                        needed_wrs = 2
                    
                    available_wrs = [wr for wr in wrs if wr not in stack_players + [rb1, rb2]]
                    if len(available_wrs) < needed_wrs:
                        continue
                    
                    # Get best WRs that fit
                    wr_combinations = []
                    if needed_wrs == 2:
                        for i, wr1 in enumerate(available_wrs[:8]):
                            for wr2 in available_wrs[i+1:8]:
                                if wr1.salary + wr2.salary <= remaining_after_rb:
                                    wr_combinations.append((wr1, wr2))
                                    if len(wr_combinations) >= 10:
                                        break
                            if len(wr_combinations) >= 10:
                                break
                    else:  # needed_wrs == 3
                        for i, wr1 in enumerate(available_wrs[:6]):
                            for j, wr2 in enumerate(available_wrs[i+1:6]):
                                for wr3 in available_wrs[j+1:6]:
                                    if wr1.salary + wr2.salary + wr3.salary <= remaining_after_rb:
                                        wr_combinations.append((wr1, wr2, wr3))
                                        if len(wr_combinations) >= 10:
                                            break
                                if len(wr_combinations) >= 10:
                                    break
                            if len(wr_combinations) >= 10:
                                break
                    
                    if not wr_combinations:
                        continue
                    
                    for wr_combo in wr_combinations:
                        if len(wr_combo) == 2:
                            wr1, wr2 = wr_combo
                            wr3 = None
                            wr_salary = wr1.salary + wr2.salary
                            wr_score = wr1.actual_score + wr2.actual_score
                        else:
                            wr1, wr2, wr3 = wr_combo
                            wr_salary = wr1.salary + wr2.salary + wr3.salary
                            wr_score = wr1.actual_score + wr2.actual_score + wr3.actual_score
                        
                        remaining_after_wr = remaining_after_rb - wr_salary
                        
                        # TE (if not in stack)
                        if stack_type == 'TE':
                            te = stack_player
                            te_salary = te.salary
                            te_score = te.actual_score
                        else:
                            # Find best TE that fits
                            excluded_players = stack_players + [rb1, rb2, wr1, wr2]
                            if wr3:
                                excluded_players.append(wr3)
                            available_tes = [te for te in tes if te not in excluded_players]
                            
                            if not available_tes:
                                continue
                            
                            te = None
                            te_salary = 0
                            te_score = 0
                            for potential_te in available_tes[:5]:
                                if potential_te.salary <= remaining_after_wr:
                                    te = potential_te
                                    te_salary = te.salary
                                    te_score = te.actual_score
                                    break
                            
                            if not te:
                                continue
                        
                        remaining_after_te = remaining_after_wr - te_salary
                        
                        # FLEX (can be RB/WR/TE, but not already selected)
                        excluded_players = stack_players + [rb1, rb2, wr1, wr2, te]
                        if wr3:
                            excluded_players.append(wr3)
                        flex_pool = [p for p in rbs + wrs + tes if p not in excluded_players]
                        
                        if not flex_pool:
                            continue
                        
                        # Find best FLEX that fits
                        flex = None
                        flex_salary = 0
                        flex_score = 0
                        for potential_flex in flex_pool[:8]:
                            if potential_flex.salary <= remaining_after_te:
                                flex = potential_flex
                                flex_salary = flex.salary
                                flex_score = flex.actual_score
                                break
                        
                        if not flex:
                            continue
                        
                        remaining_after_flex = remaining_after_te - flex_salary
                        
                        # DST (avoid playing against lineup players)
                        opponent_teams = [qb.team, rb1.team, rb2.team, wr1.team, wr2.team, te.team, flex.team]
                        if wr3:
                            opponent_teams.append(wr3.team)
                        available_dsts = [d for d in dsts if d.opponent not in opponent_teams]
                        
                        if not available_dsts:
                            available_dsts = dsts  # Fallback to all DSTs
                        
                        # Find best DST that fits
                        dst = None
                        dst_salary = 0
                        dst_score = 0
                        for potential_dst in available_dsts[:5]:
                            if potential_dst.salary <= remaining_after_flex:
                                dst = potential_dst
                                dst_salary = dst.salary
                                dst_score = dst.actual_score
                                break
                        
                        if not dst:
                            continue
                        
                        # Calculate total
                        total_salary = stack_salary + rb_salary + wr_salary + te_salary + flex_salary + dst_salary
                        total_score = stack_score + rb_score + wr_score + te_score + flex_score + dst_score
                        
                        # Validate lineup
                        all_players = stack_players + [rb1, rb2, wr1, wr2]
                        if wr3:
                            all_players.append(wr3)
                        all_players.extend([te, flex, dst])
                        
                        # Check for duplicates
                        player_names = [p.name for p in all_players]
                        if len(set(player_names)) != len(player_names):
                            continue
                        
                        # Check team diversity (at least 3 different teams)
                        teams = [p.team for p in all_players]
                        if len(set(teams)) < 3:
                            continue
                        
                        # Check salary cap constraint (HARD CONSTRAINT)
                        if total_salary > DK_SALARY_CAP:
                            continue
                        
                        # Check if this is the best lineup so far
                        if total_score > best_score:
                            best_score = total_score
                            best_lineup = OptimalLineup(
                                week=0,  # Will be set later
                                players=all_players,
                                total_score=total_score,
                                total_salary=total_salary
                            )
                            print(f"    ✅ New best STACKED lineup found! Score: {best_score:.2f}, Salary: {total_salary}, Stack: {qb.name} + {partner.name}")
                            print(f"    Budget allocation: RB=${rb_salary:,}, WR=${wr_salary:,}, TE=${te_salary:,}, DST=${dst_salary:,}")
        
        if best_lineup:
            print(f"Optimal lineup found after {attempts} attempts")
            print(f"Final score: {best_lineup.total_score:.2f}, Salary: {best_lineup.total_salary}")
        else:
            print(f"No valid lineup found after {attempts} attempts")
            
        return best_lineup
    
    def find_optimal_lineup(self, players: List[Player]) -> Optional[OptimalLineup]:
        """Find the optimal lineup using actual scores - efficient approach inspired by generate_line_up_from_stack"""
        # Filter players by position (handle different position formats)
        qbs = [p for p in players if p.position in ['QB', 'QB/FLEX']]
        rbs = [p for p in players if p.position in ['RB', 'RB/FLEX']]
        wrs = [p for p in players if p.position in ['WR', 'WR/FLEX']]
        tes = [p for p in players if p.position in ['TE', 'TE/FLEX']]
        dsts = [p for p in players if p.position in ['DST', 'DEF']]
        
        print(f"Position counts - QB: {len(qbs)}, RB: {len(rbs)}, WR: {len(wrs)}, TE: {len(tes)}, DST: {len(dsts)}")
        
        if not all([qbs, rbs, wrs, tes, dsts]):
            print("Missing players for required positions")
            return None
        
        # Sort players by value ratio and pre-filter top candidates
        qbs.sort(key=lambda x: x.value_ratio, reverse=True)
        rbs.sort(key=lambda x: x.value_ratio, reverse=True)
        wrs.sort(key=lambda x: x.value_ratio, reverse=True)
        tes.sort(key=lambda x: x.value_ratio, reverse=True)
        dsts.sort(key=lambda x: x.value_ratio, reverse=True)
        
        # Pre-filter to top candidates to reduce search space
        top_qbs = qbs[:min(10, len(qbs))]
        top_rbs = rbs[:min(20, len(rbs))]
        top_wrs = wrs[:min(25, len(wrs))]
        top_tes = tes[:min(15, len(tes))]
        top_dsts = dsts[:min(10, len(dsts))]
        
        best_lineup = None
        best_score = 0
        attempts = 0
        max_attempts = 50000  # Reasonable limit to prevent infinite loops
        
        print(f"Searching for optimal lineup with {max_attempts} max attempts...")
        
        while attempts < max_attempts:
            attempts += 1
            
            # Randomly select players from top candidates
            qb = np.random.choice(top_qbs)
            remaining_salary = DK_SALARY_CAP - qb.salary
            
            # Select RBs
            rb1, rb2 = np.random.choice(top_rbs, size=2, replace=False)
            if rb1.salary + rb2.salary > remaining_salary:
                continue
                
            rb_salary = rb1.salary + rb2.salary
            rb_score = rb1.actual_score + rb2.actual_score
            
            # Select WRs
            wr1, wr2, wr3 = np.random.choice(top_wrs, size=3, replace=False)
            if wr1.salary + wr2.salary + wr3.salary > remaining_salary - rb_salary:
                continue
                
            wr_salary = wr1.salary + wr2.salary + wr3.salary
            wr_score = wr1.actual_score + wr2.actual_score + wr3.actual_score
            
            # Select TE
            te = np.random.choice(top_tes)
            if te.salary > remaining_salary - rb_salary - wr_salary:
                continue
                
            te_salary = te.salary
            te_score = te.actual_score
            
            # Select FLEX (can be RB/WR/TE, but not already selected)
            flex_pool = [p for p in top_rbs + top_wrs + top_tes 
                        if p not in [rb1, rb2, wr1, wr2, wr3, te]]
            if not flex_pool:
                continue
                
            flex = np.random.choice(flex_pool)
            if flex.salary > remaining_salary - rb_salary - wr_salary - te_salary:
                continue
                
            flex_salary = flex.salary
            flex_score = flex.actual_score
            
            # Select DST
            dst = np.random.choice(top_dsts)
            total_salary = qb.salary + rb_salary + wr_salary + te_salary + flex_salary + dst.salary
            
            if total_salary <= DK_SALARY_CAP:
                total_score = qb.actual_score + rb_score + wr_score + te_score + flex_score + dst.actual_score
                
                # Check for duplicates and team conflicts
                all_players = [qb, rb1, rb2, wr1, wr2, wr3, te, flex, dst]
                player_names = [p.name for p in all_players]
                
                # Check for duplicates
                if len(set(player_names)) != len(player_names):
                    continue
                    
                # Check team diversity (at least 3 different teams)
                teams = [p.team for p in all_players]
                if len(set(teams)) < 3:
                    continue
                    
                # Check for defense playing against lineup players
                dst_opponent = dst.opponent
                if any(p.team == dst_opponent for p in all_players if p != dst):
                    continue
                
                if total_score > best_score:
                    best_score = total_score
                    best_lineup = OptimalLineup(
                        week=0,  # Will be set later
                        players=all_players,
                        total_score=total_score,
                        total_salary=total_salary
                    )
                    print(f"New best lineup found! Score: {best_score:.2f}, Salary: {total_salary}, Attempt: {attempts}")
        
        if best_lineup:
            print(f"Optimal lineup found after {attempts} attempts")
            print(f"Final score: {best_lineup.total_score:.2f}, Salary: {best_lineup.total_salary}")
        else:
            print(f"No valid lineup found after {attempts} attempts")
            
        return best_lineup
    
    def find_optimal_lineup_flexible(self, players: List[Player]) -> Optional[OptimalLineup]:
        """Find optimal lineup using flexible approach that prioritizes stacking but adapts to constraints"""
        # Filter players by position
        qbs = [p for p in players if p.position in ['QB', 'QB/FLEX']]
        rbs = [p for p in players if p.position in ['RB', 'RB/FLEX']]
        wrs = [p for p in players if p.position in ['WR', 'WR/FLEX']]
        tes = [p for p in players if p.position in ['TE', 'TE/FLEX']]
        dsts = [p for p in players if p.position in ['DST', 'DEF']]
        
        print(f"Position counts - QB: {len(qbs)}, RB: {len(rbs)}, WR: {len(wrs)}, TE: {len(tes)}, DST: {len(dsts)}")
        
        if not all([qbs, rbs, wrs, tes, dsts]):
            print("Missing players for required positions")
            return None
        
        # Sort by actual score
        qbs.sort(key=lambda x: x.actual_score, reverse=True)
        rbs.sort(key=lambda x: x.actual_score, reverse=True)
        wrs.sort(key=lambda x: x.actual_score, reverse=True)
        tes.sort(key=lambda x: x.actual_score, reverse=True)
        dsts.sort(key=lambda x: x.actual_score, reverse=True)
        
        print(f"Top 5 QBs by score: {[f'{qb.name} ({qb.actual_score:.1f})' for qb in qbs[:5]]}")
        print(f"Top 5 RBs by score: {[f'{rb.name} ({rb.actual_score:.1f})' for rb in rbs[:5]]}")
        print(f"Top 5 WRs by score: {[f'{wr.name} ({wr.actual_score:.1f})' for wr in wrs[:5]]}")
        
        best_lineup = None
        best_score = 0
        attempts = 0
        max_attempts = 50000
        
        print(f"Searching for optimal lineup with flexible stacking approach...")
        
        # Strategy: Try different approaches in order of preference
        # 1. High-scoring QB with stack
        # 2. High-scoring QB without stack
        # 3. Best overall lineup regardless of stacking
        
        # First, try to find lineups with QB-WR/TE stacks
        for qb in qbs[:6]:  # Try top 6 QBs
            qb_team = qb.team
            remaining_salary = DK_SALARY_CAP - qb.salary
            
            # Find potential stack partners
            qb_wrs = [wr for wr in wrs if wr.team == qb_team][:2]  # Top 2 WRs from QB's team
            qb_tes = [te for te in tes if te.team == qb_team][:1]  # Top TE from QB's team
            
            # Try different stack combinations
            stack_options = []
            
            # QB + WR stacks
            for wr in qb_wrs:
                stack_options.append(('WR', wr))
            
            # QB + TE stacks
            for te in qb_tes:
                stack_options.append(('TE', te))
            
            for stack_type, stack_player in stack_options:
                attempts += 1
                if attempts > max_attempts:
                    break
                
                # Calculate stack cost and score
                stack_salary = qb.salary + stack_player.salary
                stack_score = qb.actual_score + stack_player.actual_score
                stack_players = [qb, stack_player]
                
                remaining_after_stack = DK_SALARY_CAP - stack_salary
                
                # Fill remaining positions with best available players
                # RBs (need 2)
                available_rbs = [rb for rb in rbs if rb not in stack_players]
                if len(available_rbs) < 2:
                    continue
                
                # Try different RB combinations (more flexible)
                rb_combinations = []
                for i, rb1 in enumerate(available_rbs[:12]):
                    for rb2 in available_rbs[i+1:12]:
                        if rb1.salary + rb2.salary <= remaining_after_stack:
                            rb_combinations.append((rb1, rb2))
                            if len(rb_combinations) >= 20:
                                break
                    if len(rb_combinations) >= 20:
                        break
                
                if not rb_combinations:
                    continue
                
                for rb1, rb2 in rb_combinations:
                    rb_salary = rb1.salary + rb2.salary
                    rb_score = rb1.actual_score + rb2.actual_score
                    remaining_after_rb = remaining_after_stack - rb_salary
                    
                    # WRs (need 3, but one is in stack if it's a WR)
                    needed_wrs = 2  # Since one WR is in stack
                    available_wrs = [wr for wr in wrs if wr not in stack_players + [rb1, rb2]]
                    
                    if len(available_wrs) < needed_wrs:
                        continue
                    
                    # Get best WRs that fit
                    wr_combinations = []
                    for i, wr1 in enumerate(available_wrs[:10]):
                        for wr2 in available_wrs[i+1:10]:
                            if wr1.salary + wr2.salary <= remaining_after_rb:
                                wr_combinations.append((wr1, wr2))
                                if len(wr_combinations) >= 15:
                                    break
                        if len(wr_combinations) >= 15:
                            break
                    
                    if not wr_combinations:
                        continue
                    
                    for wr1, wr2 in wr_combinations:
                        wr_salary = wr1.salary + wr2.salary
                        wr_score = wr1.actual_score + wr2.actual_score
                        remaining_after_wr = remaining_after_rb - wr_salary
                        
                        # TE (if not in stack)
                        if stack_type == 'TE':
                            te = stack_player
                            te_salary = te.salary
                            te_score = te.actual_score
                        else:
                            # Find best TE that fits
                            excluded_players = stack_players + [rb1, rb2, wr1, wr2]
                            if wr3:
                                excluded_players.append(wr3)
                            available_tes = [te for te in tes if te not in excluded_players]
                            available_tes.sort(key=lambda x: x.value_ratio, reverse=True)
                            
                            te = None
                            te_salary = 0
                            te_score = 0
                            for potential_te in available_tes[:15]:
                                if potential_te.salary <= te_budget:
                                    te = potential_te
                                    te_salary = te.salary
                                    te_score = te.actual_score
                                    break
                            
                            if not te:
                                continue
                        
                        remaining_after_te = remaining_after_wr - te_salary
                        
                        # FLEX (can be RB/WR/TE, but not already selected)
                        excluded_players = [qb, partner, rb1, rb2, wr1, wr2, te]
                        if wr3:
                            excluded_players.append(wr3)
                        flex_pool = [p for p in rbs + wrs + tes if p not in excluded_players]
                        flex_pool.sort(key=lambda x: x.value_ratio, reverse=True)
                        
                        flex = None
                        flex_salary = 0
                        flex_score = 0
                        for potential_flex in flex_pool[:20]:
                            if potential_flex.salary <= remaining_after_te:
                                flex = potential_flex
                                flex_salary = potential_flex.salary
                                flex_score = potential_flex.actual_score
                                break
                        
                        if not flex:
                            continue
                        
                        remaining_after_flex = remaining_after_te - flex_salary
                        
                        # DST (avoid playing against lineup players)
                        opponent_teams = [qb.team, rb1.team, rb2.team, wr1.team, wr2.team, te.team, flex.team]
                        available_dsts = [d for d in dsts if d.opponent not in opponent_teams]
                        
                        if not available_dsts:
                            available_dsts = dsts  # Fallback to all DSTs
                        
                        available_dsts.sort(key=lambda x: x.value_ratio, reverse=True)
                        
                        dst = None
                        dst_salary = 0
                        dst_score = 0
                        for potential_dst in available_dsts[:15]:
                            if potential_dst.salary <= dst_budget:
                                dst = potential_dst
                                dst_salary = potential_dst.salary
                                dst_score = potential_dst.actual_score
                                break
                        
                        if not dst:
                            continue
                        
                        # Calculate total
                        total_salary = stack['salary'] + rb_salary + wr_salary + te_salary + flex_salary + dst_salary
                        total_score = stack_score + rb_score + wr_score + te_score + flex_score + dst_score
                        
                        # Validate lineup
                        all_players = [qb, partner, rb1, rb2, wr1, wr2]
                        if wr3:
                            all_players.append(wr3)
                        all_players.extend([te, flex, dst])
                        
                        # Check for duplicates
                        player_names = [p.name for p in all_players]
                        if len(set(player_names)) != len(player_names):
                            continue
                        
                        # Check team diversity (at least 3 different teams)
                        teams = [p.team for p in all_players]
                        if len(set(teams)) < 3:
                            continue
                        
                        # Check if this is the best lineup so far
                        if total_score > best_score:
                            best_score = total_score
                            best_lineup = OptimalLineup(
                                week=0,  # Will be set later
                                players=all_players,
                                total_score=total_score,
                                total_salary=total_salary
                            )
                            print(f"New best STACKED lineup found! Score: {best_score:.2f}, Salary: {total_salary}, Stack: {qb.name} + {stack_player.name}")
                            print(f"    Budget allocation: RB=${rb_salary:,}, WR=${wr_salary:,}, TE=${te_salary:,}, DST=${dst_salary:,}")
        
        if best_lineup:
            print(f"🎉 Optimal STACKED lineup found after {attempts} attempts")
            print(f"Final score: {best_lineup.total_score:.2f}, Salary: {best_lineup.total_salary}")
        else:
            print(f"❌ No valid stacked lineup found after {attempts} attempts")
            
        return best_lineup
    
    def find_optimal_lineup_stack_first(self, players: List[Player]) -> Optional[OptimalLineup]:
        """Find optimal lineup by prioritizing QB-WR/TE stacks first, then building around them with smart budget allocation"""
        # Filter players by position
        qbs = [p for p in players if p.position in ['QB', 'QB/FLEX']]
        rbs = [p for p in players if p.position in ['RB', 'RB/FLEX']]
        wrs = [p for p in players if p.position in ['WR', 'WR/FLEX']]
        tes = [p for p in players if p.position in ['TE', 'TE/FLEX']]
        dsts = [p for p in players if p.position in ['DST', 'DEF']]
        
        print(f"Position counts - QB: {len(qbs)}, RB: {len(rbs)}, WR: {len(wrs)}, TE: {len(tes)}, DST: {len(dsts)}")
        
        if not all([qbs, rbs, wrs, tes, dsts]):
            print("Missing players for required positions")
            return None
        
        # Sort by actual score
        qbs.sort(key=lambda x: x.actual_score, reverse=True)
        rbs.sort(key=lambda x: x.actual_score, reverse=True)
        wrs.sort(key=lambda x: x.actual_score, reverse=True)
        tes.sort(key=lambda x: x.actual_score, reverse=True)
        dsts.sort(key=lambda x: x.actual_score, reverse=True)
        
        print(f"Top 5 QBs by score: {[f'{qb.name} ({qb.actual_score:.1f})' for qb in qbs[:5]]}")
        print(f"Top 5 RBs by score: {[f'{rb.name} ({rb.actual_score:.1f})' for rb in rbs[:5]]}")
        print(f"Top 5 WRs by score: {[f'{wr.name} ({wr.actual_score:.1f})' for wr in wrs[:5]]}")
        
        best_lineup = None
        best_score = 0
        attempts = 0
        max_attempts = 100000
        
        print(f"Searching for optimal lineup with IMPROVED STACK-FIRST approach...")
        
        # Step 1: Find all possible QB-WR/TE stacks and their scores
        print("Step 1: Finding all possible QB-WR/TE stacks...")
        stacks = []
        
        for qb in qbs[:10]:  # Top 10 QBs
            qb_team = qb.team
            
            # Find WRs from same team
            qb_wrs = [wr for wr in wrs if wr.team == qb_team]
            for wr in qb_wrs[:3]:  # Top 3 WRs from QB's team
                stack_score = qb.actual_score + wr.actual_score
                stack_salary = qb.salary + wr.salary
                stacks.append({
                    'type': 'QB-WR',
                    'qb': qb,
                    'partner': wr,
                    'score': stack_score,
                    'salary': stack_salary,
                    'remaining': DK_SALARY_CAP - stack_salary
                })
            
            # Find TEs from same team
            qb_tes = [te for te in tes if te.team == qb_team]
            for te in qb_tes[:2]:  # Top 2 TEs from QB's team
                stack_score = qb.actual_score + te.actual_score
                stack_salary = qb.salary + te.salary
                stacks.append({
                    'type': 'QB-TE',
                    'qb': qb,
                    'partner': te,
                    'score': stack_score,
                    'salary': stack_salary,
                    'remaining': DK_SALARY_CAP - stack_salary
                })
        
        # Sort stacks by total score
        stacks.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"Found {len(stacks)} possible stacks")
        print("Top 5 stacks:")
        for i, stack in enumerate(stacks[:5]):
            print(f"  {i+1}. {stack['qb'].name} + {stack['partner'].name} = {stack['score']:.1f} pts, ${stack['salary']:,}")
        
        # Step 2: For each stack, try to build the best possible lineup around it with smart budget allocation
        print("Step 2: Building lineups around each stack with smart budget allocation...")
        
        for stack in stacks[:20]:  # Try top 20 stacks
            attempts += 1
            if attempts > max_attempts:
                break
            
            qb = stack['qb']
            partner = stack['partner']
            stack_score = stack['score']
            remaining_salary = stack['remaining']
            
            print(f"Trying stack: {qb.name} + {partner.name} (Score: {stack_score:.1f}, Remaining: ${remaining_salary:,})")
            
            # Smart budget allocation: Reserve budget for each position
            # After stack, we need: 2 RB, 2-3 WR, 1 TE, 1 FLEX, 1 DST
            # Allocate budget more intelligently
            
            # Calculate average salaries for remaining positions to estimate budget needs
            avg_rb_salary = sum(rb.salary for rb in rbs[:20]) / 20
            avg_wr_salary = sum(wr.salary for wr in wrs[:30]) / 30
            avg_te_salary = sum(te.salary for te in tes[:20]) / 20
            avg_dst_salary = sum(dst.salary for dst in dsts[:10]) / 10
            
            # Estimate budget needed for remaining positions
            needed_wrs = 3 if stack['type'] == 'QB-TE' else 2  # Already have one WR if QB-WR stack
            estimated_budget_needed = (2 * avg_rb_salary) + (needed_wrs * avg_wr_salary) + avg_te_salary + avg_dst_salary
            
            if estimated_budget_needed > remaining_salary:
                print(f"  ⚠️  Estimated budget needed (${estimated_budget_needed:,.0f}) exceeds remaining (${remaining_salary:,})")
                continue
            
            # Try different budget allocation strategies
            budget_strategies = [
                {'rb_budget': 0.35, 'wr_budget': 0.35, 'te_budget': 0.15, 'dst_budget': 0.15},  # Balanced
                {'rb_budget': 0.40, 'wr_budget': 0.30, 'te_budget': 0.15, 'dst_budget': 0.15},  # RB-heavy
                {'rb_budget': 0.30, 'wr_budget': 0.40, 'te_budget': 0.15, 'dst_budget': 0.15},  # WR-heavy
                {'rb_budget': 0.25, 'wr_budget': 0.35, 'te_budget': 0.25, 'dst_budget': 0.15},  # TE-heavy
            ]
            
            for strategy in budget_strategies:
                rb_budget = remaining_salary * strategy['rb_budget']
                wr_budget = remaining_salary * strategy['wr_budget']
                te_budget = remaining_salary * strategy['te_budget']
                dst_budget = remaining_salary * strategy['dst_budget']
                
                print(f"  Strategy: RB=${rb_budget:,.0f}, WR=${wr_budget:,.0f}, TE=${te_budget:,.0f}, DST=${dst_budget:,.0f}")
                
                # Find RBs within budget
                available_rbs = [rb for rb in rbs if rb not in [qb, partner]]
                rb_combinations = []
                
                # Try to find 2 RBs that fit within budget, prioritizing value ratio
                available_rbs.sort(key=lambda x: x.value_ratio, reverse=True)
                for i, rb1 in enumerate(available_rbs[:20]):
                    for rb2 in available_rbs[i+1:20]:
                        if rb1.salary + rb2.salary <= rb_budget:
                            rb_combinations.append((rb1, rb2))
                            if len(rb_combinations) >= 10:
                                break
                    if len(rb_combinations) >= 10:
                        break
                
                if not rb_combinations:
                    print(f"    ❌ No RB combinations found within budget")
                    continue
                
                for rb1, rb2 in rb_combinations:
                    rb_salary = rb1.salary + rb2.salary
                    rb_score = rb1.actual_score + rb2.actual_score
                    remaining_after_rb = remaining_salary - rb_salary
                    
                    # Find WRs within budget
                    available_wrs = [wr for wr in wrs if wr not in [qb, partner, rb1, rb2]]
                    available_wrs.sort(key=lambda x: x.value_ratio, reverse=True)
                    
                    wr_combinations = []
                    if needed_wrs == 2:
                        for i, wr1 in enumerate(available_wrs[:15]):
                            for wr2 in available_wrs[i+1:15]:
                                if wr1.salary + wr2.salary <= wr_budget:
                                    wr_combinations.append((wr1, wr2))
                                    if len(wr_combinations) >= 10:
                                        break
                            if len(wr_combinations) >= 10:
                                break
                    else:  # needed_wrs == 3
                        for i, wr1 in enumerate(available_wrs[:10]):
                            for j, wr2 in enumerate(available_wrs[i+1:10]):
                                for wr3 in available_wrs[j+1:10]:
                                    if wr1.salary + wr2.salary + wr3.salary <= wr_budget:
                                        wr_combinations.append((wr1, wr2, wr3))
                                        if len(wr_combinations) >= 10:
                                            break
                                if len(wr_combinations) >= 10:
                                    break
                            if len(wr_combinations) >= 10:
                                break
                    
                    if not wr_combinations:
                        continue
                    
                    for wr_combo in wr_combinations:
                        if len(wr_combo) == 2:
                            wr1, wr2 = wr_combo
                            wr3 = None
                            wr_salary = wr1.salary + wr2.salary
                            wr_score = wr1.actual_score + wr2.actual_score
                        else:
                            wr1, wr2, wr3 = wr_combo
                            wr_salary = wr1.salary + wr2.salary + wr3.salary
                            wr_score = wr1.actual_score + wr2.actual_score + wr3.actual_score
                        
                        remaining_after_wr = remaining_after_rb - wr_salary
                        
                        # Find TE within budget
                        if stack['type'] == 'QB-TE':
                            te = partner
                            te_salary = te.salary
                            te_score = te.actual_score
                        else:
                            excluded_players = [qb, partner, rb1, rb2, wr1, wr2]
                            if wr3:
                                excluded_players.append(wr3)
                            available_tes = [te for te in tes if te not in excluded_players]
                            available_tes.sort(key=lambda x: x.value_ratio, reverse=True)
                            
                            te = None
                            te_salary = 0
                            te_score = 0
                            for potential_te in available_tes[:15]:
                                if potential_te.salary <= te_budget:
                                    te = potential_te
                                    te_salary = te.salary
                                    te_score = te.actual_score
                                    break
                            
                            if not te:
                                continue
                        
                        remaining_after_te = remaining_after_wr - te_salary
                        
                        # Find FLEX within remaining budget
                        excluded_players = [qb, partner, rb1, rb2, wr1, wr2, te]
                        if wr3:
                            excluded_players.append(wr3)
                        flex_pool = [p for p in rbs + wrs + tes if p not in excluded_players]
                        flex_pool.sort(key=lambda x: x.value_ratio, reverse=True)
                        
                        flex = None
                        flex_salary = 0
                        flex_score = 0
                        for potential_flex in flex_pool[:20]:
                            if potential_flex.salary <= remaining_after_te:
                                flex = potential_flex
                                flex_salary = potential_flex.salary
                                flex_score = potential_flex.actual_score
                                break
                        
                        if not flex:
                            continue
                        
                        remaining_after_flex = remaining_after_te - flex_salary
                        
                        # Find DST within budget
                        opponent_teams = [qb.team, rb1.team, rb2.team, wr1.team, wr2.team, te.team, flex.team]
                        available_dsts = [d for d in dsts if d.opponent not in opponent_teams]
                        
                        if not available_dsts:
                            available_dsts = dsts  # Fallback to all DSTs
                        
                        available_dsts.sort(key=lambda x: x.value_ratio, reverse=True)
                        
                        dst = None
                        dst_salary = 0
                        dst_score = 0
                        for potential_dst in available_dsts[:15]:
                            if potential_dst.salary <= dst_budget:
                                dst = potential_dst
                                dst_salary = potential_dst.salary
                                dst_score = potential_dst.actual_score
                                break
                        
                        if not dst:
                            continue
                        
                        # Calculate total
                        total_salary = stack['salary'] + rb_salary + wr_salary + te_salary + flex_salary + dst_salary
                        total_score = stack_score + rb_score + wr_score + te_score + flex_score + dst_score
                        
                        # Validate lineup
                        all_players = [qb, partner, rb1, rb2, wr1, wr2]
                        if wr3:
                            all_players.append(wr3)
                        all_players.extend([te, flex, dst])
                        
                        # Check for duplicates
                        player_names = [p.name for p in all_players]
                        if len(set(player_names)) != len(player_names):
                            continue
                        
                        # Check team diversity (at least 3 different teams)
                        teams = [p.team for p in all_players]
                        if len(set(teams)) < 3:
                            continue
                        
                        # Check salary cap constraint (HARD CONSTRAINT)
                        if total_salary > DK_SALARY_CAP:
                            continue
                        
                        # Check if this is the best lineup so far
                        if total_score > best_score:
                            best_score = total_score
                            best_lineup = OptimalLineup(
                                week=0,  # Will be set later
                                players=all_players,
                                total_score=total_score,
                                total_salary=total_salary
                            )
                            print(f"    ✅ New best STACKED lineup found! Score: {best_score:.2f}, Salary: {total_salary}, Stack: {qb.name} + {partner.name}")
                            print(f"    Budget allocation: RB=${rb_salary:,}, WR=${wr_salary:,}, TE=${te_salary:,}, DST=${dst_salary:,}")
        
        if best_lineup:
            print(f"🎉 Optimal STACKED lineup found after {attempts} attempts")
            print(f"Final score: {best_lineup.total_score:.2f}, Salary: {best_lineup.total_salary}")
        else:
            print(f"❌ No valid stacked lineup found after {attempts} attempts")
            
        return best_lineup
    
    def analyze_week(self, week: int) -> Optional[OptimalLineup]:
        """Analyze a single week and find optimal lineup"""
        print(f"Analyzing Week {week}...")
        
        # Load data
        week_data = self.load_week_data(week)
        if week_data.empty:
            print(f"No data found for Week {week}")
            return None
        
        # Create player objects
        players = self.create_player_objects(week_data)
        print(f"Valid players: {len(players)}")
        
        # Try stack-first approach first, fallback to basic if needed
        print("Trying stack-first optimal lineup search...")
        optimal = self.find_optimal_lineup_stack_first(players)
        
        if not optimal:
            print("Stack-first search failed, trying basic approach...")
            optimal = self.find_optimal_lineup(players)
        
        if optimal:
            optimal.week = week
            print(f"Optimal lineup found: {optimal.total_score:.2f} points, ${optimal.total_salary:,}")
            return optimal
        else:
            print("No valid lineup found")
            return None
    
    def analyze_all_weeks(self) -> Dict[int, OptimalLineup]:
        """Analyze all available weeks"""
        print("Finding optimal lineups for all weeks...")
        
        # Find all week directories
        week_dirs = [d for d in self.data_path.iterdir() if d.is_dir() and d.name.startswith('WEEK')]
        weeks = sorted([int(d.name[4:]) for d in week_dirs])
        
        print(f"Found weeks: {weeks}")
        
        optimal_lineups = {}
        for week in weeks:
            optimal = self.analyze_week(week)
            if optimal:
                optimal_lineups[week] = optimal
        
        self.optimal_lineups = optimal_lineups
        return optimal_lineups
    
    def analyze_lineup_construction_patterns(self) -> Dict:
        """Analyze patterns in optimal lineup construction"""
        print("\n=== Analyzing Lineup Construction Patterns ===")
        
        if not self.optimal_lineups:
            return {}
        
        patterns = {
            'total_lineups': len(self.optimal_lineups),
            'avg_total_score': np.mean([l.total_score for l in self.optimal_lineups.values()]),
            'avg_total_salary': np.mean([l.total_salary for l in self.optimal_lineups.values()]),
            'salary_utilization': np.mean([l.total_salary / DK_SALARY_CAP for l in self.optimal_lineups.values()]),
            'stack_analysis': {},
            'position_spending': {},
            'team_diversity': {},
            'defense_patterns': {},
            'flex_position_analysis': {}
        }
        
        # Stack analysis
        stack_data = []
        for week, lineup in self.optimal_lineups.items():
            stack_data.append({
                'week': week,
                'stack_count': lineup.stack_count,
                'stack_salary': lineup.stack_salary,
                'stack_salary_pct': lineup.stack_salary / lineup.total_salary * 100,
                'has_stack': lineup.stack_count > 0
            })
        
        stack_df = pd.DataFrame(stack_data)
        patterns['stack_analysis'] = {
            'avg_stack_count': stack_df['stack_count'].mean(),
            'avg_stack_salary': stack_df['stack_salary'].mean(),
            'avg_stack_salary_pct': stack_df['stack_salary_pct'].mean(),
            'weeks_with_stacks': stack_df['has_stack'].sum(),
            'stack_frequency': stack_df['has_stack'].mean()
        }
        
        # Position spending analysis
        position_spending_data = []
        for week, lineup in self.optimal_lineups.items():
            spending = lineup.position_spending
            spending['week'] = week
            position_spending_data.append(spending)
        
        pos_spending_df = pd.DataFrame(position_spending_data)
        patterns['position_spending'] = {
            'avg_qb_spending': pos_spending_df['QB'].mean(),
            'avg_rb_spending': pos_spending_df['RB'].mean(),
            'avg_wr_spending': pos_spending_df['WR'].mean(),
            'avg_te_spending': pos_spending_df['TE'].mean(),
            'avg_flex_spending': pos_spending_df.get('FLEX', pd.Series([0] * len(pos_spending_df))).mean(),
            'avg_dst_spending': pos_spending_df['DST'].mean()
        }
        
        # Team diversity analysis
        team_data = []
        for week, lineup in self.optimal_lineups.items():
            team_data.append({
                'week': week,
                'team_count': lineup.team_count,
                'teams': lineup.unique_teams
            })
        
        team_df = pd.DataFrame(team_data)
        patterns['team_diversity'] = {
            'avg_team_count': team_df['team_count'].mean(),
            'min_teams': team_df['team_count'].min(),
            'max_teams': team_df['team_count'].max(),
            'team_frequency': Counter([team for teams in team_df['teams'] for team in teams])
        }
        
        # Defense patterns
        defense_data = []
        for week, lineup in self.optimal_lineups.items():
            dst = lineup.dst
            if dst:
                defense_data.append({
                    'week': week,
                    'dst_team': dst.team,
                    'dst_opponent': dst.opponent,
                    'has_conflict': lineup.defense_opponent_conflict,
                    'dst_salary': dst.salary,
                    'dst_score': dst.actual_score
                })
        
        defense_df = pd.DataFrame(defense_data)
        patterns['defense_patterns'] = {
            'avg_dst_salary': defense_df['dst_salary'].mean(),
            'avg_dst_score': defense_df['dst_score'].mean(),
            'conflict_frequency': defense_df['has_conflict'].mean(),
            'dst_team_frequency': defense_df['dst_team'].value_counts().to_dict()
        }
        
        # FLEX position analysis
        flex_data = []
        for week, lineup in self.optimal_lineups.items():
            flex = lineup.flex
            if flex:
                flex_data.append({
                    'week': week,
                    'flex_position': flex.position,
                    'flex_salary': flex.salary,
                    'flex_score': flex.actual_score,
                    'flex_team': flex.team
                })
        
        flex_df = pd.DataFrame(flex_data)
        patterns['flex_position_analysis'] = {
            'flex_position_distribution': flex_df['flex_position'].value_counts().to_dict(),
            'avg_flex_salary': flex_df['flex_salary'].mean(),
            'avg_flex_score': flex_df['flex_score'].mean()
        }
        
        return patterns
    
    def generate_lineup_construction_report(self) -> str:
        """Generate comprehensive lineup construction report"""
        print("\n=== Generating Lineup Construction Report ===")
        
        if not self.optimal_lineups:
            return "No optimal lineups found for analysis"
        
        report = []
        report.append("=" * 80)
        report.append("2024 NFL DFS OPTIMAL LINEUP CONSTRUCTION ANALYSIS")
        report.append("=" * 80)
        report.append("")
        
        # Basic statistics
        total_lineups = len(self.optimal_lineups)
        avg_score = np.mean([l.total_score for l in self.optimal_lineups.values()])
        avg_salary = np.mean([l.total_salary for l in self.optimal_lineups.values()])
        salary_utilization = np.mean([l.total_salary / DK_SALARY_CAP for l in self.optimal_lineups.values()])
        
        report.append(f"ANALYSIS SUMMARY:")
        report.append(f"- Optimal lineups found: {total_lineups}")
        report.append(f"- Average optimal score: {avg_score:.2f} points")
        report.append(f"- Average salary used: ${avg_salary:,.0f}")
        report.append(f"- Average salary utilization: {salary_utilization:.1%}")
        report.append("")
        
        # Analyze patterns
        patterns = self.analyze_lineup_construction_patterns()
        
        # Stack analysis
        stack_analysis = patterns['stack_analysis']
        report.append("STACK CONSTRUCTION PATTERNS:")
        report.append(f"- Average stacks per lineup: {stack_analysis['avg_stack_count']:.2f}")
        report.append(f"- Average stack salary: ${stack_analysis['avg_stack_salary']:,.0f}")
        report.append(f"- Average stack salary %: {stack_analysis['avg_stack_salary_pct']:.1f}%")
        report.append(f"- Weeks with stacks: {stack_analysis['weeks_with_stacks']}/{total_lineups}")
        report.append(f"- Stack frequency: {stack_analysis['stack_frequency']:.1%}")
        report.append("")
        
        # Position spending
        pos_spending = patterns['position_spending']
        report.append("POSITION SPENDING PATTERNS:")
        report.append(f"- QB: ${pos_spending['avg_qb_spending']:,.0f} ({pos_spending['avg_qb_spending']/avg_salary:.1%})")
        report.append(f"- RB: ${pos_spending['avg_rb_spending']:,.0f} ({pos_spending['avg_rb_spending']/avg_salary:.1%})")
        report.append(f"- WR: ${pos_spending['avg_wr_spending']:,.0f} ({pos_spending['avg_wr_spending']/avg_salary:.1%})")
        report.append(f"- TE: ${pos_spending['avg_te_spending']:,.0f} ({pos_spending['avg_te_spending']/avg_salary:.1%})")
        report.append(f"- FLEX: ${pos_spending['avg_flex_spending']:,.0f} ({pos_spending['avg_flex_spending']/avg_salary:.1%})")
        report.append(f"- DST: ${pos_spending['avg_dst_spending']:,.0f} ({pos_spending['avg_dst_spending']/avg_salary:.1%})")
        report.append("")
        
        # Team diversity
        team_diversity = patterns['team_diversity']
        report.append("TEAM DIVERSITY PATTERNS:")
        report.append(f"- Average teams per lineup: {team_diversity['avg_team_count']:.1f}")
        report.append(f"- Team range: {team_diversity['min_teams']} - {team_diversity['max_teams']} teams")
        report.append("")
        
        # Defense patterns
        defense_patterns = patterns['defense_patterns']
        report.append("DEFENSE SELECTION PATTERNS:")
        report.append(f"- Average DST salary: ${defense_patterns['avg_dst_salary']:,.0f}")
        report.append(f"- Average DST score: {defense_patterns['avg_dst_score']:.2f} points")
        report.append(f"- DST vs lineup conflict frequency: {defense_patterns['conflict_frequency']:.1%}")
        report.append("")
        
        # FLEX analysis
        flex_analysis = patterns['flex_position_analysis']
        report.append("FLEX POSITION PATTERNS:")
        for pos, count in flex_analysis['flex_position_distribution'].items():
            report.append(f"- {pos}: {count} times ({count/total_lineups:.1%})")
        report.append(f"- Average FLEX salary: ${flex_analysis['avg_flex_salary']:,.0f}")
        report.append(f"- Average FLEX score: {flex_analysis['avg_flex_score']:.2f} points")
        report.append("")
        
        # Detailed lineup breakdowns
        report.append("DETAILED LINEUP BREAKDOWNS:")
        for week, lineup in sorted(self.optimal_lineups.items()):
            report.append(f"\nWeek {week} - {lineup.total_score:.2f} points, ${lineup.total_salary:,}")
            report.append(f"  QB: {lineup.qb.name} ({lineup.qb.team}) - ${lineup.qb.salary:,} - {lineup.qb.actual_score:.2f} pts")
            report.append(f"  RB: {lineup.rbs[0].name} ({lineup.rbs[0].team}) - ${lineup.rbs[0].salary:,} - {lineup.rbs[0].actual_score:.2f} pts")
            report.append(f"  RB: {lineup.rbs[1].name} ({lineup.rbs[1].team}) - ${lineup.rbs[1].salary:,} - {lineup.rbs[1].actual_score:.2f} pts")
            report.append(f"  WR: {lineup.wrs[0].name} ({lineup.wrs[0].team}) - ${lineup.wrs[0].salary:,} - {lineup.wrs[0].actual_score:.2f} pts")
            report.append(f"  WR: {lineup.wrs[1].name} ({lineup.wrs[1].team}) - ${lineup.wrs[1].salary:,} - {lineup.wrs[1].actual_score:.2f} pts")
            report.append(f"  WR: {lineup.wrs[2].name} ({lineup.wrs[2].team}) - ${lineup.wrs[2].salary:,} - {lineup.wrs[2].actual_score:.2f} pts")
            report.append(f"  TE: {lineup.te.name} ({lineup.te.team}) - ${lineup.te.salary:,} - {lineup.te.actual_score:.2f} pts")
            if lineup.flex:
                report.append(f"  FLEX: {lineup.flex.name} ({lineup.flex.team}) - ${lineup.flex.salary:,} - {lineup.flex.actual_score:.2f} pts")
            report.append(f"  DST: {lineup.dst.name} ({lineup.dst.team}) - ${lineup.dst.salary:,} - {lineup.dst.actual_score:.2f} pts")
            report.append(f"  Teams: {', '.join(lineup.unique_teams)} ({lineup.team_count} teams)")
            report.append(f"  Stacks: {lineup.stack_count} ({lineup.stack_salary:,} salary)")
            report.append(f"  DST conflict: {'Yes' if lineup.defense_opponent_conflict else 'No'}")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def save_detailed_lineup_data(self, output_file: str = "optimal_lineup_details.csv"):
        """Save detailed lineup data to CSV"""
        print(f"\nSaving detailed lineup data to {output_file}")
        
        if not self.optimal_lineups:
            return
        
        lineup_data = []
        for week, lineup in self.optimal_lineups.items():
            for player in lineup.players:
                lineup_data.append({
                    'Week': week,
                    'Position': player.position,
                    'Name': player.name,
                    'Team': player.team,
                    'Opponent': player.opponent,
                    'Salary': player.salary,
                    'Actual_Score': player.actual_score,
                    'Value_Ratio': player.value_ratio,
                    'Lineup_Total_Score': lineup.total_score,
                    'Lineup_Total_Salary': lineup.total_salary,
                    'Team_Count': lineup.team_count,
                    'Stack_Count': lineup.stack_count,
                    'Stack_Salary': lineup.stack_salary,
                    'DST_Conflict': lineup.defense_opponent_conflict
                })
        
        df = pd.DataFrame(lineup_data)
        df.to_csv(output_file, index=False)
        print(f"Saved {len(lineup_data)} player entries to {output_file}")
    
    def analyze_lineup_patterns_across_weeks(self, weeks_data: Dict[int, OptimalLineup]) -> Dict:
        """Analyze patterns across multiple weeks of optimal lineups"""
        if not weeks_data:
            return {}
        
        analysis = {
            'summary_stats': {},
            'stack_analysis': {},
            'salary_patterns': {},
            'team_utilization': {},
            'position_patterns': {},
            'value_patterns': {},
            'weekly_breakdown': {}
        }
        
        # Summary statistics
        total_weeks = len(weeks_data)
        total_score = sum(lineup.total_score for lineup in weeks_data.values())
        total_salary = sum(lineup.total_salary for lineup in weeks_data.values())
        
        analysis['summary_stats'] = {
            'total_weeks': total_weeks,
            'total_score': total_score,
            'average_score_per_week': total_score / total_weeks,
            'total_salary': total_salary,
            'average_salary_per_week': total_salary / total_weeks,
            'average_salary_utilization': (total_salary / (total_weeks * DK_SALARY_CAP)) * 100
        }
        
        # Stack analysis
        stack_data = []
        for week, lineup in weeks_data.items():
            for qb, partner in lineup.all_stacks:
                stack_data.append({
                    'week': week,
                    'qb_name': qb.name,
                    'qb_team': qb.team,
                    'partner_name': partner.name,
                    'partner_position': partner.position,
                    'combined_score': qb.actual_score + partner.actual_score,
                    'combined_salary': qb.salary + partner.salary,
                    'stack_value_ratio': ((qb.actual_score + partner.actual_score) / (qb.salary + partner.salary)) * 1000
                })
        
        if stack_data:
            analysis['stack_analysis'] = {
                'total_stacks': len(stack_data),
                'average_stack_score': sum(s['combined_score'] for s in stack_data) / len(stack_data),
                'average_stack_salary': sum(s['combined_salary'] for s in stack_data) / len(stack_data),
                'average_stack_value': sum(s['stack_value_ratio'] for s in stack_data) / len(stack_data),
                'stack_details': stack_data,
                'most_common_qb_teams': self._get_most_common([s['qb_team'] for s in stack_data]),
                'most_common_partner_positions': self._get_most_common([s['partner_position'] for s in stack_data])
            }
        
        # Salary patterns by position
        position_salaries = defaultdict(list)
        for lineup in weeks_data.values():
            for player in lineup.players:
                position_salaries[player.position].append(player.salary)
        
        analysis['salary_patterns'] = {
            'average_by_position': {
                pos: sum(salaries) / len(salaries) 
                for pos, salaries in position_salaries.items()
            },
            'total_spending_by_position': {
                pos: sum(salaries) 
                for pos, salaries in position_salaries.items()
            },
            'position_spending_percentage': {
                pos: (sum(salaries) / total_salary) * 100 
                for pos, salaries in position_salaries.items()
            }
        }
        
        # Team utilization patterns
        team_counts = defaultdict(int)
        team_scores = defaultdict(list)
        team_salaries = defaultdict(list)
        
        for lineup in weeks_data.values():
            for player in lineup.players:
                team_counts[player.team] += 1
                team_scores[player.team].append(player.actual_score)
                team_salaries[player.team].append(player.salary)
        
        analysis['team_utilization'] = {
            'most_used_teams': self._get_most_common([team for team, count in team_counts.items() for _ in range(count)]),
            'team_average_scores': {
                team: sum(scores) / len(scores) 
                for team, scores in team_scores.items()
            },
            'team_average_salaries': {
                team: sum(salaries) / len(salaries) 
                for team, salaries in team_salaries.items()
            },
            'teams_in_optimal_lineups': list(team_counts.keys())
        }
        
        # Position patterns
        position_counts = defaultdict(int)
        position_scores = defaultdict(list)
        position_values = defaultdict(list)
        
        for lineup in weeks_data.values():
            for player in lineup.players:
                position_counts[player.position] += 1
                position_scores[player.position].append(player.actual_score)
                position_values[player.position].append(player.value_ratio)
        
        analysis['position_patterns'] = {
            'position_frequency': dict(position_counts),
            'average_scores_by_position': {
                pos: sum(scores) / len(scores) 
                for pos, scores in position_scores.items()
            },
            'average_value_by_position': {
                pos: sum(values) / len(values) 
                for pos, values in position_values.items()
            }
        }
        
        # Value patterns
        all_values = []
        for lineup in weeks_data.values():
            for player in lineup.players:
                all_values.append(player.value_ratio)
        
        analysis['value_patterns'] = {
            'average_value_ratio': sum(all_values) / len(all_values),
            'min_value_ratio': min(all_values),
            'max_value_ratio': max(all_values),
            'value_ratio_distribution': self._get_value_distribution(all_values)
        }
        
        # Weekly breakdown
        analysis['weekly_breakdown'] = {
            week: {
                'score': lineup.total_score,
                'salary': lineup.total_salary,
                'utilization': (lineup.total_salary / DK_SALARY_CAP) * 100,
                'team_count': lineup.team_count,
                'stack_count': lineup.stack_count,
                'stacks': [(qb.name, partner.name) for qb, partner in lineup.all_stacks]
            }
            for week, lineup in weeks_data.items()
        }
        
        return analysis
    
    def _get_most_common(self, items: List) -> List[Tuple]:
        """Get most common items with their counts"""
        from collections import Counter
        counter = Counter(items)
        return counter.most_common()
    
    def _get_value_distribution(self, values: List[float]) -> Dict[str, int]:
        """Get distribution of value ratios"""
        distribution = {
            'Under 3.0': 0,
            '3.0-4.0': 0,
            '4.0-5.0': 0,
            '5.0-6.0': 0,
            '6.0-7.0': 0,
            'Over 7.0': 0
        }
        
        for value in values:
            if value < 3.0:
                distribution['Under 3.0'] += 1
            elif value < 4.0:
                distribution['3.0-4.0'] += 1
            elif value < 5.0:
                distribution['4.0-5.0'] += 1
            elif value < 6.0:
                distribution['5.0-6.0'] += 1
            elif value < 7.0:
                distribution['6.0-7.0'] += 1
            else:
                distribution['Over 7.0'] += 1
        
        return distribution
    
    def generate_pattern_analysis_report(self, analysis: Dict) -> str:
        """Generate a comprehensive pattern analysis report"""
        if not analysis:
            return "No analysis data available."
        
        report = []
        report.append("=" * 80)
        report.append("🏈 OPTIMAL LINEUP PATTERN ANALYSIS REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Summary Statistics
        summary = analysis.get('summary_stats', {})
        report.append("📊 SUMMARY STATISTICS")
        report.append("-" * 40)
        report.append(f"Total Weeks Analyzed: {summary.get('total_weeks', 0)}")
        report.append(f"Total Combined Score: {summary.get('total_score', 0):.2f} points")
        report.append(f"Average Score per Week: {summary.get('average_score_per_week', 0):.2f} points")
        report.append(f"Total Combined Salary: ${summary.get('total_salary', 0):,}")
        report.append(f"Average Salary per Week: ${summary.get('average_salary_per_week', 0):,.0f}")
        report.append(f"Average Salary Utilization: {summary.get('average_salary_utilization', 0):.1f}%")
        report.append("")
        
        # Stack Analysis
        stack_analysis = analysis.get('stack_analysis', {})
        if stack_analysis:
            report.append("🎯 STACK ANALYSIS")
            report.append("-" * 40)
            report.append(f"Total Stacks Used: {stack_analysis.get('total_stacks', 0)}")
            report.append(f"Average Stack Score: {stack_analysis.get('average_stack_score', 0):.2f} points")
            report.append(f"Average Stack Salary: ${stack_analysis.get('average_stack_salary', 0):,.0f}")
            report.append(f"Average Stack Value Ratio: {stack_analysis.get('average_stack_value', 0):.2f}")
            report.append("")
            
            # Most common QB teams in stacks
            qb_teams = stack_analysis.get('most_common_qb_teams', [])
            if qb_teams:
                report.append("Most Common QB Teams in Stacks:")
                for team, count in qb_teams[:5]:
                    report.append(f"  {team}: {count} times")
                report.append("")
            
            # Most common partner positions
            partner_positions = stack_analysis.get('most_common_partner_positions', [])
            if partner_positions:
                report.append("Most Common Stack Partner Positions:")
                for pos, count in partner_positions:
                    report.append(f"  {pos}: {count} times")
                report.append("")
            
            # Stack details
            stack_details = stack_analysis.get('stack_details', [])
            if stack_details:
                report.append("Detailed Stack Breakdown:")
                report.append(f"{'Week':<6} {'QB':<20} {'Partner':<20} {'Score':<8} {'Salary':<10} {'Value':<8}")
                report.append("-" * 80)
                for stack in stack_details:
                    report.append(f"{stack['week']:<6} {stack['qb_name'][:19]:<20} {stack['partner_name'][:19]:<20} "
                                f"{stack['combined_score']:<8.1f} ${stack['combined_salary']:<9,} {stack['stack_value_ratio']:<8.1f}")
                report.append("")
        
        # Salary Patterns
        salary_patterns = analysis.get('salary_patterns', {})
        if salary_patterns:
            report.append("💰 SALARY ALLOCATION PATTERNS")
            report.append("-" * 40)
            
            avg_by_pos = salary_patterns.get('average_by_position', {})
            if avg_by_pos:
                report.append("Average Salary by Position:")
                for pos, avg_salary in sorted(avg_by_pos.items(), key=lambda x: x[1], reverse=True):
                    report.append(f"  {pos}: ${avg_salary:,.0f}")
                report.append("")
            
            spending_pct = salary_patterns.get('position_spending_percentage', {})
            if spending_pct:
                report.append("Salary Spending by Position (%):")
                for pos, pct in sorted(spending_pct.items(), key=lambda x: x[1], reverse=True):
                    report.append(f"  {pos}: {pct:.1f}%")
                report.append("")
        
        # Team Utilization
        team_util = analysis.get('team_utilization', {})
        if team_util:
            report.append("🏈 TEAM UTILIZATION PATTERNS")
            report.append("-" * 40)
            
            most_used = team_util.get('most_used_teams', [])
            if most_used:
                report.append("Most Frequently Used Teams:")
                for team, count in most_used[:10]:
                    report.append(f"  {team}: {count} players")
                report.append("")
            
            team_scores = team_util.get('team_average_scores', {})
            if team_scores:
                report.append("Teams with Highest Average Scores:")
                top_teams = sorted(team_scores.items(), key=lambda x: x[1], reverse=True)[:10]
                for team, avg_score in top_teams:
                    report.append(f"  {team}: {avg_score:.2f} points")
                report.append("")
        
        # Position Patterns
        pos_patterns = analysis.get('position_patterns', {})
        if pos_patterns:
            report.append("📋 POSITION PATTERNS")
            report.append("-" * 40)
            
            freq = pos_patterns.get('position_frequency', {})
            if freq:
                report.append("Position Frequency:")
                for pos, count in sorted(freq.items(), key=lambda x: x[1], reverse=True):
                    report.append(f"  {pos}: {count} players")
                report.append("")
            
            avg_scores = pos_patterns.get('average_scores_by_position', {})
            if avg_scores:
                report.append("Average Scores by Position:")
                for pos, avg_score in sorted(avg_scores.items(), key=lambda x: x[1], reverse=True):
                    report.append(f"  {pos}: {avg_score:.2f} points")
                report.append("")
            
            avg_values = pos_patterns.get('average_value_by_position', {})
            if avg_values:
                report.append("Average Value Ratios by Position:")
                for pos, avg_value in sorted(avg_values.items(), key=lambda x: x[1], reverse=True):
                    report.append(f"  {pos}: {avg_value:.2f}")
                report.append("")
        
        # FLEX Position Analysis
        flex_analysis = analysis.get('flex_analysis', {})
        if flex_analysis:
            report.append("🎯 FLEX POSITION ANALYSIS")
            report.append("-" * 40)
            report.append(f"Total FLEX Players Analyzed: {flex_analysis.get('total_flex_players', 0)}")
            report.append("")
            
            position_counts = flex_analysis.get('position_counts', {})
            if position_counts:
                report.append("FLEX Position Distribution:")
                for pos, count in sorted(position_counts.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / flex_analysis.get('total_flex_players', 1)) * 100
                    report.append(f"  {pos}: {count} times ({percentage:.1f}%)")
                report.append("")
            
            most_common = flex_analysis.get('most_common_position')
            if most_common:
                pos, count = most_common
                report.append(f"Most Common FLEX Position: {pos} ({count} times)")
                report.append("")
            
            flex_players = flex_analysis.get('flex_players', [])
            if flex_players:
                report.append("Detailed FLEX Player Breakdown:")
                report.append(f"{'Week':<6} {'Player':<20} {'Position':<8} {'Team':<4} {'Score':<8} {'Salary':<10} {'Value':<8}")
                report.append("-" * 80)
                for player in flex_players:
                    report.append(f"{player['week']:<6} {player['name'][:19]:<20} {player['position']:<8} {player['team']:<4} "
                                f"{player['score']:<8.2f} ${player['salary']:<9,} {player['value_ratio']:<8.2f}")
                report.append("")
        
        # Value Patterns
        value_patterns = analysis.get('value_patterns', {})
        if value_patterns:
            report.append("📈 VALUE RATIO PATTERNS")
            report.append("-" * 40)
            report.append(f"Average Value Ratio: {value_patterns.get('average_value_ratio', 0):.2f}")
            report.append(f"Min Value Ratio: {value_patterns.get('min_value_ratio', 0):.2f}")
            report.append(f"Max Value Ratio: {value_patterns.get('max_value_ratio', 0):.2f}")
            report.append("")
            
            distribution = value_patterns.get('value_ratio_distribution', {})
            if distribution:
                report.append("Value Ratio Distribution:")
                for range_name, count in distribution.items():
                    if count > 0:
                        report.append(f"  {range_name}: {count} players")
                report.append("")
        
        # Weekly Breakdown
        weekly = analysis.get('weekly_breakdown', {})
        if weekly:
            report.append("📅 WEEKLY BREAKDOWN")
            report.append("-" * 40)
            report.append(f"{'Week':<6} {'Score':<8} {'Salary':<10} {'Util%':<6} {'Teams':<6} {'Stacks':<7}")
            report.append("-" * 50)
            for week in sorted(weekly.keys()):
                data = weekly[week]
                report.append(f"{week:<6} {data['score']:<8.2f} ${data['salary']:<9,} {data['utilization']:<6.1f} "
                            f"{data['team_count']:<6} {data['stack_count']:<7}")
            report.append("")
        
        report.append("=" * 80)
        report.append("End of Pattern Analysis Report")
        report.append("=" * 80)
        
        return "\n".join(report)

def main():
    """Main analysis function"""
    analyzer = OptimalLineupAnalyzer()
    
    # Analyze all weeks
    optimal_lineups = analyzer.analyze_all_weeks()
    
    if not optimal_lineups:
        print("No optimal lineups found. Exiting.")
        return
    
    # Generate lineup construction report
    report = analyzer.generate_lineup_construction_report()
    print(report)
    
    # Save detailed results
    analyzer.save_detailed_lineup_data()
    
    # Save report to file
    with open("optimal_lineup_construction_report.txt", "w") as f:
        f.write(report)
    
    print("\nOptimal lineup analysis complete!")
    print("Check optimal_lineup_construction_report.txt for detailed insights.")
    print("Check optimal_lineup_details.csv for detailed data.")

if __name__ == "__main__":
    main() 