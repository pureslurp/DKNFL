# Quick Start
There are 3 scripts needed to run predictions, in order. Each script requires the argument of "Week"
1. parse_odds.py
2. nfl_dfs.py
3. dfs_stack.py

Example of running full prediction for Week 12
1. Create a folder in 2023 for the current week,"2023/WEEK12"
2. `python3 parse_odds.py 12`
3. `python3 nfl_dfs.py 12`
4. Download DKSalaries from DraftKings and put them in the folder created with the naming convention "DKSalaries-Week12
5. `python3 dfs_stack.py 12`

The last script will output 24 lineups ranked from best to worst, dk_lineups_week12.cvs.

# Predictions

## parse_odds.py

#### inputs
- Folder created in 2023 for the week to be predicted, e.g. WEEK12

#### description
This script will pull live player props at the time of execution, for best results it is recommended to run this within 90 minutes of kick-off
This script takes 1 argument: the week

#### arguments
1 required argument: the week as an int, e.g. 12

#### example
Example for Week 12 Prediction
`python3 parse_odds.py 12`

#### output
- NFL_Proj_{WEEK}.csv

## nfl_dfs.py

#### inputs
- NFL_Proj_{WEEK}.csv from parse_odds.py

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
