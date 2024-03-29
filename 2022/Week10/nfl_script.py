#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Aug 28 19:03:29 2021

@author: seanraymor
"""
import pandas as pd
import numpy as np
pd.options.mode.chained_assignment = None  # default='warn'

import os

iterations = 100000

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
        return team_dict[opponent]
    else:
        print('invalid data')

def find_name(data):
    '''Make NFL.com team naming the same as DK team naming'''
    data = data.split('  ')
    return data[1]

def points_for(data):
    '''find each teams average points for'''
    if get_bye_week(find_name(data[0])) < Week:   
        Pts = (data[4] * 7) / (Week - 2)
    else:
        Pts = (data[4] * 7) / (Week - 1)
    # 1 – 6 Points Allowed +7 Pts
    # 7 – 13 Points Allowed +4 Pts
    # 14 – 20 Points Allowed +1 Pt
    # 21 – 27 Points Allowed +0 Pts
    # 28 – 34 Points Allowed -1 Pt
    # 35+ Points Allowed -4 Pts
    if Pts < 7:
        points = 7
    elif Pts > 6 and Pts < 14:
        points = 4
    elif Pts > 13 and Pts < 21:
        points = 1
    elif Pts > 20 and Pts < 28:
        points = 0
    elif Pts > 27 and Pts < 35:
        points = -1
    else:
        points = -4
    return points
    
def genIter():
    '''Generate a random lineup for analysis'''
    r0 = []
    qb = np.random.randint(0,high=len(dk_merge_qb))
    rb1 = np.random.randint(0,high=len(dk_merge_rb))
    rb2 = np.random.randint(0,high=len(dk_merge_rb))
    wr1 = np.random.randint(0,high=len(dk_merge_wr))
    wr2 = np.random.randint(0,high=len(dk_merge_wr))
    wr3 = np.random.randint(0,high=len(dk_merge_wr))
    te = np.random.randint(0,high=len(dk_merge_te))
    flex = np.random.randint(0,high=len(dk_merge_flex))
    dst = np.random.randint(0,high=len(dk_pool_def))
    r0.append(qb)
    r0.append(rb1)
    r0.append(rb2)
    r0.append(wr1)
    r0.append(wr2)
    r0.append(wr3)
    r0.append(te)
    r0.append(flex)
    r0.append(dst)
    return r0

def getNames(x):
    '''Convert ID from df to Names + ID'''
    n0 = []
    for iden in range(0,len(x)):
        if iden == 0:   
            n0.append(dk_merge_qb.loc[x[iden]]['Name + ID'])
        elif iden < 3:
            n0.append(dk_merge_rb.loc[x[iden]]['Name + ID'])
        elif iden < 6:
            n0.append(dk_merge_wr.loc[x[iden]]['Name + ID'])
        elif iden < 7:
            n0.append(dk_merge_te.loc[x[iden]]['Name + ID'])
        elif iden < 8:
            n0.append(dk_merge_flex.loc[x[iden]]['Name + ID'])
        else:
            n0.append(dk_pool_def.loc[x[iden]]['Name + ID'])
    return n0

def getID(x):
    '''Convert Names + ID to df ID'''
    i0 = []
    for iden in range(0,len(x)):
        if iden == 0:   
            i0.append(dk_merge_qb[dk_merge_qb['Name + ID'] == x[iden]].index)
        elif iden < 3:
            i0.append(dk_merge_rb[dk_merge_rb['Name + ID'] == x[iden]].index)
        elif iden < 6:
            i0.append(dk_merge_wr[dk_merge_wr['Name + ID'] == x[iden]].index)
        elif iden < 7:
            i0.append(dk_merge_te[dk_merge_te['Name + ID'] == x[iden]].index)
        elif iden < 8:
            i0.append(dk_merge_flex[dk_merge_flex['Name + ID'] == x[iden]].index)
        else:
            i0.append(dk_pool_def[dk_pool_def['Name + ID'] == x[iden]].index)
    return i0

def objective(x):
    '''Calculate the total points of a lineup (iteration)'''
    p0 = []
    for iden in range(0,len(x)):
        if iden == 0:   
            p0.append(float(dk_merge_qb.loc[x[iden]]['TOT']))
        elif iden < 3:
            p0.append(float(dk_merge_rb.loc[x[iden]]['TOT']))
        elif iden < 6:
            p0.append(float(dk_merge_wr.loc[x[iden]]['TOT']))
        elif iden < 7:
            p0.append(float(dk_merge_te.loc[x[iden]]['TOT'])) 
        elif iden < 8:
            p0.append(float(dk_merge_flex.loc[x[iden]]['TOT']))
        else:
            p0.append(float(dk_pool_def.loc[x[iden]]['TOT']))
    return sum(p0)
    
def constraint(x):
    '''Check if a lineup is within the DK Salary Range (50,000)'''
    valid = False
    s0 = []
    for iden in range(0,len(x)):
        if iden == 0:   
            s0.append(float(dk_merge_qb.loc[x[iden]]['Salary']))
        elif iden < 3:
            s0.append(float(dk_merge_rb.loc[x[iden]]['Salary']))
        elif iden < 6:
            s0.append(float(dk_merge_wr.loc[x[iden]]['Salary']))
        elif iden < 7:
            s0.append(float(dk_merge_te.loc[x[iden]]['Salary'])) 
        elif iden < 8:
            s0.append(float(dk_merge_flex.loc[x[iden]]['Salary']))
        else:
            s0.append(float(dk_pool_def.loc[x[iden]]['Salary']))
    if (50000 - sum(s0)) > 0:
        valid = True
    else:
        valid = False
    return valid

def get_salary(x):
    '''Find a lineups total salary'''
    s0 = []
    for iden in range(0,len(x)):
        if iden == 0:   
            s0.append(float(dk_merge_qb.loc[x[iden]]['Salary']))
        elif iden < 3:
            s0.append(float(dk_merge_rb.loc[x[iden]]['Salary']))
        elif iden < 6:
            s0.append(float(dk_merge_wr.loc[x[iden]]['Salary']))
        elif iden < 7:
            s0.append(float(dk_merge_te.loc[x[iden]]['Salary'])) 
        elif iden < 8:
            s0.append(float(dk_merge_flex.loc[x[iden]]['Salary']))
        else:
            s0.append(float(dk_pool_def.loc[x[iden]]['Salary']))
    return sum(s0)

def duplicates(x):
    '''Check if there are duplicates in the lineup (will only find duplicates in the same line up spot (i.e. RB1 <> RB1)'''
    if len(x) != len(set(x)):
        duplicates = True
    else:
        duplicates = False
    return duplicates

def value(data):
    '''Find the value of a player (point per dollar)'''
    value = float(data[3])/float(data[2])
    return value

def optimize(df, salary, pos, budget):
    '''Optimize a lineup by maximizing value

    Args: 
        df (DataFrame): The DataFrame to be optimized, should be a list of lineups
        salary (int): the current salary used by a lineup
        pos (string): the player to be optimized position (e.g. WR, RB, FLEX)
        budget (int): the current budget (50,000 - salary) that can be used
    
    Returns:
        window (string): The best value player to be replaced with the lineup that was passed
    '''
    if pos != 'FLEX':
        df = df[df['Position'] == pos]
    else:
        df = df[(df['Position'] == 'RB') | (df['Position'] == 'WR') | (df['Position'] == 'TE')]
        
    upper_bound = int(salary+(min(budget,1000)))
    lower_bound = int(salary) - 1000
    df.sort_values(by=['Value'],ascending = False, inplace=True)
    window = df[(df['Salary'] <= upper_bound) & (df['Salary'] > lower_bound)]
    #print(window)
    return window.iloc[0]['Name + ID']
    
def maximize(df, salary, pos, budget):
    '''Maximize a lineup by maximizing points

    Args: 
        df (DataFrame): The DataFrame to be maximized, should be a list of lineups
        salary (int): the current salary used by a lineup
        pos (string): the player to be optimized position (e.g. WR, RB, FLEX)
        budget (int): the current budget (50,000 - salary) that can be used
    
    Returns:
        window (string): The highest scoring player to be replaced with the lineup that was passed
    '''
    if pos != 'FLEX':
        df = df[df['Position'] == pos]
    else:
        df = df[(df['Position'] == 'RB') | (df['Position'] == 'WR') | (df['Position'] == 'TE')]
        
    upper_bound = int(salary+(min(budget,1000)))
    lower_bound = int(salary) - 500
    df.sort_values(by=['TOT'],ascending = False, inplace=True)
    window = df[(df['Salary'] <= upper_bound) & (df['Salary'] > lower_bound)]
    #print(window)
    return window.iloc[0]['Name + ID']

def get_bye_week(team):
    '''Find each teams bye week'''
    bye_dict = {
        'Football Team' : 9,
        'Buccaneers' : 9,
        'Seahawks' : 9,
        '49ers' : 6,
        'Chargers' : 7,
        'Steelers' : 7,
        'Cardinals' : 12,
        'Eagles' : 14,
        'Jets' : 6,
        'Giants' : 10,
        'Saints' : 6,
        'Patriots' : 14,
        'Vikings' : 7,
        'Dolphins' : 14,
        'Raiders' : 8,
        'Rams' : 11,
        'Chiefs' : 12,
        'Jaguars' : 7,
        'Colts' : 14,
        'Texans' : 10,
        'Titans' : 13,
        'Packers' : 13,
        'Lions' : 9,
        'Broncos' : 11,
        'Cowboys' : 7,
        'Browns' : 13,
        'Bengals' : 10,
        'Bears' : 10,
        'Panthers' : 13,
        'Bills' : 7,
        'Ravens' : 8,
        'Falcons' : 6
        }
    return bye_dict[team]

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

def calc_Yd_Pt_Est(data):
    '''Calculate yards per game as DFS points'''
    if get_bye_week(find_name(data[0])) < Week:
        AvgPYPG = data[1] / (Week - 2)
    else:
        AvgPYPG = data[1] / (Week - 1)
    return AvgPYPG
    
def calc_TD_Pt_Est(data):
    '''Calculate TDs per game as DFS points'''
    if get_bye_week(find_name(data[0])) < Week:
        TD_Pt_Est = (data[2] * 4) / (Week - 2)
    else:
        TD_Pt_Est = (data[2] * 4) / (Week - 1)
    return TD_Pt_Est

def calc_INT_Pt_Est(data):
    '''Calculate INTs per game as DFS points'''
    if get_bye_week(find_name(data[0])) < Week:
        INT_Pt_Est = (data[3] * -1) / (Week - 2)
    else:
        INT_Pt_Est = (data[3] * -1) / (Week - 1)
    return INT_Pt_Est

def calc_Rec_Pt_Est(data):
    '''Calculate Recs per game as DFS points'''
    if get_bye_week(find_name(data[0])) < Week:
        Rec_Pt_Est = (data[3] * -1) / (Week - 2)
    else:
        Rec_Pt_Est = (data[3] * -1) / (Week - 1)
    return Rec_Pt_Est

def calc_df_INT_Pts(data):
    '''calculate defensive INT per game as DFS points'''
    if get_bye_week(find_name(data[0])) < Week:
        Int_Pt_Est = (data[1] * 2) / (Week - 2)
    else:
        Int_Pt_Est = (data[1] * 2) / (Week - 1)
    return Int_Pt_Est 

def calc_Sack_Pts(data):
    '''calculate sacks per game as DFS points'''
    if get_bye_week(find_name(data[0])) < Week:
        Sck_Pt_Est = (data[2]) / (Week - 2)
    else:
        Sck_Pt_Est = (data[2]) / (Week - 1)
    return Sck_Pt_Est   

def calc_Fum_Pts(data):
    '''calculate fumbles per game as DFS points'''
    if get_bye_week(find_name(data[0])) < Week:
        Fum_Pt_Est = (data[3] * 2) / (Week - 2)
    else:
        Fum_Pt_Est = (data[3] * 2) / (Week - 1)
    return Fum_Pt_Est 

    # optimize

def optimize_main(topTierLineup):
    for index, row in topTierLineup.iterrows():
        print(index)
        maxNames = [row[0],row[1],row[2],row[3],row[4],row[5],row[6],row[7],row[8]]
        ID = getID(maxNames)
        # print(get_salary(getID(maxNames)))
        # print(maxNames)
        # print(maxIter)
        
        qb_salary = dk_merge_qb.loc[ID[0]]['Salary']
        rb1_salary = dk_merge_rb.loc[ID[1]]['Salary']
        rb2_salary = dk_merge_rb.loc[ID[2]]['Salary']
        wr1_salary = dk_merge_wr.loc[ID[3]]['Salary']
        wr2_salary = dk_merge_wr.loc[ID[4]]['Salary']
        wr3_salary = dk_merge_wr.loc[ID[5]]['Salary']
        te_salary = dk_merge_te.loc[ID[6]]['Salary']
        flex_salary = dk_merge_flex.loc[ID[7]]['Salary']
        dst_salary = dk_pool_def.loc[ID[8]]['Salary']
        
        budget = 50000 - get_salary(ID)
        
        if maxNames[3] != optimize(dk_final, flex_salary, 'FLEX', budget) and maxNames[4] != optimize(dk_final, flex_salary, 'FLEX', budget) and maxNames[5] != optimize(dk_final, flex_salary, 'FLEX', budget) and maxNames[1] != optimize(dk_final, flex_salary, 'FLEX', budget) and maxNames[2] != optimize(dk_final, flex_salary, 'FLEX', budget) and maxNames[6] != optimize(dk_final, flex_salary, 'FLEX', budget):
            maxNames[7] = optimize(dk_final, flex_salary, 'FLEX', budget)
            budget = 50000 - get_salary(getID(maxNames))
        
        if maxNames[0] != optimize(dk_final, qb_salary, 'QB', budget):
            maxNames[0] = optimize(dk_final, qb_salary, 'QB', budget)
            budget = 50000 - get_salary(getID(maxNames))
            
        if maxNames[1] != optimize(dk_final, rb1_salary, 'RB', budget) and maxNames[2] != optimize(dk_final, rb1_salary, 'RB',budget):
            maxNames[1] = optimize(dk_final, rb1_salary, 'RB', budget)
            budget = 50000 - get_salary(getID(maxNames))
            
        if maxNames[1] != optimize(dk_final, rb2_salary, 'RB', budget) and maxNames[2] != optimize(dk_final, rb2_salary, 'RB', budget):
            maxNames[2] = optimize(dk_final, rb2_salary, 'RB', budget)
            budget = 50000 - get_salary(getID(maxNames))
            
        if maxNames[3] != optimize(dk_final, wr1_salary, 'WR', budget) and maxNames[4] != optimize(dk_final, wr1_salary, 'WR', budget) and maxNames[5] != optimize(dk_final, wr1_salary, 'WR', budget):
            maxNames[3] = optimize(dk_final, wr1_salary, 'WR', budget)
            budget = 50000 - get_salary(getID(maxNames))
            
        if maxNames[3] != optimize(dk_final, wr2_salary, 'WR', budget) and maxNames[4] != optimize(dk_final, wr2_salary, 'WR', budget) and maxNames[5] != optimize(dk_final, wr2_salary, 'WR', budget):
            maxNames[4] = optimize(dk_final, wr2_salary, 'WR', budget)
            budget = 50000 - get_salary(getID(maxNames))
            
        if maxNames[3] != optimize(dk_final, wr3_salary, 'WR', budget) and maxNames[4] != optimize(dk_final, wr3_salary, 'WR', budget) and maxNames[5] != optimize(dk_final, wr3_salary, 'WR', budget):
            maxNames[5] = optimize(dk_final, wr3_salary, 'WR', budget)
            budget = 50000 - get_salary(getID(maxNames))
            
        if maxNames[6] != optimize(dk_final, te_salary, 'TE', budget):
            maxNames[6] = optimize(dk_final, te_salary, 'TE', budget)
            budget = 50000 - get_salary(getID(maxNames))
            
        if maxNames[8] != optimize(dk_final, dst_salary, 'DST', budget):
            maxNames[8] = optimize(dk_final, dst_salary, 'DST', budget)
            budget = 50000 - get_salary(getID(maxNames))
        
        # print(objective(getID(maxNames)))
        # print(maxNames)
        # print(get_salary(getID(maxNames)))
        newTotal = objective(getID(maxNames))
        maxNames.append(newTotal)
        OptimizedLineup.loc[index] = maxNames
        
    for index, row in OptimizedLineup.iterrows():
        if duplicates(row) == True:
            OptimizedLineup.drop(index, inplace = True)

    OptimizedLineup.reset_index(drop=True, inplace=True)
    
    return OptimizedLineup
        
def maximize_main(OptimizedLineup):
    # maximize
    for index, row in OptimizedLineup.iterrows():
        print(index)
        maxNames = [row[0],row[1],row[2],row[3],row[4],row[5],row[6],row[7],row[8]]
        ID = getID(maxNames)
        # print(get_salary(getID(maxNames)))
        # print(maxNames)
        # print(maxIter)
        
        qb_salary = dk_merge_qb.loc[ID[0]]['Salary']
        rb1_salary = dk_merge_rb.loc[ID[1]]['Salary']
        rb2_salary = dk_merge_rb.loc[ID[2]]['Salary']
        wr1_salary = dk_merge_wr.loc[ID[3]]['Salary']
        wr2_salary = dk_merge_wr.loc[ID[4]]['Salary']
        wr3_salary = dk_merge_wr.loc[ID[5]]['Salary']
        te_salary = dk_merge_te.loc[ID[6]]['Salary']
        flex_salary = dk_merge_flex.loc[ID[7]]['Salary']
        dst_salary = dk_pool_def.loc[ID[8]]['Salary']
        
        budget = 50000 - get_salary(ID)
        
        if maxNames[3] != maximize(dk_final, flex_salary, 'FLEX', budget) and maxNames[4] != maximize(dk_final, flex_salary, 'FLEX', budget) and maxNames[5] != maximize(dk_final, flex_salary, 'FLEX', budget) and maxNames[1] != maximize(dk_final, flex_salary, 'FLEX', budget) and maxNames[2] != maximize(dk_final, flex_salary, 'FLEX', budget) and maxNames[6] != maximize(dk_final, flex_salary, 'FLEX', budget):
            maxNames[7] = maximize(dk_final, flex_salary, 'FLEX', budget)
            budget = 50000 - get_salary(getID(maxNames))
        
        if maxNames[0] != maximize(dk_final, qb_salary, 'QB', budget):
            maxNames[0] = maximize(dk_final, qb_salary, 'QB', budget)
            budget = 50000 - get_salary(getID(maxNames))
            
        if maxNames[1] != maximize(dk_final, rb1_salary, 'RB', budget) and maxNames[2] != maximize(dk_final, rb1_salary, 'RB',budget):
            maxNames[1] = maximize(dk_final, rb1_salary, 'RB', budget)
            budget = 50000 - get_salary(getID(maxNames))
            
        if maxNames[1] != maximize(dk_final, rb2_salary, 'RB', budget) and maxNames[2] != maximize(dk_final, rb2_salary, 'RB', budget):
            maxNames[2] = maximize(dk_final, rb2_salary, 'RB', budget)
            budget = 50000 - get_salary(getID(maxNames))
            
        if maxNames[3] != maximize(dk_final, wr1_salary, 'WR', budget) and maxNames[4] != maximize(dk_final, wr1_salary, 'WR', budget) and maxNames[5] != maximize(dk_final, wr1_salary, 'WR', budget):
            maxNames[3] = maximize(dk_final, wr1_salary, 'WR', budget)
            budget = 50000 - get_salary(getID(maxNames))
            
        if maxNames[3] != maximize(dk_final, wr2_salary, 'WR', budget) and maxNames[4] != maximize(dk_final, wr2_salary, 'WR', budget) and maxNames[5] != maximize(dk_final, wr2_salary, 'WR', budget):
            maxNames[4] = maximize(dk_final, wr2_salary, 'WR', budget)
            budget = 50000 - get_salary(getID(maxNames))
            
        if maxNames[3] != maximize(dk_final, wr3_salary, 'WR', budget) and maxNames[4] != maximize(dk_final, wr3_salary, 'WR', budget) and maxNames[5] != maximize(dk_final, wr3_salary, 'WR', budget):
            maxNames[5] = maximize(dk_final, wr3_salary, 'WR', budget)
            budget = 50000 - get_salary(getID(maxNames))
            
        if maxNames[6] != maximize(dk_final, te_salary, 'TE', budget):
            maxNames[6] = maximize(dk_final, te_salary, 'TE', budget)
            budget = 50000 - get_salary(getID(maxNames))
            
        if maxNames[8] != maximize(dk_final, dst_salary, 'DST', budget):
            maxNames[8] = maximize(dk_final, dst_salary, 'DST', budget)
            budget = 50000 - get_salary(getID(maxNames))
        
        # print(objective(getID(maxNames)))
        # print(maxNames)
        # print(get_salary(getID(maxNames)))
        newTotal = objective(getID(maxNames))
        maxNames.append(newTotal)
        MaximizedLineup.loc[index] = maxNames
        
    for index, row in MaximizedLineup.iterrows():
        if duplicates(row) == True:
            MaximizedLineup.drop(index, inplace = True)
      
    #print(getNames(maxLineup))
    MaximizedLineup.to_csv(f'{path}/NFL_DK_LineUps.csv', index = False)
    return MaximizedLineup

Week = 10
path = f'DKNFL/Week{Week}/'
csv = f'{path}/DKSalaries-Week{Week}.csv'
dk_pool = pd.read_csv(csv)


nfl_rushing_defense = pd.read_html('https://www.nfl.com/stats/team-stats/defense/rushing/2021/reg/all')
nfl_passing_defense = pd.read_html('https://www.nfl.com/stats/team-stats/defense/passing/2021/reg/all')
nfl_receiving_defense = pd.read_html('https://www.nfl.com/stats/team-stats/defense/receiving/2021/reg/all')
nfl_passing_offense = pd.read_html('https://www.nfl.com/stats/team-stats/offense/passing/2021/reg/all')
nfl_rushing_offense = pd.read_html('https://www.nfl.com/stats/team-stats/offense/rushing/2021/reg/all')
nfl_scoring_offense = pd.read_html('https://www.nfl.com/stats/team-stats/offense/scoring/2021/reg/all')

rb_scale = np.linspace(-4, 4, 32)
wr_scale = np.linspace(-3, 3, 32)
qb_scale = np.linspace(-3, 3, 32)
d_scale = np.linspace(-2.5, 2.5, 32)

## QB DATA
passing_df = nfl_passing_defense[0]
passing_df['Opp'] = passing_df["Team"].apply(lambda x: find_name(x))
passing_df.drop(['Att','Cmp','Cmp %', 'Yds/Att','Rate','1st','1st%','20+','40+','Lng','Sck'],axis=1,inplace=True)
#1 pt per 25 yds, 4pt passing TD, 3 pt 300 yd game, -1 interception
passing_df['Yd Pt Est'] = passing_df.apply(lambda x: calc_Yd_Pt_Est(x),axis=1) * 0.04
passing_df['TD Pt Est'] = passing_df.apply(lambda x: calc_TD_Pt_Est(x),axis=1)
passing_df['INT Pt Est'] = passing_df.apply(lambda x: calc_INT_Pt_Est(x), axis=1)
passing_df['Total'] = passing_df['Yd Pt Est'] + passing_df['TD Pt Est'] + passing_df['INT Pt Est']
passing_df.sort_values(by=['Total'],inplace=True)
passing_df['Scale'] = qb_scale
passing_df.drop(['Total','TD','INT','Yd Pt Est','TD Pt Est','INT Pt Est','Yds','Team'],axis=1,inplace=True)
#print(passing_df.head())

dk_pool_qb = dk_pool[dk_pool['Position'] == "QB"]
dk_pool_qb.drop(['ID'],axis=1,inplace=True)
dk_pool_qb['Opp'] = dk_pool_qb.apply(lambda x: find_opponent(x),axis=1)
dk_merge_qb = pd.merge(dk_pool_qb,passing_df, how='left', on='Opp')
dk_merge_qb['TOT'] = dk_merge_qb['AvgPointsPerGame'] + dk_merge_qb['Scale']
dk_merge_qb = dk_merge_qb[dk_merge_qb['Salary'] > 4000]
dk_merge_qb.to_csv('qb_data.csv',index=False)
dk_merge_qb.drop(['Game Info', 'TeamAbbrev', 'Roster Position','AvgPointsPerGame','Opp','Scale'],axis=1,inplace=True)
#print(dk_merge_qb)

## RB DATA
rushing_df = nfl_rushing_defense[0]
rushing_df.drop(['Att','YPC','20+','40+','Lng','Rush 1st','Rush 1st%', 'Rush FUM'], axis=1,inplace=True)
rushing_df['Opp'] = rushing_df['Team'].apply(lambda x: find_name(x))
rushing_df['Yd Pt Est'] = rushing_df.apply(lambda x: calc_Yd_Pt_Est(x),axis=1) * 0.1
rushing_df['TD Pt Est'] = rushing_df.apply(lambda x: calc_TD_Pt_Est(x),axis=1) * 1.5
rushing_df['Total'] = rushing_df['Yd Pt Est'] + rushing_df['TD Pt Est']
rushing_df.sort_values(by=['Total'],inplace=True)
rushing_df['Scale'] = rb_scale
rushing_df.drop(['Total','Yd Pt Est','TD Pt Est','Team','Rush Yds','TD'],axis=1,inplace=True)
#print(rushing_df.head())
#1pt per 10yds or .1 pt per yard
#rush TD is 6 pts


dk_pool_rb = dk_pool[dk_pool['Position'] == 'RB']
dk_pool_rb.drop(['ID'],axis=1,inplace=True)
dk_pool_rb['Opp'] = dk_pool_rb.apply(lambda x: find_opponent(x),axis=1)
dk_merge_rb = pd.merge(dk_pool_rb,rushing_df, how='left', on='Opp')
dk_merge_rb['TOT'] = dk_merge_rb['AvgPointsPerGame'] + dk_merge_rb['Scale']
dk_merge_rb = dk_merge_rb[dk_merge_rb['Salary'] > 4000]
dk_merge_rb.drop(['Game Info', 'TeamAbbrev', 'Roster Position','AvgPointsPerGame','Opp','Scale'],axis=1,inplace=True)
#print(dk_merge.info())
#print(dk_merge_rb)


## WR DATA
receiving_df = nfl_receiving_defense[0]
receiving_df = receiving_df[['Team','Yds','TD','Rec']]
receiving_df['Yd Pt Est'] = receiving_df.apply(lambda x: calc_Yd_Pt_Est(x),axis=1) * 0.1
receiving_df['TD Pt Est'] = receiving_df.apply(lambda x: calc_TD_Pt_Est(x),axis=1) * 1.5
receiving_df['Rec Pt Est'] = receiving_df.apply(lambda x: calc_Rec_Pt_Est(x), axis=1)
receiving_df['Opp'] = receiving_df['Team'].apply(lambda x: find_name(x))
receiving_df['Total'] = receiving_df['Yd Pt Est'] + receiving_df['TD Pt Est'] + receiving_df['Rec Pt Est']
receiving_df.sort_values(by=['Total'],inplace=True)
receiving_df['Scale'] = wr_scale
receiving_df.drop(['Rec','Team','Yd Pt Est','Total','TD Pt Est','Rec Pt Est','TD','Yds'],axis=1,inplace=True)
#1pt per 10yds or .1 pt per yard
#rec TD is 6 pts
#rec is 1 pt

dk_pool_wr = dk_pool[dk_pool['Position'] == 'WR']
dk_pool_wr.drop(['ID'],axis=1,inplace=True)
dk_pool_wr['Opp'] = dk_pool_wr.apply(lambda x: find_opponent(x),axis=1)
dk_merge_wr = pd.merge(dk_pool_wr,receiving_df, how='left', on='Opp')
dk_merge_wr['TOT'] = dk_merge_wr['AvgPointsPerGame'] + dk_merge_wr['Scale']
dk_merge_wr = dk_merge_wr[dk_merge_wr['Salary'] > 3000]
dk_merge_wr.drop(['Game Info', 'TeamAbbrev', 'Roster Position','AvgPointsPerGame','Opp','Scale'],axis=1,inplace=True)
#print(dk_merge.info())
#print(dk_merge_wr)
#dk_merge_wr.to_csv('WR_Data.csv', index = False) 

## TE DATA
dk_pool_te = dk_pool[dk_pool['Position'] == 'TE']
dk_pool_te.drop(['ID'],axis=1,inplace=True)
dk_pool_te['Opp'] = dk_pool_te.apply(lambda x: find_opponent(x),axis=1)
dk_merge_te = pd.merge(dk_pool_te,receiving_df, how='left', on='Opp')
dk_merge_te['TOT'] = dk_merge_te['AvgPointsPerGame'] + dk_merge_te['Scale']
dk_merge_te = dk_merge_te[dk_merge_te['Salary'] > 2500]
dk_merge_te.drop(['Game Info', 'TeamAbbrev', 'Roster Position','AvgPointsPerGame','Opp','Scale'],axis=1,inplace=True)
#print(dk_merge.info())
#print(dk_merge_te)


## DEF DATA
pass_offense = nfl_passing_offense[0]
rush_offense = nfl_rushing_offense[0]
scoring_offense = nfl_scoring_offense[0]
#sack 1 pt
#int 2 pt
#fum 2 pt

pass_offense.drop(['Att','Cmp','Cmp %','Yds/Att','Pass Yds','Rate','TD','1st','1st%','20+','40+','Lng','SckY'],axis=1,inplace=True)
#print(pass_offense.info())
rush_offense.drop(['Att','Rush Yds','20+','40+','Lng','YPC','TD','Rush 1st','Rush 1st%'],axis=1,inplace=True)
#print(rush_offense.info())
scoring_offense.drop(['Rsh TD','Rec TD','2-PT'],axis=1,inplace=True)
#print(scoring_offense.info())
dk_merge_def = pd.merge(pass_offense,rush_offense,how='left',on='Team')
dk_merge_def = pd.merge(dk_merge_def,scoring_offense,how='left',on='Team')
dk_merge_def['Opp'] = dk_merge_def['Team'].apply(lambda x: find_name(x))
dk_merge_def['INT Pts'] = dk_merge_def.apply(lambda x: calc_df_INT_Pts(x),axis=1)
dk_merge_def['Sack Pts'] = dk_merge_def.apply(lambda x: calc_Sack_Pts(x),axis=1)
dk_merge_def['Fum Pts'] = dk_merge_def.apply(lambda x: calc_Fum_Pts(x),axis=1)
dk_merge_def['Pts Scored'] = dk_merge_def.apply(lambda x: points_for(x),axis=1)
dk_merge_def['Total'] = dk_merge_def['INT Pts'] + dk_merge_def['Sack Pts'] + dk_merge_def['Fum Pts'] + dk_merge_def['Pts Scored']
dk_merge_def.sort_values(by=['Total'],ascending=True,inplace=True)
dk_merge_def['Scale'] = d_scale
dk_merge_def.drop(['INT','Sck','Rush FUM','Tot TD','Team','INT Pts','Sack Pts','Total','Fum Pts','Pts Scored'],axis=1,inplace=True)

dk_pool_def = dk_pool[dk_pool['Position'] == 'DST']
dk_pool_def.drop(['ID'],axis=1,inplace=True)
dk_pool_def['Opp'] = dk_pool_def.apply(lambda x: find_opponent(x),axis=1)
dk_pool_def = pd.merge(dk_pool_def, dk_merge_def, how='left',on='Opp')
dk_pool_def['TOT'] = dk_pool_def['AvgPointsPerGame'] + dk_pool_def['Scale']
dk_pool_def.to_csv('dk_defense.csv', index = False)
dk_pool_def.drop(['Game Info','TeamAbbrev','Roster Position','AvgPointsPerGame','Scale','Opp'],axis=1,inplace=True)


## FLEX DATA
dk_merge_flex = pd.concat([dk_merge_rb,dk_merge_wr,dk_merge_te],ignore_index=True)
dk_merge_flex.sort_values(by=['TOT'],ascending=False,inplace=True)
#print(dk_merge_flex)

dk_final = pd.concat([dk_merge_flex, dk_pool_def, dk_merge_qb], ignore_index=True)
dk_final.drop(['Name'],axis=1,inplace=True)
dk_final['Value'] = dk_final.apply(lambda x: value(x),axis=1)
dk_final.to_csv(f'{path}DK_Final.csv', index = False)


## LINE UP
# 1 QB, 2 RB, 3 WR, 1 TE, 1 FLEX, 1 DST

i = 0
k = 0
maxIter = 0
topTierLineup = pd.DataFrame(columns=['QB','RB','RB','WR','WR','WR','TE','FLEX','DST','TOT'])
OptimizedLineup = pd.DataFrame(columns=['QB','RB','RB','WR','WR','WR','TE','FLEX','DST','TOT'])
MaximizedLineup = pd.DataFrame(columns=['QB','RB','RB','WR','WR','WR','TE','FLEX','DST','TOT'])

        

#main loop
while i < iterations:
    #get a sample
    lineup = genIter()
    #lineup.sort()
    #assign sample
    currentIter = objective(lineup)
    #check if sample is better than current best sample
    if currentIter > maxIter and constraint(lineup):
        #reassign
        maxIter = currentIter
        maxLineup = lineup
    #check if sample is a top tier sample
    if currentIter > 125 and constraint(lineup) and duplicates(getNames(lineup)) == False:
        #add players to top tier dataframe
        topTierData = getNames(lineup)
        topTierData.append(currentIter)
        #print(topTierData)
        topTierLineup.loc[k] = topTierData
        k = k + 1
    #iterate only if it is a valid lineup
    if constraint(lineup):
        i = i + 1
    #counter
    if i % 1000 == 0:
        print(i)
        
        
OptimizedLineup = optimize_main(topTierLineup)
maximize_main(OptimizedLineup)
        
        
        