# ESPN Fantasy Projections Scraper

This script scrapes ESPN fantasy football projections for DFS (Daily Fantasy Sports) lineup optimization. It extracts bust, projected, and boom values for each player by clicking on player names to open popup modals.

## Features

- **Manual Login Support**: Interactive login process (no credentials storage required)
- **Chrome WebDriver**: Uses Chrome with automatic WebDriver management
- **Dual Analysis Modes**: 
  - **Fine Mode**: Detailed extraction with popup clicking for boom/bust data
  - **Coarse Mode**: Simplified extraction from table rows (projected points only)
- **Week-Based Organization**: Automatically organizes data into weekly folders
- **Comprehensive Data**: Extracts bust/boom scores, percentages, and projected points
- **Incremental Scraping**: Resumes from where it left off to avoid duplicate work
- **CSV Output**: Saves all data to CSV with immediate append functionality
- **Robust Error Handling**: Detailed logging and fallback mechanisms

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Chrome Browser

The script uses Chrome WebDriver with automatic management. Make sure you have Chrome browser installed on your system.

### 3. ESPN Account Access

You'll need a valid ESPN account to access fantasy projections. The script will prompt you to log in manually when it starts.

**Note**: No credentials storage is required - you'll log in interactively each time the script runs.

## Usage

### Week-Based Usage (Recommended)

```bash
python espn_fantasy_scraper.py --week 1
```

This will:
1. Create a `2025/WEEK1/` folder
2. Open Chrome browser for manual login
3. Navigate to the fantasy players page
4. Scrape all player projections
5. Save results to `2025/WEEK1/espn_fantasy_projections.csv`

### Analysis Mode Options

```bash
# Fine mode (default) - includes boom/bust data from popups
python espn_fantasy_scraper.py --week 1 --mode fine

# Coarse mode - projected points only, much faster
python espn_fantasy_scraper.py --week 1 --mode coarse
```

### Advanced Usage

```bash
# Custom output filename
python espn_fantasy_scraper.py --week 1 --output custom_projections.csv

# Limit to specific number of pages
python espn_fantasy_scraper.py --week 1 --max-pages 5

# Combine options
python espn_fantasy_scraper.py --week 1 --mode coarse --max-pages 3 --output quick_scan.csv
```

## Output Format

The CSV file contains the following columns:

### Core Player Information:
- `player_name`: Player's full name
- `team`: Team abbreviation (e.g., "Cin", "Cle")  
- `position`: Position abbreviation (e.g., "WR", "RB", "QB", "D/ST")
- `opponent`: Opponent team abbreviation

### Projection Data:
- `projected_points`: Projected fantasy points from main table

### Detailed Analysis (Fine Mode Only):
- `bust_score`: Points in bust scenario
- `projected_score`: Detailed projected score from popup
- `boom_score`: Points in boom scenario
- `bust_percentage`: Probability of bust performance (%)
- `boom_percentage`: Probability of boom performance (%)

### Data Availability by Mode:
- **Fine Mode**: All columns populated with detailed boom/bust analysis
- **Coarse Mode**: Only core info and `projected_points`; other fields set to '0'

## Example Output

### Fine Mode:
```csv
player_name,team,position,opponent,projected_points,bust_score,projected_score,boom_score,bust_percentage,boom_percentage
Ja'Marr Chase,Cin,WR,@Cle,19.7,12.3,16.7,24.8,29,29
```

### Coarse Mode:
```csv
player_name,team,position,opponent,projected_points,bust_score,projected_score,boom_score,bust_percentage,boom_percentage
Ja'Marr Chase,Cin,WR,@Cle,19.7,0,0,0,0,0
```

## Troubleshooting

### Common Issues

1. **Manual Login Required**: The script will pause and ask you to complete login manually
   - Make sure you can see the ESPN players table before pressing Enter
   - If login fails, refresh the page and try again

2. **Chrome WebDriver Error**: 
   - Ensure Chrome browser is installed and up to date
   - The script automatically downloads the correct ChromeDriver version
   - If issues persist, try updating Chrome browser

3. **Popup Not Found (Fine Mode)**:
   - The site structure may have changed; check the debug output
   - Try using coarse mode (`--mode coarse`) as a fallback
   - Fine mode requires JavaScript popups to be enabled

4. **Rate Limiting**: 
   - The script includes delays to avoid overwhelming the server
   - Fine mode is slower due to popup interactions
   - Use coarse mode for faster scraping when boom/bust data isn't needed

5. **Pagination Issues**:
   - If pagination stops working, the script will continue with available data
   - Use `--max-pages` to limit scraping to specific number of pages

### Debug Mode

To see the browser in action (not headless), uncomment this line in `espn_fantasy_scraper.py`:

```python
# options.add_argument("--headless")
```

### Performance Tips

- **Use Coarse Mode**: Much faster when you only need projected points
- **Incremental Scraping**: Script resumes from where it left off
- **Limit Pages**: Use `--max-pages` for testing or partial scraping
- **Monitor Progress**: Script shows detailed progress and player summaries

## File Structure

The scraper automatically creates a weekly folder structure:

```
2025/
├── WEEK1/
│   └── espn_fantasy_projections.csv
├── WEEK2/
│   └── espn_fantasy_projections.csv
└── ...
```

This structure integrates seamlessly with the Advanced Lineup Generator which looks for data in these weekly folders.

## Integration with DFS Optimizer

The output CSV can be used directly with the Advanced Lineup Generator:

```bash
# First, scrape projections for the week
python espn_fantasy_scraper.py --week 1 --mode fine

# Then generate lineups using the scraped data
python advanced_lineup_generator.py --week 1 --num-lineups 20
```

The bust/projected/boom values provide comprehensive projection data for:

- **Risk Assessment**: Compare bust vs boom scenarios
- **Multiple Optimization Strategies**: Use projected, risk-adjusted, or boom optimization
- **Monte Carlo Simulations**: Leverage probability distributions
- **Value-Based Lineup Construction**: Identify high-upside plays

## Security Notes

- **No Credential Storage**: Manual login eliminates the need to store credentials
- **Session-Based**: Each run requires fresh authentication
- **Browser Security**: Uses standard Chrome security features
- **No Data Transmission**: Scraped data stays on your local machine

## Future Enhancements

- **Support for Different Projection Sources**: Additional fantasy sites
- **Batch Processing**: Multi-week scraping in single run
- **Enhanced Data Quality**: Injury status and snap count integration
- **Real-Time Updates**: Live projection monitoring during games
- **Automated Scheduling**: Cron job integration for regular updates
- **Advanced Analytics**: Weather impact and matchup analysis
