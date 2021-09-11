#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Aug 28 19:03:29 2021

@author: seanraymor
"""
import pandas as pd
import numpy as np
pd.options.mode.chained_assignment = None  # default='warn'

iterations = 100000

def find_opponent(data):
    own = data[5]
    data = data[4].split('@')
    opp = data[1].split(' ')
    data[1] = opp[0]
    for x in data:
        if x == own:
            pass
        else:
            opponent = x
    return team_dict[opponent]

def find_name(data):
    data = data.split('  ')
    return data[1]

def points_for(data):
    data = (data * 7) / 16
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
    
#Gneerate a random lineup
def genIter():
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

#Convert IDs into Names
def getNames(x):
    n0 = []
    for iden in range(0,len(x)):
        if iden == 0:   
            n0.append(dk_merge_qb.loc[x[iden]]['Name'])
        elif iden < 3:
            n0.append(dk_merge_rb.loc[x[iden]]['Name'])
        elif iden < 6:
            n0.append(dk_merge_wr.loc[x[iden]]['Name'])
        elif iden < 7:
            n0.append(dk_merge_te.loc[x[iden]]['Name'])
        elif iden < 8:
            n0.append(dk_merge_flex.loc[x[iden]]['Name'])
        else:
            n0.append(dk_pool_def.loc[x[iden]]['Name'])
            
    return n0

#Calculate total points of a lineup
def objective(x):
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
    
#Check if a lineup is within the Dk Salary range
def constraint(x):
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

def duplicates(x):
    if len(x) != len(set(x)):
        duplicates = True
    else:
        duplicates = False
    return duplicates
    

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

dk_pool = pd.read_csv('DKSalaries-Week1.csv')

nfl_rushing_defense = pd.read_html('https://www.nfl.com/stats/team-stats/defense/rushing/2020/reg/all')
nfl_passing_defense = pd.read_html('https://www.nfl.com/stats/team-stats/defense/passing/2020/reg/all')
nfl_receiving_defense = pd.read_html('https://www.nfl.com/stats/team-stats/defense/receiving/2020/reg/all')
nfl_passing_offense = pd.read_html('https://www.nfl.com/stats/team-stats/offense/passing/2020/reg/all')
nfl_rushing_offense = pd.read_html('https://www.nfl.com/stats/team-stats/offense/rushing/2020/reg/all')
nfl_scoring_offense = pd.read_html('https://www.nfl.com/stats/team-stats/offense/scoring/2020/reg/all')

scale = np.linspace(0, 10, 32)
d_scale = np.linspace(0, 5, 32)

## QB DATA
passing_df = nfl_passing_defense[0]
passing_df.drop(['Att','Cmp','Cmp %', 'Yds/Att','Rate','1st','1st%','20+','40+','Lng','Sck'],axis=1,inplace=True)
passing_df['AvgPYPG'] = passing_df['Yds'] / 16
#1 pt per 25 yds, 4pt passing TD, 3 pt 300 yd game, -1 interception
passing_df['Yd Pt Est'] = passing_df['AvgPYPG'] * 0.04
passing_df['TD Pt Est'] = (passing_df['TD'] * 4) / 16
passing_df['INT Pt Est'] = (passing_df['INT'] * -1) / 16
passing_df['Total'] = passing_df['Yd Pt Est'] + passing_df['TD Pt Est'] + passing_df['INT Pt Est']
passing_df['Opp'] = passing_df["Team"].apply(lambda x: find_name(x))
passing_df.sort_values(by=['Total'],inplace=True)
passing_df['Scale'] = scale
passing_df.drop(['AvgPYPG','Total','TD','INT','Yd Pt Est','TD Pt Est','INT Pt Est','Yds','Team'],axis=1,inplace=True)
#print(passing_df.head())

dk_pool_qb = dk_pool[dk_pool['Position'] == "QB"]
dk_pool_qb.drop(['Name + ID', 'ID'],axis=1,inplace=True)
dk_pool_qb['Opp'] = dk_pool_qb.apply(lambda x: find_opponent(x),axis=1)
dk_merge_qb = pd.merge(dk_pool_qb,passing_df, how='left', on='Opp')
dk_merge_qb['TOT'] = dk_merge_qb['AvgPointsPerGame'] + dk_merge_qb['Scale']
dk_merge_qb = dk_merge_qb[dk_merge_qb['Salary'] > 4000]
dk_merge_qb.drop(['Game Info', 'TeamAbbrev', 'Roster Position','AvgPointsPerGame','Opp','Scale'],axis=1,inplace=True)
#print(dk_merge_qb)




## RB DATA
rushing_df = nfl_rushing_defense[0]
rushing_df.drop(['Att','YPC','20+','40+','Lng','Rush 1st','Rush 1st%', 'Rush FUM'], axis=1,inplace=True)

rushing_df['AvgRYPG'] = rushing_df['Rush Yds'] / 16
rushing_df['TDpGame'] = rushing_df['TD'] / 16
rushing_df.drop(['Rush Yds','TD'], axis=1, inplace=True)
rushing_df['Yd Pt Est'] = rushing_df['AvgRYPG'] * 0.1
rushing_df['TD Pt Est'] = rushing_df['TDpGame'] * 6
rushing_df['Total'] = rushing_df['Yd Pt Est'] + rushing_df['TD Pt Est']
rushing_df['Opp'] = rushing_df['Team'].apply(lambda x: find_name(x))
rushing_df.sort_values(by=['Total'],inplace=True)
rushing_df['Scale'] = scale
rushing_df.drop(['AvgRYPG','Total','TDpGame','Yd Pt Est','TD Pt Est','Team'],axis=1,inplace=True)
#print(rushing_df.head())
#1pt per 10yds or .1 pt per yard
#rush TD is 6 pts


dk_pool_rb = dk_pool[dk_pool['Position'] == 'RB']
dk_pool_rb.drop(['Name + ID', 'ID'],axis=1,inplace=True)
dk_pool_rb['Opp'] = dk_pool_rb.apply(lambda x: find_opponent(x),axis=1)
dk_merge_rb = pd.merge(dk_pool_rb,rushing_df, how='left', on='Opp')
dk_merge_rb['TOT'] = dk_merge_rb['AvgPointsPerGame'] + dk_merge_rb['Scale']
dk_merge_rb = dk_merge_rb[dk_merge_rb['Salary'] > 4000]
dk_merge_rb.drop(['Game Info', 'TeamAbbrev', 'Roster Position','AvgPointsPerGame','Opp','Scale'],axis=1,inplace=True)
#print(dk_merge.info())
#print(dk_merge_rb)


## WR DATA
receiving_df = nfl_receiving_defense[0]
receiving_df['AvgRYPG'] = receiving_df['Yds'] / 16
receiving_df['AvgRecPG'] = receiving_df['Rec'] / 16
receiving_df['TD_PG'] = receiving_df['TD'] / 16
receiving_df['Yd Pt Est'] = receiving_df['AvgRYPG'] * 0.1
receiving_df['TD Pt Est'] = receiving_df['TD_PG'] * 6
receiving_df['Rec Pt Est'] = receiving_df['AvgRecPG']
receiving_df['Opp'] = receiving_df['Team'].apply(lambda x: find_name(x))
receiving_df['Total'] = receiving_df['Yd Pt Est'] + receiving_df['TD Pt Est'] + receiving_df['Rec Pt Est']
receiving_df.sort_values(by=['Total'],inplace=True)
receiving_df['Scale'] = scale
receiving_df.drop(['Rec','Team','Yd Pt Est','Total','TD Pt Est','Rec Pt Est','AvgRYPG','AvgRecPG','TD_PG','TD','Yds', 'Yds/Rec','20+','40+','Lng','Rec 1st','Rec 1st%','Rec FUM','PDef'],axis=1,inplace=True)
#1pt per 10yds or .1 pt per yard
#rec TD is 6 pts
#rec is 1 pt

dk_pool_wr = dk_pool[dk_pool['Position'] == 'WR']
dk_pool_wr.drop(['Name + ID', 'ID'],axis=1,inplace=True)
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
dk_pool_te.drop(['Name + ID', 'ID'],axis=1,inplace=True)
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
dk_merge_def['INT Pts'] = (dk_merge_def['INT'] * 2) / 16
dk_merge_def['Sack Pts'] = dk_merge_def['Sck'] / 16
dk_merge_def['Fum Pts'] = (dk_merge_def['Rush FUM'] * 2) / 16
dk_merge_def['Pts Scored'] = dk_merge_def['Tot TD'].apply(lambda x: points_for(x))
dk_merge_def['Total'] = dk_merge_def['INT Pts'] + dk_merge_def['Sack Pts'] + dk_merge_def['Fum Pts'] + dk_merge_def['Pts Scored']
dk_merge_def.sort_values(by=['Total'],ascending=True,inplace=True)
dk_merge_def['Scale'] = d_scale
dk_merge_def.drop(['INT','Sck','Rush FUM','Tot TD','Team','INT Pts','Sack Pts','Total','Fum Pts','Pts Scored'],axis=1,inplace=True)

dk_pool_def = dk_pool[dk_pool['Position'] == 'DST']
dk_pool_def.drop(['Name + ID', 'ID'],axis=1,inplace=True)
dk_pool_def['Opp'] = dk_pool_def.apply(lambda x: find_opponent(x),axis=1)
dk_pool_def = pd.merge(dk_pool_def, dk_merge_def, how='left',on='Opp')
dk_pool_def['TOT'] = dk_pool_def['AvgPointsPerGame'] + dk_pool_def['Scale']
dk_pool_def.drop(['Game Info','TeamAbbrev','Roster Position','AvgPointsPerGame','Scale','Opp'],axis=1,inplace=True)
#print(dk_pool_def.head())

## FLEX DATA
dk_merge_flex = pd.concat([dk_merge_rb,dk_merge_wr,dk_merge_te],ignore_index=True)
dk_merge_flex.sort_values(by=['TOT'],ascending=False,inplace=True)
#print(dk_merge_flex)


## LINE UP
# 1 QB, 2 RB, 3 WR, 1 TE, 1 FLEX, 1 DST

i = 0
k = 0
maxIter = 0
topTierLineup = pd.DataFrame(columns=['QB','RB','RB','WR','WR','WR','TE','FLEX','DST','TOT'])

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
    if currentIter > 190 and constraint(lineup) and duplicates(getNames(lineup)) == False:
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

print(maxIter)
print(getNames(maxLineup))
topTierLineup.to_csv('NFL_DK_LineUps.csv', index = False)

