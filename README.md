# DKNFL - DraftKings NFL DFS Lineup Optimizer

## Overview
This repository contains a comprehensive suite of tools for predicting and optimizing DraftKings NFL contest lineups based on player prop data, historical performance, and advanced analytics.

## Quick Start
To generate predictions for a specific week, follow these steps in order:

1. **Create week folder**: Create a folder in `2024/` for the current week (e.g., `2024/WEEK12`)
2. **Parse odds**: Run `python3 parse_odds.py 12` to fetch live player props
3. **Download salaries**: Download DKSalaries from DraftKings and save as `DKSalaries-Week12.csv` in the week folder
4. **Generate lineups**: Run `python3 dfs_stack.py 12` to create optimized lineups

The final script outputs 24 lineups ranked from best to worst in `dk_lineups_week12.csv`.

## Core Scripts

### 1. parse_odds.py
**Purpose**: Fetches live player prop data and converts it to DFS projections

**Prerequisites**:
- Firefox browser installed
- Internet connection for live odds

**Inputs**:
- Week number as command line argument
- Target folder in `2024/` directory

**Description**:
Pulls live player props at execution time. For best results, run within 90 minutes of kickoff. **Note**: This script overwrites existing data for past weeks with current live data.

**Usage**:
```bash
python3 parse_odds.py 12
```

**Output**:
- `NFL_Proj_DFS.csv` - Player projections for DFS

### 2. dfs_stack.py
**Purpose**: Creates optimized DraftKings lineups using QB-WR/TE stacks

**Prerequisites**:
- `parse_odds.py` must be run first
- `NFL_Proj_DFS.csv` from parse_odds.py
- `DKSalaries-Week{WEEK}.csv` from DraftKings

**Description**:
Generates 4 different stacks (2 based on highest total, 2 based on best value) and creates 24 optimized lineups with exposure management.

**Usage**:
```bash
# For predictions (default)
python3 dfs_stack.py 12

# For backtesting
python3 dfs_stack.py 12 backtest
```

**Output**:
- `dk_lineups_week{WEEK}.csv` - 24 ranked lineups

## Additional Tools

### 3. dfs_box_scores.py
**Purpose**: Processes actual game results for backtesting and analysis

**Description**:
Compares predicted lineups against actual player performance to evaluate prediction accuracy.

### 4. merge_scores.py
**Purpose**: Merges predicted scores with actual game results

**Description**:
Creates comprehensive datasets combining projections and actual performance for analysis.

### 5. dashboard.py
**Purpose**: Generates analysis dashboards and reports

**Description**:
Creates visualizations and summary statistics for lineup performance and player analysis.

### 6. league_analysis.py
**Purpose**: Analyzes league-wide trends and patterns

**Description**:
Provides insights into league performance, team matchups, and strategic considerations.

### 7. parse_odds.py (Detailed)
**Purpose**: Advanced odds parsing and market analysis

**Description**:
Enhanced version of the basic odds parser with additional market analysis capabilities.

## Utility Scripts

### utils.py
Contains helper functions, constants, and data structures used across the project:
- Team abbreviations and mappings
- Position definitions
- Common utility functions

### nfl_dfs.py
Basic NFL DFS utilities and helper functions.

## Project Structure

```
DKNFL/
├── 2024/                    # Current season data
│   ├── WEEK1/              # Week-specific folders
│   ├── WEEK2/
│   └── ...
├── parse_odds.py           # Live odds parser
├── dfs_stack.py            # Main lineup optimizer
├── dfs_box_scores.py       # Results processor
├── merge_scores.py         # Score merger
├── dashboard.py            # Analysis dashboard
├── league_analysis.py      # League analysis
├── utils.py                # Utility functions
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Requirements

Install dependencies:
```bash
pip install -r requirements.txt
```

## Workflow

1. **Weekly Setup**: Create week folder and download DraftKings salaries
2. **Data Collection**: Run parse_odds.py to get live projections
3. **Lineup Generation**: Run dfs_stack.py to create optimized lineups
4. **Analysis**: Use additional tools for backtesting and analysis
5. **Results Processing**: After games, use dfs_box_scores.py to evaluate performance

## Features

- **Live Data Integration**: Real-time player prop data
- **Advanced Stacking**: QB-WR/TE correlation optimization
- **Exposure Management**: Prevents over-exposure to individual players
- **Multiple Strategies**: Total-based and value-based approaches
- **Backtesting**: Historical performance analysis
- **Comprehensive Analysis**: Dashboard and reporting tools

## Notes

- Run parse_odds.py close to game time for most accurate projections
- The system generates 24 lineups with different strategies and exposures
- All scripts support both prediction and backtesting modes
- Historical data from 2022 and 2023 seasons is preserved for analysis

## Contributing

This project is designed for personal use in NFL DFS contests. Please ensure compliance with DraftKings terms of service and local gambling regulations.
