"""NFL Box Score Scraper for DFS Scoring"""

import argparse
import sys
from typing import Dict, List, Optional
import pandas as pd
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from dfs_stack import fix_name
import time
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    WebDriverException,
    NoSuchElementException
)

class DKScoring:
    """Calculate DraftKings fantasy points for different stat categories"""
    
    @staticmethod
    def passing_yards(yards: int) -> float:
        """0.04 points per yard, bonus 3 points at 300"""
        bonus = 3 if yards >= 300 else 0
        return (yards * 0.04) + bonus
    
    @staticmethod
    def passing_td(tds: int) -> float:
        """4 points per passing TD"""
        return tds * 4
    
    @staticmethod
    def interceptions(ints: int) -> float:
        """-1 point per interception"""
        return ints * -1
    
    @staticmethod
    def rushing_yards(yards: int) -> float:
        """0.1 points per yard, bonus 3 points at 100"""
        bonus = 3 if yards >= 100 else 0
        return (yards * 0.1) + bonus
    
    @staticmethod
    def rushing_td(tds: int) -> float:
        """6 points per rushing TD"""
        return tds * 6
    
    @staticmethod
    def receptions(recs: int) -> float:
        """1 point per reception"""
        return recs
    
    @staticmethod
    def receiving_yards(yards: int) -> float:
        """0.1 points per yard, bonus 3 points at 100"""
        bonus = 3 if yards >= 100 else 0
        return (yards * 0.1) + bonus
    
    receiving_td = rushing_td  # Same scoring for receiving TDs

class PlayerNameCleaner:
    """Clean and standardize player names"""
    
    @staticmethod
    def clean_name(name: str) -> str:
        """Clean player name from raw format"""
        if "." not in name:
            return name
            
        parts = name.split(".")
        
        # Handle special cases
        if parts[0] == "Amon-Ra":
            return "Amon-Ra St. Brown"
        elif parts[0] == "Equanimeous":
            return "Equanimeous St. Brown"
            
        # Handle standard cases
        if len(parts) > 2:
            # Join initials and last name
            initials = parts[:-1]
            last_name = parts[-1][:-1]  # Remove trailing character
            return f'{".".join(initials)}. {last_name}'.strip()
        else:
            return parts[0][:-1]  # Remove trailing character

class FootballDBScraper:
    """Scraper for FootballDB box scores"""
    
    def __init__(self, week: int):
        self.week = week
        self.base_url = "https://www.footballdb.com"
        self.driver = None
        
        # Define expected columns for each stat type
        self.stat_columns = {
            'passing': ["player", "pass_Yds", "pass_TD", "pass_INT"],
            'rushing': ["player", "rush_Yds", "rush_TD"],
            'receiving': ["player", "rec_Rec", "rec_Yds", "rec_TD"]
        }
        
    def setup_driver(self) -> webdriver.Firefox:
        """Initialize Selenium WebDriver"""
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(10)  # Reduce from 120 to improve performance
        self.wait = WebDriverWait(self.driver, 10)
        return self.driver
        
    def get_game_links(self) -> List[str]:
        """Get all game URLs for the specified week"""
        try:
            print(f"Navigating to {self.base_url}/games/index.html")
            self.driver.get(f"{self.base_url}/games/index.html")
            
            # Wait for content to load with multiple possible selectors
            selectors_to_try = [
                (By.CLASS_NAME, "statistics"),
                (By.TAG_NAME, "table"),
                (By.CLASS_NAME, "games"),
                (By.ID, "games")
            ]
            
            content_found = False
            for selector_type, selector_value in selectors_to_try:
                try:
                    print(f"Trying to find element with {selector_type}: {selector_value}")
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    content_found = True
                    print(f"Found content with {selector_type}: {selector_value}")
                    break
                except TimeoutException:
                    print(f"Timeout waiting for {selector_type}: {selector_value}")
                    continue
            
            if not content_found:
                print("Could not find any expected content, proceeding anyway...")
            
            # Add delay to ensure page is fully loaded
            time.sleep(3)
            
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            print(f"Page title: {soup.title.string if soup.title else 'No title found'}")
            
            # Try multiple approaches to find games table
            games_table = None
            
            # Approach 1: Look for statistics class
            tables = soup.find_all('table', class_='statistics')
            if tables and len(tables) >= self.week:
                games_table = tables[self.week - 1]
                print(f"Found games table using statistics class (week {self.week})")
            
            # Approach 2: Look for any table with game links
            if not games_table:
                all_tables = soup.find_all('table')
                for i, table in enumerate(all_tables):
                    links = table.find_all('a', href=True)
                    if any('boxscore' in link.get('href', '') for link in links):
                        if i == self.week - 1:  # Assuming tables are in week order
                            games_table = table
                            print(f"Found games table at index {i}")
                            break
            
            # Approach 3: Look for any links containing boxscore
            if not games_table:
                all_links = soup.find_all('a', href=True)
                boxscore_links = [link for link in all_links if 'boxscore' in link.get('href', '')]
                if boxscore_links:
                    print(f"Found {len(boxscore_links)} boxscore links directly")
                    return [link.get('href') for link in boxscore_links]
            
            if not games_table:
                print("Could not find games table, trying to extract links from page...")
                # Last resort: look for any boxscore links on the page
                all_links = soup.find_all('a', href=True)
                boxscore_links = [link.get('href') for link in all_links if 'boxscore' in link.get('href', '')]
                return boxscore_links
            
            # Extract links from the found table
            links = []
            for row in games_table.find_all('tr'):
                link_elem = row.find("a")
                if link_elem and link_elem.get('href'):
                    links.append(link_elem.get('href'))
            
            print(f"Found {len(links)} game links")
            return links
            
        except Exception as e:
            print(f"Error getting game links: {e}")
            print("Trying alternative approach...")
            
            # Alternative: try to construct URLs manually for common patterns
            try:
                # Try to get the current year from the URL or page
                current_year = "2025"  # Default to 2024
                alternative_links = []
                
                # Common game patterns for week 4
                if self.week == 4:
                    # These are example URLs - we'd need to get the actual game URLs
                    print("Attempting to construct alternative URLs for Week 4...")
                    # This is a fallback - in practice we'd need the actual game URLs
                
                return alternative_links
            except Exception as e2:
                print(f"Alternative approach also failed: {e2}")
                return []
            
    def parse_stats_table(self, table, stat_type: str) -> pd.DataFrame:
        """Parse a single stats table into a DataFrame"""
        try:
            header = table.find("thead")
            body = table.find("tbody")
            
            if not header or not body:
                print(f"No header or body found for {stat_type} table")
                return pd.DataFrame(columns=self.stat_columns[stat_type])
            
            # Get raw column names
            columns = [th.text.strip() for th in header.find_all("th")]
            print(f"Found columns for {stat_type}: {columns}")
            
            # Define column mappings for each stat type based on actual HTML
            column_maps = {
                'passing': {
                    'Yds': 'pass_Yds', 
                    'TD': 'pass_TD', 
                    'Int': 'pass_INT',
                    'Att': 'pass_Att',
                    'Cmp': 'pass_Cmp'
                },
                'rushing': {
                    'Yds': 'rush_Yds', 
                    'TD': 'rush_TD',
                    'Att': 'rush_Att'
                },
                'receiving': {
                    'Rec': 'rec_Rec', 
                    'Yds': 'rec_Yds', 
                    'TD': 'rec_TD',
                    'Tar': 'rec_Tar'
                }
            }
            
            rows = []
            for row in body.find_all("tr"):
                # Skip TOTAL rows
                if 'TOTAL' in row.get_text():
                    continue
                    
                values = [td.text.strip() for td in row.find_all("td")]
                if len(values) >= len(columns):
                    row_dict = dict(zip(columns, values))
                    
                    # Extract player name from the first column
                    player_col = columns[0] if columns else 'Player'
                    player_name = row_dict.get(player_col, '')
                    
                    # Clean player name - handle the span structure from the HTML
                    if player_name:
                        # Remove any HTML tags that might be in the text
                        player_name = player_name.replace('\xa0', ' ')  # Replace non-breaking spaces
                        player_name = PlayerNameCleaner.clean_name(player_name)
                    
                    if not player_name or player_name == 'TOTAL':
                        continue
                    
                    # Map column names to our expected format
                    mapped_dict = {'player': player_name}
                    for old_col, new_col in column_maps[stat_type].items():
                        # Look for columns that contain the old_col text
                        for col in columns:
                            if old_col in col:
                                value = row_dict.get(col, '0')
                                # Clean the value (remove 't' from TD values, etc.)
                                if value.endswith('t'):
                                    value = value[:-1]
                                mapped_dict[new_col] = value
                                break
                    
                    rows.append(mapped_dict)
            
            df = pd.DataFrame(rows)
            print(f"Parsed {stat_type} stats with {len(df)} rows and columns: {df.columns.tolist()}")
            return df
            
        except Exception as e:
            print(f"Error parsing {stat_type} stats table: {e}")
            return pd.DataFrame(columns=self.stat_columns[stat_type])
            
    def process_game(self, game_url: str) -> Dict[str, pd.DataFrame]:
        """Process a single game's box score"""
        try:
            full_url = f"{self.base_url}{game_url}" if not game_url.startswith('http') else game_url
            print(f"Processing game: {full_url}")
            
            self.driver.get(full_url)
            
            # Wait longer for the page to fully load
            print("Waiting for page to load...")
            time.sleep(5)  # Initial wait
            
            # Try multiple approaches to find stats
            stats_div = None
            
            # Approach 1: Look for mobToggle_stats (the actual ID from the HTML)
            try:
                print("Waiting for mobToggle_stats element...")
                self.wait.until(
                    EC.presence_of_element_located((By.ID, "mobToggle_stats"))
                )
                # Additional wait after finding the element
                time.sleep(3)
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                stats_div = soup.find('div', {"id": "mobToggle_stats"})
                print("Found stats using mobToggle_stats ID")
                
                # Debug: Check what's actually in the stats div
                if stats_div:
                    print(f"Stats div found with {len(stats_div.find_all('h2'))} h2 headers")
                    print(f"Stats div found with {len(stats_div.find_all('table'))} tables")
                    print(f"Stats div found with {len(stats_div.find_all('div', class_='statsvisitor'))} statsvisitor divs")
                    print(f"Stats div found with {len(stats_div.find_all('div', class_='statshome'))} statshome divs")
                else:
                    print("Stats div not found in soup")
                    
            except TimeoutException:
                print("mobToggle_stats not found, trying alternative approaches...")
            
            # Approach 2: Look for divBox_stats (old approach)
            if not stats_div:
                try:
                    print("Waiting for divBox_stats element...")
                    self.wait.until(
                        EC.presence_of_element_located((By.ID, "divBox_stats"))
                    )
                    time.sleep(3)
                    soup = BeautifulSoup(self.driver.page_source, "html.parser")
                    stats_div = soup.find('div', {"id": "divBox_stats"})
                    print("Found stats using divBox_stats ID")
                except TimeoutException:
                    print("divBox_stats not found, trying alternative approaches...")
            
            # Approach 3: Look for any div with stats
            if not stats_div:
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                stats_divs = soup.find_all('div', class_=lambda x: x and 'stats' in x.lower())
                if stats_divs:
                    stats_div = stats_divs[0]
                    print("Found stats using class containing 'stats'")
            
            # Approach 4: Look for tables directly
            if not stats_div:
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                tables = soup.find_all("table")
                if tables:
                    print(f"Found {len(tables)} tables directly on page")
                    # Use the page itself as the stats container
                    stats_div = soup
            
            if not stats_div:
                print(f"No stats found for game {game_url}")
                # Debug: Let's see what's actually on the page
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                print(f"Page has {len(soup.find_all('div'))} divs")
                print(f"Page has {len(soup.find_all('table'))} tables")
                print(f"Page has {len(soup.find_all('h2'))} h2 headers")
                return {}
            
            # Process stats based on the actual HTML structure
            stats = {
                'passing': pd.DataFrame(columns=self.stat_columns['passing']),
                'rushing': pd.DataFrame(columns=self.stat_columns['rushing']),
                'receiving': pd.DataFrame(columns=self.stat_columns['receiving'])
            }
            
            # Look for h2 headers to identify sections
            h2_headers = stats_div.find_all('h2')
            print(f"Found {len(h2_headers)} h2 headers: {[h.text for h in h2_headers]}")
            
            # Process each section based on h2 headers
            for h2 in h2_headers:
                section_name = h2.text.strip().lower()
                print(f"Processing section: {section_name}")
                
                # Find all tables that follow this h2 until the next h2
                # Look for tables within statsvisitor and statshome divs
                section_tables = []
                next_element = h2.find_next_sibling()
                
                while next_element and next_element.name != 'h2':
                    if next_element.name == 'div':
                        div_classes = next_element.get('class', [])
                        if 'statsvisitor' in div_classes or 'statshome' in div_classes:
                            # Found a stats div, look for tables within it
                            tables_in_div = next_element.find_all('table')
                            section_tables.extend(tables_in_div)
                            print(f"Found {len(tables_in_div)} tables in {div_classes} div")
                    elif next_element.name == 'table':
                        # Direct table (fallback)
                        section_tables.append(next_element)
                        print("Found direct table")
                    
                    next_element = next_element.find_next_sibling()
                
                print(f"Found {len(section_tables)} total tables in {section_name} section")
                
                # Process tables based on section type
                if 'pass' in section_name:
                    for table in section_tables:
                        table_stats = self.parse_stats_table(table, 'passing')
                        if not table_stats.empty:
                            stats['passing'] = pd.concat([stats['passing'], table_stats], ignore_index=True)
                elif 'rush' in section_name:
                    for table in section_tables:
                        table_stats = self.parse_stats_table(table, 'rushing')
                        if not table_stats.empty:
                            stats['rushing'] = pd.concat([stats['rushing'], table_stats], ignore_index=True)
                elif 'receiv' in section_name:
                    for table in section_tables:
                        table_stats = self.parse_stats_table(table, 'receiving')
                        if not table_stats.empty:
                            stats['receiving'] = pd.concat([stats['receiving'], table_stats], ignore_index=True)
            
            # If no h2 headers found, try the old approach with table indices
            if not h2_headers:
                print("No h2 headers found, trying table index approach...")
                tables = stats_div.find_all("table")
                print(f"Found {len(tables)} tables in stats div")
                
                if len(tables) >= 6:
                    # Original approach with 6 tables
                    stats = {
                        'passing': pd.concat([self.parse_stats_table(t, 'passing') for t in tables[:2]]),
                        'rushing': pd.concat([self.parse_stats_table(t, 'rushing') for t in tables[2:4]]),
                        'receiving': pd.concat([self.parse_stats_table(t, 'receiving') for t in tables[4:6]])
                    }
                elif len(tables) > 0:
                    # Try to process whatever tables we have
                    for i, table in enumerate(tables):
                        table_text = table.get_text().lower()
                        if 'pass' in table_text or 'comp' in table_text or 'att' in table_text:
                            table_stats = self.parse_stats_table(table, 'passing')
                            if not table_stats.empty:
                                stats['passing'] = pd.concat([stats['passing'], table_stats], ignore_index=True)
                        elif 'rush' in table_text or 'car' in table_text:
                            table_stats = self.parse_stats_table(table, 'rushing')
                            if not table_stats.empty:
                                stats['rushing'] = pd.concat([stats['rushing'], table_stats], ignore_index=True)
                        elif 'rec' in table_text or 'catch' in table_text or 'target' in table_text:
                            table_stats = self.parse_stats_table(table, 'receiving')
                            if not table_stats.empty:
                                stats['receiving'] = pd.concat([stats['receiving'], table_stats], ignore_index=True)
            
            return stats
            
        except Exception as e:
            print(f"Error processing game {game_url}: {e}")
            return {}
            
    def process_all_games(self) -> pd.DataFrame:
        """Process all games and combine stats with retry logic"""
        try:
            game_links = self.get_game_links()
            print(f"Found {len(game_links)} games to process")
            
            if not game_links:
                print("No game links found!")
                return pd.DataFrame()
            
            all_stats = []
            for i, link in enumerate(game_links, 1):
                print(f"\nProcessing game {i}/{len(game_links)}")
                
                # Try up to 3 times to process each game
                for attempt in range(3):
                    try:
                        if attempt > 0:
                            print(f"Retry attempt {attempt + 1} for game {link}")
                            
                        game_stats = self.process_game(link)
                        if game_stats:
                            all_stats.append(game_stats)
                            break
                        
                        # If no stats but no error, just move on
                        if attempt == 0:
                            print(f"No stats found for game {link}, skipping...")
                            break
                            
                    except Exception as e:
                        print(f"Error on attempt {attempt + 1}: {e}")
                        if attempt == 2:  # Last attempt
                            print(f"Failed to process game {link} after 3 attempts, skipping...")
                        else:
                            print("Waiting 5 seconds before retry...")
                            time.sleep(5)
                            # Refresh the page before retry
                            try:
                                self.driver.refresh()
                            except:
                                pass
                
            if not all_stats:
                print("No valid games processed!")
                return pd.DataFrame()
                    
            # Combine all game stats
            print("\nCombining stats from all games...")
            combined_stats = {
                'passing': pd.concat([g['passing'] for g in all_stats if 'passing' in g and not g['passing'].empty]),
                'rushing': pd.concat([g['rushing'] for g in all_stats if 'rushing' in g and not g['rushing'].empty]),
                'receiving': pd.concat([g['receiving'] for g in all_stats if 'receiving' in g and not g['receiving'].empty])
            }
            
            # Merge all stats together
            master = pd.merge(combined_stats['passing'], combined_stats['rushing'], 
                            how='outer', on='player')
            master = pd.merge(master, combined_stats['receiving'], how='outer', on='player')
            
            # Clean up and calculate DFS points
            master = master.fillna(0)
            master = self.calculate_dfs_points(master)
            
            print(f"\nSuccessfully processed {len(all_stats)} games")
            return master
            
        except Exception as e:
            print(f"Error processing games: {e}")
            raise
            
    def calculate_dfs_points(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate DraftKings fantasy points"""
        scoring_map = {
            'pass_Yds': DKScoring.passing_yards,
            'pass_TD': DKScoring.passing_td,
            'pass_INT': DKScoring.interceptions,
            'rush_Yds': DKScoring.rushing_yards,
            'rush_TD': DKScoring.rushing_td,
            'rec_Rec': DKScoring.receptions,
            'rec_Yds': DKScoring.receiving_yards,
            'rec_TD': DKScoring.receiving_td
        }
        
        # Ensure all required columns exist
        for col in scoring_map.keys():
            if col not in df.columns:
                print(f"Missing column {col}, adding with zeros")
                df[col] = 0
        
        # Calculate points for each stat category
        print("\nCalculating DFS points for columns:", list(scoring_map.keys()))
        for col, scoring_func in scoring_map.items():
            try:
                # Convert to numeric, replacing any non-numeric values with 0
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                df[col] = df[col].astype(float).apply(scoring_func)
            except Exception as e:
                print(f"Error calculating points for {col}: {e}")
                df[col] = 0
        
        # Calculate total points
        point_columns = list(scoring_map.keys())
        df["DFS Total"] = df[point_columns].sum(axis=1)
        
        # Clean up final DataFrame
        df.rename(columns={"player": "Name"}, inplace=True)
        df["Name"] = df["Name"].apply(fix_name)
        
        print("\nFinal columns:", df.columns.tolist())
        return df

def main(argv):
    """Main function for NFL box score scraping and DFS points calculation"""
    parser = argparse.ArgumentParser(description='Scrape NFL box scores and calculate DFS points')
    parser.add_argument("weeks", type=int, nargs='+', help="NFL Week(s) - can specify multiple weeks")
    args = parser.parse_args()
    
    try:
        # Process each week
        for week in args.weeks:
            print(f"\n{'='*50}")
            print(f"Processing Week {week}")
            print(f"{'='*50}")
            
            scraper = FootballDBScraper(week)
            driver = scraper.setup_driver()
            
            try:
                master_df = scraper.process_all_games()
                
                # Save results
                output_path = f"2025/WEEK{week}/box_score_debug.csv"
                master_df.to_csv(output_path, index=False)
                print(f"\nSuccessfully wrote box scores to {output_path}")
                
            except Exception as e:
                print(f"\nError processing week {week}: {e}")
                continue
                
            finally:
                if driver:
                    driver.quit()
        
        print(f"\n{'='*50}")
        print(f"Completed processing {len(args.weeks)} week(s): {args.weeks}")
        print(f"{'='*50}")
        
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main(sys.argv[1:])