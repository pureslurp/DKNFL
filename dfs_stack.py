import pandas as pd
import random
import numpy as np
import sys
import argparse
from utils import TEAM_DICT, CITY_TO_TEAM, BYE_DICT
from alive_progress import alive_bar

class Player:
    "A class to represent a Player"
    def __init__(self, player_df: pd.DataFrame):
        try:
            self.name = player_df["Name + ID"].iloc[0]
            self.position = player_df["Position"].iloc[0]
            self.salary = player_df["Salary"].iloc[0]
            try:
                self.score = player_df["Proj DFS Total"].iloc[0]
            except:
                self.score = player_df["Act DFS Total"].iloc[0]
            self.game_info = player_df["Game Info"].iloc[0]
            self.team = player_df["TeamAbbrev"].iloc[0]
        except:
            self.name = player_df["Name + ID"]
            self.position = player_df["Position"]
            self.salary = player_df["Salary"]
            try:
                self.score = player_df["Proj DFS Total"]
            except:
                self.score = player_df["Act DFS Total"]
            self.game_info = player_df["Game Info"]
            self.team = player_df["TeamAbbrev"]

    def get_value(self):
        "a function that returns the value of a Player"
        return self.score / self.salary * 1000
    
    def get_opponent(self):
        "a function that returns the opposing team of a Player"
        game_info = self.game_info.split(" ")[0].split("@")
        if game_info[0] == self.team:
            return game_info[1]
        else:
            return game_info[0]
    
    def get_attribute(self, attr: str):
        if attr == "value":
            return self.get_value()
        else:
            return self.score
        
    def __str__(self):
        return f'{self.name}'

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
                new_player = Player(candidate)
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
            new_player = Player(candidate)
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
    
class Stack:
    def __init__(self, qb: Player, wrte: Player) -> None:
        self.stack = {
            "QB" : qb,
            "WR/TE" : wrte
        }

    def get_salary(self):
        "a function that returns the total salary of a stack"
        return self.stack["QB"].salary + self.stack["WR/TE"].salary
    
    def get_total(self):
        "a function that returns the total projected score of a stack"
        return self.stack["QB"].score + self.stack["WR/TE"].score
    
    def get_attribute(self, attr: str):
        if attr == "value":
            return self.stack["QB"].get_value() + self.stack["WR/TE"].get_value()
        else:
            return self.get_total()
        
    def __str__(self):
        self._data = {
            "Name": [self.stack["QB"].name, self.stack["WR/TE"].name, "Total"],
            "Salary": [self.stack["QB"].salary, self.stack["WR/TE"].salary, self.get_salary()],
            "Score" : [self.stack["QB"].score, self.stack["WR/TE"].score, self.get_total()],
            "Value" : [self.stack["QB"].get_value(), self.stack["WR/TE"].get_value(), self.get_attribute("value")],
        }
        self.df = pd.DataFrame(self._data)
        return f"{self.df}"

    

def get_list_of_teams(df: pd.DataFrame) -> list:
    "a function that returns a list of all teams playing this week"
    teamList = df['TeamAbbrev'].values.tolist()
    res_teamList = []
    [res_teamList.append(x) for x in teamList if x not in res_teamList]
    return res_teamList

def qb_wr_stack(df: pd.DataFrame, team: str) -> pd.DataFrame:
    '''given a team, return potential list of stacks'''
    new_df = df[df['TeamAbbrev'] == team]
    new_df = new_df[(new_df["Position"] == "QB") | (new_df["Position"] == "WR") | (new_df["Position"] == "TE")]
    if len(new_df) < 3:
        raise Exception(f"Unable to pull data for {team}, please verify props have been populated for members of that team.")
    if len(new_df[new_df["Position"] == "QB"]) < 1:
        raise Exception(f"Unable to find a QB for {team}, please verify props have been populated for members of that team.")
    if len(new_df[(new_df["Position"] == "WR") | (new_df["Position"] == "TE")]) < 1:
        raise Exception(f"Unable to find a WR/TE for {team}, please verify props have been populated for members of that team.")
    return new_df


def highest_stack(stack_df: pd.DataFrame, attr: str ="point", limit:int=14500):
    "a function that returns the best stack from a list of a teams WRs and TEs"
    qb = Player(stack_df[stack_df["Position"] == "QB"].iloc[0])
    wrs = stack_df[(stack_df["Position"] == "WR") | (stack_df["Position"] == "TE")]
    value = 0
    for _, wr in wrs.iterrows():
        p = Player(wr)
        sal = qb.salary + p.salary
        if sal >= limit:
            continue
        else:
            score = qb.get_attribute(attr) + p.get_attribute(attr)
            if score > value:
                value = score
                player = p
    stack = Stack(qb, player)
    return stack

def find_best_stack(df: pd.DataFrame, attr:str="point", second_best:bool=False):
    "a function that finds the best stack from all the teams"
    stacks = {}
    for team in get_list_of_teams(df):
        high_stack = highest_stack(qb_wr_stack(df, team), attr)
        if high_stack.stack["QB"].salary < 5200:
            continue
        else:
            score = round(high_stack.get_attribute(attr), 2)
            stacks[high_stack] = score
    if second_best:
        return list({k: v for k, v in sorted(stacks.items(), key=lambda item: item[1])}.items())[-2][0]
    else:
        return list({k: v for k, v in sorted(stacks.items(), key=lambda item: item[1])}.items())[-1][0]

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


def generate_line_up_from_stack(df: pd.DataFrame, stack: Stack, NoL: int = 6) -> pd.DataFrame:
    """An optimized function that generates lineups based on a stack"""
    print(stack)
    dkRoster = pd.DataFrame(columns=("QB", "RB1", "RB2", "WR1", "WR2", "WR3", "TE", "FLEX", "DST", "Salary", "TotalPoints"))
    
    # Set up initial stack players
    qb = stack.stack["QB"]
    opp_team = qb.get_opponent()
    
    # Handle WR/TE stack player
    if stack.stack["WR/TE"].position == "WR":
        wr1 = stack.stack["WR/TE"]
        te_df = position_df(df, "TE").copy()
        te_df.loc[:, 'value'] = te_df['Proj DFS Total'] / te_df['Salary']
        te_df = te_df.sort_values(by='value', ascending=False)
        te = Player(te_df.iloc[0:1])
    else:
        te = stack.stack["WR/TE"]
        wr_df = position_df(df, "WR").copy()
        wr_df.loc[:, 'value'] = wr_df['Proj DFS Total'] / wr_df['Salary']
        wr_df = wr_df.sort_values(by='value', ascending=False)
        wr1 = Player(wr_df.iloc[0:1])

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
    dst_df = dst_df[dst_df["TeamAbbrev"] != opp_team].copy()
    dst_df.loc[:, 'value'] = dst_df['Proj DFS Total'] / dst_df['Salary']
    dst_df = dst_df.sort_values(by='value', ascending=False).head(10)
    dst_df.reset_index(drop=True, inplace=True)

    # Systematic lineup generation
    for rb1_idx in range(len(rb_df)):
        rb1 = Player(rb_df.iloc[rb1_idx:rb1_idx+1])
        
        for rb2_idx in range(rb1_idx + 1, len(rb_df)):
            rb2 = Player(rb_df.iloc[rb2_idx:rb2_idx+1])
            
            for wr2_idx in range(len(wr_df)):
                wr2 = Player(wr_df.iloc[wr2_idx:wr2_idx+1])
                
                for wr3_idx in range(wr2_idx + 1, len(wr_df)):
                    wr3 = Player(wr_df.iloc[wr3_idx:wr3_idx+1])
                    
                    for flex_idx in range(len(flex_df)):
                        flex = Player(flex_df.iloc[flex_idx:flex_idx+1])
                        
                        for dst_idx in range(len(dst_df)):
                            dst = Player(dst_df.iloc[dst_idx:dst_idx+1])
                            
                            # Create and validate lineup
                            lineup = LineUp(qb, rb1, rb2, wr1, wr2, wr3, te, flex, dst)
                            
                            if lineup.salary <= 50000 and not lineup.duplicates():
                                dkRoster.loc[len(dkRoster)] = lineup.to_dict()
                                
                            # Early stopping if we have enough high-quality lineups
                            if len(dkRoster) >= NoL * 2:
                                dkRoster.sort_values(by="TotalPoints", ascending=False, inplace=True, ignore_index=True)
                                return optimize_lineups(dkRoster.head(NoL), stack, df)

    # Final sorting and selection
    if len(dkRoster) == 0:
        print("No valid lineups found. Try adjusting the criteria.")
        return dkRoster
        
    dkRoster.sort_values(by="TotalPoints", ascending=False, inplace=True, ignore_index=True)
    return optimize_lineups(dkRoster.head(NoL), stack, df)

def optimize_lineups(lineups: pd.DataFrame, stack: Stack, df: pd.DataFrame):
    "a function that optimizes a set of lineups by going through each player and comparing the above and below players"
    wrt = stack.stack["WR/TE"]
    for index, lineup in lineups.iterrows():
        lineup_obj = LineUp(Player(df[df["Name + ID"] == lineup["QB"].name]), Player(df[df["Name + ID"] == lineup["RB1"].name]),  Player(df[df["Name + ID"] == lineup["RB2"].name]),  Player(df[df["Name + ID"] == lineup["WR1"].name]),  Player(df[df["Name + ID"] == lineup["WR2"].name]), Player(df[df["Name + ID"] == lineup["WR3"].name]), Player(df[df["Name + ID"] == lineup["TE"].name]), Player(df[df["Name + ID"] == lineup["FLEX"].name]),  Player(df[df["Name + ID"] == lineup["DST"].name]))
        lineup_obj = lineup_obj.optimize(df, wrt)
        lineup["TotalPoints"] = lineup_obj.total
        if lineup["TotalPoints"] in lineups["TotalPoints"].values:
            print("duplicate or too many players on same team")
            continue
        else:
            lineups.iloc[index] = list(lineup_obj.to_dict().values())
    return lineups

def find_opponent(data):
    '''Find who player is playing against from DK Salaries'''
    #(TODO) Fix this shit
    own = data[6]
    data = data[5].split('@')
    if len(data) > 1:
        opp = data[1].split(' ')
        data[1] = opp[0]
        for x in data:
            if x == own:
                pass
            else:
                opponent = x
        return TEAM_DICT[opponent]
    else:
        print('invalid data')

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
    
def defense(dk_pool: pd.DataFrame, WEEK:int):
    nfl_passing_offense = pd.read_html('https://www.nfl.com/stats/team-stats/offense/passing/2024/reg/all')
    nfl_rushing_offense = pd.read_html('https://www.nfl.com/stats/team-stats/offense/rushing/2024/reg/all')
    nfl_ppg = pd.read_html("https://www.teamrankings.com/nfl/stat/points-per-game")
    d_scale = np.linspace(-5, 5, 32)
    pass_offense = nfl_passing_offense[0]
    rush_offense = nfl_rushing_offense[0]
    ppg = nfl_ppg[0]

    dk_merge_def = pd.merge(pass_offense,rush_offense,how='left',on='Team')
    ppg["Opp"] = ppg["Team"].apply(lambda x: CITY_TO_TEAM[x])
    dk_merge_def['Opp'] = dk_merge_def['Team'].apply(lambda x: find_name(x))
    dk_merge_def = pd.merge(dk_merge_def,ppg,how='left',on='Opp')
    dk_merge_def['INT Pts'] = dk_merge_def.apply(lambda x: calc_df_INT_Pts(x, WEEK),axis=1)
    dk_merge_def['Sack Pts'] = dk_merge_def.apply(lambda x: calc_Sack_Pts(x, WEEK),axis=1)
    dk_merge_def['Fum Pts'] = dk_merge_def.apply(lambda x: calc_Fum_Pts(x, WEEK),axis=1)
    dk_merge_def['Pts Scored'] = dk_merge_def["2024"].apply(lambda x: points_for(x))
    dk_merge_def['Total'] = dk_merge_def['INT Pts'] + dk_merge_def['Sack Pts'] + dk_merge_def['Fum Pts'] + dk_merge_def['Pts Scored']
    dk_merge_def.sort_values(by=['Total'],ascending=True,inplace=True)
    dk_merge_def['Scale'] = d_scale
    dk_pool_def = dk_pool[dk_pool['Position'] == 'DST']
    dk_pool_def.drop(['ID'],axis=1,inplace=True)
    dk_pool_def['Opp'] = dk_pool_def.apply(lambda x: find_opponent(x),axis=1)
    dk_pool_def = pd.merge(dk_pool_def, dk_merge_def, how='left',on='Opp')
    dk_pool_def.to_csv(f'2024/Week{WEEK}/defense_debug.csv')
    dk_pool_def['DFS Total'] = ((dk_pool_def['AvgPointsPerGame']/dk_pool_def['AvgPointsPerGame'].max()) * 8) + dk_pool_def['Scale']
    dk_pool_def.drop(['Game Info','TeamAbbrev','AvgPointsPerGame','Scale','Opp'],axis=1,inplace=True)
    return dk_pool_def[["Name", "DFS Total"]]


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

    total_dict = {
        "forward" : "Proj DFS Total",
        "backtest" : "Act DFS Total"
    }

    if args.test == "forward":
        dk_stat = pd.read_csv(f"{path}NFL_PROJ_DFS.csv")
        csv_name = f"dk_lineups_week{WEEK}.csv"
    else:
        dk_stat = pd.read_csv(f"{path}box_score_debug.csv")
        csv_name = f"dk_lineups_week{WEEK}_backtest.csv"

    dk_stat["Name"] = dk_stat["Name"].apply(lambda x: fix_name(x))
    dk_defense = defense(dk_pool, WEEK)
    dk_stat = pd.concat([dk_stat, dk_defense], ignore_index=True)
    dfMain = pd.merge(dk_pool,dk_stat,how='left',on='Name')
    dfMain[total_dict[args.test]] = dfMain['DFS Total'].replace('', np.nan)
    dfMain.dropna(subset=[total_dict[args.test]], inplace=True)
    if args.test == "forward":
        dfMain.to_csv(f"{path}dashboard.csv")
    dfMain_DEF = dfMain[dfMain["Position"] == "DST"]

    dfMain_Players = dfMain[dfMain["Position"] != "DST"]
    dfMain_QB = dfMain[dfMain["Position"] == "QB"]
    dfMain_Players_noTEnoQB = dfMain_Players[(dfMain_Players["Position"] != "TE") & (dfMain_Players["Position"] != "QB")]
    dfMain_Players_TE = dfMain_Players[dfMain_Players["Position"] == "TE"]
    dfMain_Players_TE = dfMain_Players_TE[dfMain_Players_TE["Salary"] > 3400]
    dfMain_Players_noTEnoQB = dfMain_Players_noTEnoQB[dfMain_Players_noTEnoQB["Salary"] > 3100]
    frames = [dfMain_QB, dfMain_Players_TE, dfMain_DEF, dfMain_Players_noTEnoQB]
    dfMain = pd.concat(frames)
    dfMain.drop(["AvgPointsPerGame"],axis=1, inplace=True)
    dfMain["Value"] = (dfMain[total_dict[args.test]] / dfMain["Salary"]) * 1000
    best_stack_points = find_best_stack(dfMain)
    best_stack_value = find_best_stack(dfMain, attr="value")
    dk_lineup_points = generate_line_up_from_stack(dfMain, best_stack_points)
    print(dk_lineup_points)
    dk_lineup_points_2nd = generate_line_up_from_stack(dfMain, find_best_stack(dfMain, second_best=True))
    dk_lineup_points_comb = pd.concat([dk_lineup_points, dk_lineup_points_2nd])
    print(dk_lineup_points_comb)
    dk_lineup_value = generate_line_up_from_stack(dfMain, best_stack_value)
    dk_lineup_value_2nd = generate_line_up_from_stack(dfMain, find_best_stack(dfMain, attr="value", second_best=True))
    dk_lineup_value_comb = pd.concat([dk_lineup_value, dk_lineup_value_2nd])
    dk_lineup_comb = pd.concat([dk_lineup_points_comb, dk_lineup_value_comb])
    dk_lineup_comb.sort_values(by="TotalPoints", ascending=False, inplace=True, ignore_index=True)
    dk_lineup_comb.to_csv(f"{path}{csv_name}")

if __name__ == "__main__":
    main(sys.argv[1:])