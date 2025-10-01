# Position vs Team Analysis Script

This script analyzes how each position performs against specific NFL teams by calculating the average points given up by each team to each position.

## Usage

```bash
python3 position_vs_team_analysis.py --week <week_number>
```

### Examples

```bash
# Analyze weeks 1-2 and output to WEEK3 folder
python3 position_vs_team_analysis.py --week 3

# Analyze weeks 1-3 and output to WEEK4 folder  
python3 position_vs_team_analysis.py --week 4
```

## Output

The script generates a CSV file in the format:
- **File location**: `2025/WEEK{X}/position_vs_team_week{X}.csv`
- **Columns**: `Team`, `DST`, `QB`, `RB`, `TE`, `WR`
- **Rows**: Each NFL team
- **Values**: Average points given up by that team to each position

## How It Works

1. **Data Sources**:
   - `DKSalaries*.csv` files: Contains player information, positions, teams, and game matchups
   - `box_score_debug.csv` files: Contains actual points scored by each player

2. **Process**:
   - For each week being analyzed, the script:
     - Loads player data from DKSalaries file
     - Loads points data from box_score_debug file
     - Matches players to their opponents using game info
     - Groups points by opponent team and position
   - Calculates averages across all analyzed weeks
   - Outputs results to CSV

3. **Example Output**:
   ```
   Team,DST,QB,RB,TE,WR
   ARI,0.0,17.68,8.12,7.8,10.32
   ATL,0.0,11.37,7.54,1.83,6.22
   BAL,0.0,8.26,10.47,8.0,5.82
   ```

## Requirements

- Python 3.x
- pandas
- Data files in the expected format in `2025/WEEK{X}/` folders

## Notes

- Week 1 is invalid (need at least 2 weeks of data)
- The script processes all weeks from 1 to (week-1)
- Missing player data will show warnings but won't stop execution
- Results are rounded to 2 decimal places
