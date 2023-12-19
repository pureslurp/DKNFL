from inspect import stack
from multiprocessing.sharedctypes import Value
import requests
import pandas as pd
import random



def get_list_of_teams(df):
    teamList = df['TeamAbbrev'].values.tolist()
    res_teamList = []
    [res_teamList.append(x) for x in teamList if x not in res_teamList]
    return res_teamList

def find_team_position(df, team, pos):
    playerList = []
    new_df = df[df["TeamAbbrev"] == team]
    new_df = new_df[new_df["Position"] == pos]
    return new_df

def qb_wr_stack(df, team):
    '''given a qb, find wr stacks points and salary'''
    new_df = df[df['TeamAbbrev'] == team]
    new_df = new_df[(new_df["Position"] == "QB") | (new_df["Position"] == "WR") | (new_df["Position"] == "TE")]
    return new_df


def highest_stack(stack, attr="point", limit=16000):
    if attr == 'value':
        col = "Value"
    else:
        col = "Projected Points"
    qb = stack[stack["Position"] == "QB"].iloc[0]
    wrs = stack[(stack["Position"] == "WR") | (stack["Position"] == "TE")]
    value = 0
    salary = 0
    for index, wr in wrs.iterrows():
        sal = float(qb["Salary"]) + float(wr["Salary"])
        if sal >= limit:
            continue
        else:
            score = float(qb[col]) + float(wr[col])
            if score > value:
                value = score
                player = wr["Name"]
                salary = int(qb["Salary"]) + int(wr["Salary"])
    new_df = stack[(stack["Name"] == qb["Name"]) | (stack["Name"] == player)]
    return new_df


def stack_sal(stack, attr="point"):
    if len(stack) != 2:
        raise ValueError("Stack must be 2")
    if attr == 'value':
        col = "Value"
    else:
        col = "Projected Points"
    score = sum(stack[col])
    sal = sum(stack["Salary"])
    return score, sal

def find_best_stack(df, attr="point"):
    highestTotal = 0
    for team in get_list_of_teams(df):
        score, sal = stack_sal(highest_stack(qb_wr_stack(df, team), attr), attr)
        if score > highestTotal:
            highestTotal = score
            bestStack = highest_stack(qb_wr_stack(df, team), attr)
    return bestStack

def find_2nd_best_stack(df, best_stack, attr="point"):
    highestTotal = 0
    best_stack_points = find_best_stack(df)
    best_stack_value = find_best_stack(df, attr="value")
    for team in get_list_of_teams(df):
        stack_entry = highest_stack(qb_wr_stack(df, team), attr)
        score, sal = stack_sal(stack_entry, attr)
        stack_check_points = stack_entry[stack_entry['Position'] == "QB"].equals(best_stack_points[best_stack_points["Position"] == "QB"])
        stack_check_value = stack_entry[stack_entry['Position'] == "QB"].equals(best_stack_value[best_stack_value["Position"] == "QB"])
        if score > highestTotal and stack_check_points is False and stack_check_value is False:
            highestTotal = score
            best2ndStack = highest_stack(qb_wr_stack(df, team), attr)
    return best2ndStack

def fix_player_name(name):
    if name == "DJ Chark":
        return "DJ Chark Jr."
    else:
        return name.strip()

def position_df(df, pos):
    if pos != "FLEX":
        new_df = df[df["Position"] == pos]
        new_df.reset_index(drop=True, inplace=True)
    else:
        new_df = df[(df["Position"] == "WR") | (df["Position"] == "RB")]
        new_df.reset_index(drop=True, inplace=True)
    return new_df

def checkDuplicates(df):
    elem = df["Name"].values
    if len(elem) == len(set(elem)):
        return False
    else:
        return True

def team_rb(df, team):
    print(team)


def generate_line_up_from_stack(df, stack, NoL=6):
    print(stack)
    dkRoster = pd.DataFrame(columns=("QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "DST", "TotalPoints"))
    highest_points = 0
    qb = stack[stack["Position"] == "QB"]
    if len(stack[stack["Position"] == "WR"]) == 1:
        wr1 = stack[stack["Position"] == "WR"]
        te_df = position_df(df, "TE")
        te = te_df.iloc[[random.randint(0, len(te_df) - 1)]]
    else:
        te = stack[stack["Position"] == "TE"]
        wr_df = position_df(df, "WR")
        wr1 = wr_df.iloc[[random.randint(0, len(wr_df) - 1)]]
    rb_df = position_df(df, "RB")
    wr_df = position_df(df, "WR")
    flex_df = position_df(df, "FLEX")
    dst_df = position_df(df, "DST")
    for x in range(200000):
        rb1 = rb_df.iloc[[random.randint(0, len(rb_df) - 1)]]
        rb2 = rb_df.iloc[[random.randint(0, len(rb_df) - 1)]]
        wr2 = wr_df.iloc[[random.randint(0, len(wr_df) - 1)]]
        wr3 = wr_df.iloc[[random.randint(0, len(wr_df) - 1)]]
        flex = flex_df.iloc[[random.randint(0, len(flex_df) - 1)]]
        dst = dst_df.iloc[[random.randint(0, len(dst_df) - 1)]]
        frames = [qb, rb1, rb2, wr1, wr2, wr3, te, flex, dst]
        res_df = pd.concat(frames)
        lineup = res_df["Name + ID"].values.tolist()
        sal = sum(res_df["Salary"])
        scores = sum(res_df["Projected Points"])
        lineup.append(scores)
        if sal <= 50000 and (scores > highest_points) and not checkDuplicates(res_df):
            dkRoster.loc[len(dkRoster)] = lineup
            dkRoster.sort_values(by="TotalPoints", ascending=False, inplace=True, ignore_index=True)
            dkRoster = dkRoster.iloc[0:NoL]
            if len(dkRoster) == (NoL + 1):
                highest_points = float(dkRoster.iloc[NoL]["TotalPoints"])


        if x % 10000 == 0:
            print(x)
    return dkRoster

def main():
    WEEK = 12
    playerData = []
    defData = []
    dfPoints = pd.DataFrame(columns=("Name", "Projected Points"))
    dfMain = pd.read_csv(f"DKSalaries-week{WEEK}.csv")
    dfMain_DEF = dfMain[dfMain["Position"] == "DST"]
    dfMain_Players = dfMain[dfMain["Position"] != "DST"]
    dfMain_Players_noTE = dfMain_Players[dfMain_Players["Position"] != "TE"]
    dfMain_Players_TE = dfMain_Players[dfMain_Players["Position"] == "TE"]
    dfMain_Players_TE = dfMain_Players_TE[dfMain_Players_TE["Salary"] > 2900]
    dfMain_Players_noTE = dfMain_Players_noTE[dfMain_Players_noTE["Salary"] > 3500]
    frames = [dfMain_Players_TE, dfMain_DEF, dfMain_Players_noTE]
    dfMain = pd.concat(frames)
    print(dfMain.info())
    dfMain.drop(["AvgPointsPerGame", "Roster Position"],axis=1, inplace=True)
    team_dict = {'TB' : 'Buccaneers',
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
                'WAS' : 'Football Team',
                'HOU' : 'Texans'
        }
    response = requests.get(f"https://api.sportsdata.io/v3/nfl/projections/json/PlayerGameProjectionStatsByWeek/2022REG/{WEEK}?key=bad0f33a84ad429da9bc6479ee509c26")
    for res in response.json():
        playerData.append(res)

    response_def = requests.get(f"https://api.sportsdata.io/v3/nfl/projections/json/FantasyDefenseProjectionsByGame/2022REG/{WEEK}?key=bad0f33a84ad429da9bc6479ee509c26")
    for res_d in response_def.json():
        defData.append(res_d)

    for data in playerData:
        # print(data["FantasyPointsDraftKings"])
        # if data["Description"] == "FantasyPointsPPR":
        row = [data["Name"], data["FantasyPointsDraftKings"]]
        dfPoints.loc[len(dfPoints)] = row

    for dst in defData:
        row = [team_dict[dst["Team"]], dst["FantasyPointsDraftKings"]]
        dfPoints.loc[len(dfPoints)] = row

    dfMain["Name"] = dfMain["Name"].apply(lambda x: fix_player_name(x))
    dfPoints["Name"] = dfPoints["Name"].apply(lambda x: fix_player_name(x))
    dfMain = pd.merge(dfMain, dfPoints, on="Name", how="left")
    dfMain["Value"] = (dfMain["Projected Points"] / dfMain["Salary"]) * 1000
    dfMain = dfMain[dfMain['Projected Points'].notna()]
    dfMain.to_csv(f"NFL_Projections_Week{WEEK}.csv")
    dfMain = dfMain[dfMain['Projected Points'] != 0]

    best_stack_points = find_best_stack(dfMain)
    best_stack_value = find_best_stack(dfMain, attr="value")
    dk_lineup_points = generate_line_up_from_stack(dfMain, best_stack_points)
    print(dk_lineup_points)
    dk_lineup_points_2nd = generate_line_up_from_stack(dfMain, find_2nd_best_stack(dfMain, best_stack_points))
    dk_lineup_points_comb = pd.concat([dk_lineup_points, dk_lineup_points_2nd])
    print(dk_lineup_points_comb)
    dk_lineup_value = generate_line_up_from_stack(dfMain, best_stack_value)
    dk_lineup_value_2nd = generate_line_up_from_stack(dfMain, find_2nd_best_stack(dfMain, best_stack_value, attr="value"))
    dk_lineup_value_comb = pd.concat([dk_lineup_value, dk_lineup_value_2nd])

    dk_lineup_comb = pd.concat([dk_lineup_points_comb, dk_lineup_value_comb])
    dk_lineup_comb.sort_values(by="TotalPoints", ascending=False, inplace=True, ignore_index=True)

    dk_lineup_comb.to_csv(f"dk_lineups_week{WEEK}.csv")

if __name__ == "__main__":
    main()