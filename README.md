# Quick Start
There are 3 scripts needed to run predictions, in order. Each script requires the argument of "Week"
1. parse_odds.py
2. nfl_dfs.py
3. dfs_stack.py

Example of running full prediction for Week 12
1. Create a folder in 2023 for the current week,"2023/WEEK12"
2. run `python3 parse_odds.py 12` in the target location
3. run `python3 nfl_dfs.py 12` in the target location
4. Download DKSalaries from DraftKings and put them in the folder created with the naming convention "DKSalaries-Week12
5. run `python3 dfs_stack.py 12` in the target location

The last script will output 24 lineups ranked from best to worst, dk_lineups_week12.cvs.

# Predictions

## parse_odds.py

#### pre-req
- Firefox installed

#### inputs
- Folder created in 2023 for the week to be predicted, e.g. WEEK12

#### description
This script will pull live player props at the time of execution, for best results it is recommended to run this within 90 minutes of kick-off. **Note** -- Since the script pulls live odds, you can't pull player prop data from a past week. If you try to pass a past week, it will overwrite that weeks data with the live player prop data from the time at which you ran the script.

#### arguments
1 required argument: the week as an int, e.g. 12

#### example
Example for Week 12 Prediction
`python3 parse_odds.py 12`

#### output
- NFL_Proj_{WEEK}.csv

## nfl_dfs.py

#### pre-req
- parse_odds.py has already been ran

#### inputs
- NFL_Proj_{WEEK}.csv

#### description
This script will turn the player prop data output from the parse_odds.py script into dfs totals.

#### arguments
1 required argument: the week as an int, e.g. 12

#### example
Example for Week 12 Prediction
`python3 nfl_dfs.py 12`

### output
- NFL_Proj_DFS_WEEK{WEEK}.csv

## dfs_stack.py

#### pre-req
- nfl_dfs.py has already been ran

#### inputs
- NFL_Proj_DFS_WEEK{WEEK}.csv from nfl_dfs.py
- DKSalaries csv from DraftKings in the WEEK{WEEK} folder labeled DKSalaries-WEEK{WEEK}, e.g. WEEK12/DKSalaries-WEEK12

#### description
This script will take the data from nfl_dfs.py and use it to create 4 stacks, 2 based on overall highest total and 2 based on overall value

#### arguments
1 required argument, 1 optional: 
- required: the week as an int, e.g. 12
- optional: "forward" (default) to predict, and "backtest" to backtest

#### example
Example for Week 12 Prediction
`python3 dfs_stack.py 12`

#### output
- dk_lineups_week{WEEK}.csv


# Backtest
_todo_

1. dfs_box_scores.py
2. dfs_stack.py
