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
            self.score = player_df["Proj DFS Total"].iloc[0]
            self.game_info = player_df["Game Info"].iloc[0]
            self.team = player_df["TeamAbbrev"].iloc[0]
        except:
            self.name = player_df["Name + ID"]
            self.position = player_df["Position"]
            self.salary = player_df["Salary"]
            self.score = player_df["Proj DFS Total"]
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
    "A class to represent a DraftKings lineup"
    def __init__(self, qb: Player, rb1: Player, rb2: Player, wr1: Player, wr2:Player, wr3: Player, te: Player, flex: Player, dst:Player):
        self.players = {"QB": qb,
             "RB1" : rb1,
             "RB2" : rb2,
             "WR1" : wr1,
             "WR2" : wr2,
             "WR3" : wr3,
             "TE" : te,
             "FLEX" : flex,
             "DST" : dst
            }
    
    def get_salary(self):
        "a function that will return the sum of the LineUps total salary"
        salary = 0
        for key in self.players:
            salary += self.players[key].salary
        return salary
        
    def get_total(self):
        "a function that will return the sum of the LineUps total projected score"
        total = 0
        for key in self.players:
            total += self.players[key].score
        return total
    
    def duplicates(self):
        "a function that will check the LineUp for duplicates"
        elem = []
        for key in self.players:
            elem.append(self.players[key].name)
        if len(elem) == len(set(elem)):
            return False
        else:
            return True
        
    def to_dict(self):
        "a function that will export the LineUp with salary and total points to a dictionary"
        self.players.update(
            {"Salary" : self.get_salary(),
             "TotalPoints" : self.get_total()})
        return self.players
    
    def __len__(self):
        return 9
    
    def get_lowest_sal_player(self):
        "a function that returns the player with the lowest salary (excluding defense)"
        _low_sal = 10000
        for key, value in self.players.items():
            if key != "DST":
                if value.salary < _low_sal:
                    _low_sal = value.salary
                    low_player = value
                    low_player_pos = key
        return low_player, low_player_pos


    def optimize(self, df, wrt):
        for pos, player in self.players.items():
            budget = self.get_salary()
            if player.position != "QB" and player.name != wrt.name:
                df_filt = df[df["Roster Position"].str.contains(pos)==True]
                df_filt = df_filt[(df_filt["Salary"] < player.salary + min(500, 50000-budget)) & (df_filt["Salary"] > player.salary - 500)] 
                for _, r2 in df_filt.iterrows():
                    new_player = Player(r2)
                    if new_player.score > self.players[pos].score and new_player.name not in self.names:
                        print(f"Replacing {self.players[pos].name} with {new_player.name}" )
                        self.players[pos] = new_player
        _low_player, _low_player_pos = self.get_lowest_sal_player()
        _budget = self.get_salary()
        df_filt = df[df["Roster Position"].str.contains(_low_player.position)==True]
        df_filt = df_filt[(df_filt["Salary"] < _low_player.salary + 50000-_budget) & (df_filt["Salary"] > _low_player.salary)] 
        for _, r2 in df_filt.iterrows():
            new_player = Player(r2)
            if new_player.score > _low_player.score and new_player.name not in self.names:
                print(f"Replacing {_low_player.name} with {new_player.name}" )
                _low_player = new_player
                self.players[_low_player_pos] = new_player
        return self
        
    @property
    def names(self):
        "a function that returns a list of Players in the LineUp"
        names = []
        for key in self.players:
            names.append(self.players[key].name)
        return names
    
    def __str__(self):
        return f'Lineup: {self.players}'
    
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


def highest_stack(stack_df: pd.DataFrame, attr: str ="point", limit:int=16400):
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
        Int_Pt_Est = (data["INT"] * 2) / (WEEK)
    return Int_Pt_Est 

def calc_Sack_Pts(data, WEEK):
    '''calculate sacks per game as DFS points'''
    if BYE_DICT[find_name(data[0])] < WEEK:
        Sck_Pt_Est = (data["Sck"]) / (WEEK - 2)
    else:
        Sck_Pt_Est = (data["Sck"]) / (WEEK)
    return Sck_Pt_Est   

def calc_Fum_Pts(data, WEEK):
    '''calculate fumbles per game as DFS points'''
    if BYE_DICT[find_name(data[0])] < WEEK:
        Fum_Pt_Est = (data["Rush FUM"] * 2) / (WEEK - 2)
    else:
        Fum_Pt_Est = (data["Rush FUM"] * 2) / (WEEK)
    return Fum_Pt_Est 


def generate_line_up_from_stack(df: pd.DataFrame, stack: Stack, NoL: int =6, iter:int =200000) -> pd.DataFrame:
    '''a function that generates a dataframe of lineups based on a stack
    
    Inputs:
        df (pd.DataFrame): the master dataframe with all players and info
        stack (Stack): the stack to be built around
        NoL (int): number of rows/lineups to generate from the stack
        iter (int): number of iterations to run

    Output:
        dkRoster (pd.DataFrame): a dataframe with stack lineups sorted by highest projected scores
    '''
    print(stack)
    dkRoster = pd.DataFrame(columns=("QB", "RB1", "RB2", "WR1", "WR2", "WR3", "TE", "FLEX", "DST", "Salary", "TotalPoints"))
    highest_points = 0
    qb = stack.stack["QB"]
    opp_team = qb.get_opponent()
    if stack.stack["WR/TE"].position == "WR":
        wr1 = stack.stack["WR/TE"]
        te_df = position_df(df, "TE")
        te = Player(te_df.iloc[[random.randint(0, len(te_df) - 1)]])
    else:
        te = stack.stack["WR/TE"]
        wr_df = position_df(df, "WR")
        wr1 = Player(wr_df.iloc[[random.randint(0, len(wr_df) - 1)]])
    rb_df = position_df(df, "RB")
    wr_df = position_df(df, "WR")
    flex_df = position_df(df, "FLEX")
    dst_df = position_df(df, "DST")
    dst_df = dst_df[dst_df["TeamAbbrev"] != opp_team]
    
    with alive_bar(iter) as bar:
        print("Building ultimate lineups...")
        for _ in range(iter):
            rb1 = Player(rb_df.iloc[[random.randint(0, len(rb_df) - 1)]])
            rb2 = Player(rb_df.iloc[[random.randint(0, len(rb_df) - 1)]])
            wr2 = Player(wr_df.iloc[[random.randint(0, len(wr_df) - 1)]])
            wr3 = Player(wr_df.iloc[[random.randint(0, len(wr_df) - 1)]])
            flex = Player(flex_df.iloc[[random.randint(0, len(flex_df) - 1)]])
            dst = Player(dst_df.iloc[[random.randint(0, len(dst_df) - 1)]])
            lineup = LineUp(qb, rb1, rb2, wr1, wr2, wr3, te, flex, dst)
            if lineup.get_salary() <= 50000 and (lineup.get_total() > highest_points) and not lineup.duplicates():
                dkRoster.loc[len(dkRoster)] = lineup.to_dict()
                dkRoster.sort_values(by="TotalPoints", ascending=False, inplace=True, ignore_index=True)
                dkRoster = dkRoster.iloc[0:NoL]
                if len(dkRoster) == (NoL + 1):
                    highest_points = float(dkRoster.iloc[NoL]["TotalPoints"])
            bar()
    dkRoster = optimize_lineups(dkRoster, stack, df)
    return dkRoster

def optimize_lineups(lineups: pd.DataFrame, stack: Stack, df: pd.DataFrame):
    "a function that optimizes a set of lineups by going through each player and comparing the above and below players"
    wrt = stack.stack["WR/TE"]
    for index, lineup in lineups.iterrows():
        lineup_obj = LineUp(Player(df[df["Name + ID"] == lineup["QB"].name]), Player(df[df["Name + ID"] == lineup["RB1"].name]),  Player(df[df["Name + ID"] == lineup["RB2"].name]),  Player(df[df["Name + ID"] == lineup["WR1"].name]),  Player(df[df["Name + ID"] == lineup["WR2"].name]), Player(df[df["Name + ID"] == lineup["WR3"].name]), Player(df[df["Name + ID"] == lineup["TE"].name]), Player(df[df["Name + ID"] == lineup["FLEX"].name]),  Player(df[df["Name + ID"] == lineup["DST"].name]))
        lineup_obj = lineup_obj.optimize(df, wrt)
        lineup["TotalPoints"] = lineup_obj.get_total()
        if lineup["TotalPoints"] in lineups["TotalPoints"].values:
            print("duplicate")
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
    dk_merge_def['Pts Scored'] = dk_merge_def["2023"].apply(lambda x: points_for(x))
    dk_merge_def['Total'] = dk_merge_def['INT Pts'] + dk_merge_def['Sack Pts'] + dk_merge_def['Fum Pts'] + dk_merge_def['Pts Scored']
    dk_merge_def.sort_values(by=['Total'],ascending=True,inplace=True)
    dk_merge_def['Scale'] = d_scale
    dk_pool_def = dk_pool[dk_pool['Position'] == 'DST']
    dk_pool_def.drop(['ID'],axis=1,inplace=True)
    dk_pool_def['Opp'] = dk_pool_def.apply(lambda x: find_opponent(x),axis=1)
    dk_pool_def = pd.merge(dk_pool_def, dk_merge_def, how='left',on='Opp')
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

    if args.test == "forward":
        dk_stat = pd.read_csv(f"{path}NFL_PROJ_DFS.csv")
    else:
        dk_stat = pd.read_csv(f"{path}box_score_debug_week_{WEEK}.csv")

    dk_stat["Name"] = dk_stat["Name"].apply(lambda x: fix_name(x))
    dk_defense = defense(dk_pool, WEEK)
    dk_stat = pd.concat([dk_stat, dk_defense], ignore_index=True)
    dfMain = pd.merge(dk_pool,dk_stat,how='left',on='Name')
    dfMain['Proj DFS Total'] = dfMain['DFS Total'].replace('', np.nan)
    dfMain.dropna(subset=['Proj DFS Total'], inplace=True)
    dfMain.to_csv(f"{path}dashboard.csv")
    dfMain_DEF = dfMain[dfMain["Position"] == "DST"]
    dfMain_Players = dfMain[dfMain["Position"] != "DST"]
    dfMain_QB = dfMain[dfMain["Position"] == "QB"]
    dfMain_Players_noTEnoQB = dfMain_Players[(dfMain_Players["Position"] != "TE") & (dfMain_Players["Position"] != "QB")]
    dfMain_Players_TE = dfMain_Players[dfMain_Players["Position"] == "TE"]
    dfMain_Players_TE = dfMain_Players_TE[dfMain_Players_TE["Salary"] > 2400]
    dfMain_Players_noTEnoQB = dfMain_Players_noTEnoQB[dfMain_Players_noTEnoQB["Salary"] > 3100]
    frames = [dfMain_QB, dfMain_Players_TE, dfMain_DEF, dfMain_Players_noTEnoQB]
    dfMain = pd.concat(frames)
    dfMain.drop(["AvgPointsPerGame"],axis=1, inplace=True)
    dfMain["Value"] = (dfMain["Proj DFS Total"] / dfMain["Salary"]) * 1000
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
    dk_lineup_comb.to_csv(f"{path}dk_lineups_week{WEEK}.csv")

if __name__ == "__main__":
    main(sys.argv[1:])