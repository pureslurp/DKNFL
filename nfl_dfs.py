#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Aug 28 19:03:29 2021

@author: seanraymor
"""
import pandas as pd
import numpy as np
pd.options.mode.chained_assignment = None  # default='warn'
import sys
import argparse

def points_to_dfs(key, data):
    match key:
        case "Passing Yards":
            if data >= 300:
                return (data * 0.04) + 3
            else:
                return data * .04
        case "Rushing Yards":
            if data >= 100:
                return (data * 0.1) + 3
            else:
                return data * 0.1
        case "Receiving Yards":
            return data * 0.1
        case "Receptions":
            return data
        case "Touchdowns":
            try:
                if data < 0:
                    return (data/-110) * 6
                else:
                    return (100/data) * 6
            except:
                return 0
        case "Passing TDS":
            return data * 4
        case "Interceptions":
            if data < 3 and data > 0:
                return data * -1
            else:
                if data < 0:
                    return (data/-110) * -1
                else:
                    return (100/data) * -1

def main(argv):
    argParser = argparse.ArgumentParser()
    argParser.add_argument("week", type=int, help="NFL Week")
    args = argParser.parse_args()
    WEEK = args.week
    nfl_stats = pd.read_csv(f"2024/WEEK{WEEK}/NFL_Proj_{WEEK}.csv")
    print(nfl_stats.head())

    stat_dict = {
        "Passing Yards" : "Pass Yds DFS",
        "Rushing Yards" : "Rush Yds DFS",
        "Receiving Yards" : "Rec Yds DFS",
        "Receptions" : "Rec DFS",
        "Touchdowns" : "TDs DFS",
        "Passing TDS" : "Pass TDs DFS",
        "Interceptions" : "Int DFS"
        }

    for key, value in stat_dict.items():
        nfl_stats[value] = nfl_stats[key].apply(lambda x: points_to_dfs(key, x))

    nfl_stats["DFS Total"] = nfl_stats[list(stat_dict.values())].sum(axis=1)
    nfl_stats.drop(columns=list(stat_dict.keys()), inplace=True)
    nfl_stats.drop(columns=list(stat_dict.values()), inplace=True)


    nfl_stats.to_csv(f"2024/WEEK{WEEK}/NFL_Proj_DFS_WEEK{WEEK}.csv")

    print(nfl_stats.head())

if __name__ == "__main__":
    main(sys.argv[1:])