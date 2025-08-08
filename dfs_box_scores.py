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
    WebDriverException
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
            self.driver.get(f"{self.base_url}/games/index.html")
            
            # Wait for content to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "statistics"))
            )
            
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            games_table = soup.find_all('table', class_='statistics')[self.week - 1]
            
            return [
                game.find("a").get('href') 
                for game in games_table.find_all('tr') 
                if game.find("a")
            ]
            
        except Exception as e:
            print(f"Error getting game links: {e}")
            return []
            
    def parse_stats_table(self, table, stat_type: str) -> pd.DataFrame:
        """Parse a single stats table into a DataFrame"""
        try:
            header = table.find("thead")
            body = table.find("tbody")
            
            if not header or not body:
                return pd.DataFrame(columns=self.stat_columns[stat_type])
            
            # Get raw column names
            columns = [th.text for th in header.find_all("th")]
            
            # Define column mappings for each stat type
            column_maps = {
                'passing': {'Yds': 'pass_Yds', 'TD': 'pass_TD', 'Int': 'pass_INT'},
                'rushing': {'Yds': 'rush_Yds', 'TD': 'rush_TD'},
                'receiving': {'Rec': 'rec_Rec', 'Yds': 'rec_Yds', 'TD': 'rec_TD'}
            }
            
            rows = []
            for row in body.find_all("tr"):
                values = [td.text for td in row.find_all("td")]
                row_dict = dict(zip(columns, values))
                
                # Clean player name
                row_dict['player'] = PlayerNameCleaner.clean_name(row_dict.get(columns[0], ''))
                
                # Map column names to our expected format
                mapped_dict = {'player': row_dict['player']}
                for old_col, new_col in column_maps[stat_type].items():
                    if old_col in row_dict:
                        mapped_dict[new_col] = row_dict[old_col]
                
                rows.append(mapped_dict)
            
            df = pd.DataFrame(rows)
            print(f"Parsed {stat_type} stats with columns: {df.columns.tolist()}")
            return df
            
        except Exception as e:
            print(f"Error parsing {stat_type} stats table: {e}")
            return pd.DataFrame(columns=self.stat_columns[stat_type])
            
    def process_game(self, game_url: str) -> Dict[str, pd.DataFrame]:
        """Process a single game's box score"""
        try:
            self.driver.get(f"{self.base_url}{game_url}")
            
            # Add explicit wait for stats div
            self.wait.until(
                EC.presence_of_element_located((By.ID, "divBox_stats"))
            )
            
            # Add small delay to ensure all content is loaded
            time.sleep(2)
            
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            stats_div = soup.find('div', {"id": "divBox_stats"})
            if not stats_div:
                return {}
                
            tables = stats_div.find_all("table")
            stats = {
                'passing': pd.concat([self.parse_stats_table(t, 'passing') for t in tables[:2]]),
                'rushing': pd.concat([self.parse_stats_table(t, 'rushing') for t in tables[2:4]]),
                'receiving': pd.concat([self.parse_stats_table(t, 'receiving') for t in tables[4:6]])
            }
            
            return stats
            
        except Exception as e:
            print(f"Error processing game {game_url}: {e}")
            return {}
            
    def process_all_games(self) -> pd.DataFrame:
        """Process all games and combine stats with retry logic"""
        try:
            game_links = self.get_game_links()
            print(f"Found {len(game_links)} games to process")
            
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
    parser.add_argument("week", type=int, help="NFL Week")
    args = parser.parse_args()
    
    try:
        scraper = FootballDBScraper(args.week)
        driver = scraper.setup_driver()
        
        master_df = scraper.process_all_games()
        
        # Save results
        output_path = f"2024/WEEK{args.week}/box_score_debug.csv"
        master_df.to_csv(output_path, index=False)
        print(f"\nSuccessfully wrote box scores to {output_path}")
        
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
        
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main(sys.argv[1:])