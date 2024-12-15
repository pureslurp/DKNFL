"""NFL Props Scraper and DFS Points Calculator"""

# Standard library imports
import argparse
import sys
import time
from collections import defaultdict
from typing import Dict, List, Tuple

# Third-party imports
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Constants
STAT_LIST = [
    "Passing Yards", "Rushing Yards", "Receiving Yards", "Receptions",
    "Touchdowns", "Passing TDS", "Interceptions"
]

STAT_DICT = {
    "Passing Yards": "Pass Yds DFS",
    "Rushing Yards": "Rush Yds DFS",
    "Receiving Yards": "Rec Yds DFS",
    "Receptions": "Rec DFS",
    "Touchdowns": "TDs DFS",
    "Passing TDS": "Pass TDs DFS",
    "Interceptions": "Int DFS"
}

class DFSPointsCalculator:
    """Calculate DFS points based on different statistics"""
    
    @staticmethod
    def passing_yards(yards: float) -> float:
        """Calculate DFS points for passing yards"""
        bonus = 3 if yards >= 300 else 0
        return (yards * 0.04) + bonus
    
    @staticmethod
    def rushing_yards(yards: float) -> float:
        """Calculate DFS points for rushing yards"""
        bonus = 3 if yards >= 100 else 0
        return (yards * 0.1) + bonus
    
    @staticmethod
    def receiving_yards(yards: float) -> float:
        """Calculate DFS points for receiving yards"""
        return yards * 0.1
    
    @staticmethod
    def receptions(count: float) -> float:
        """Calculate DFS points for receptions"""
        return count
    
    @staticmethod
    def touchdowns(odds: float) -> float:
        """
        Calculate DFS points for touchdowns using a probability-based model
        
        Args:
            odds: American odds for scoring at least one touchdown
            
        Returns:
            float: Expected DFS points from touchdowns
        """
        try:
            # Convert American odds to probability of scoring at least one TD
            if odds < 0:
                prob_1_td = abs(odds) / (abs(odds) + 100)
            else:
                prob_1_td = 100 / (odds + 100)
                
            # Calculate probability of multiple TDs using geometric distribution
            # P(2|1) = P(1) * 0.25  # Assuming 25% chance of another TD if you score one
            # P(3|2) = P(2) * 0.15  # Assuming 15% chance of third TD if you score two
            # P(4|3) = P(3) * 0.10  # Assuming 10% chance of fourth TD if you score three
            
            prob_2_td = prob_1_td * 0.25
            prob_3_td = prob_2_td * 0.15
            prob_4_td = prob_3_td * 0.10
            
            # Calculate expected touchdown points
            expected_points = (
                (prob_1_td * 6) +           # Points from 1 TD
                (prob_2_td * 6) +           # Points from 2nd TD
                (prob_3_td * 6) +           # Points from 3rd TD
                (prob_4_td * 6)             # Points from 4th TD
            )
            
            return expected_points
            
        except (ZeroDivisionError, TypeError):
            return 0
    
    @staticmethod
    def passing_tds(count: float) -> float:
        """Calculate DFS points for passing touchdowns"""
        return count * 4
    
    @staticmethod
    def interceptions(odds: float) -> float:
        """Calculate DFS points for interceptions"""
        if 0 < odds < 3:
            return odds * -1
        try:
            if odds < 0:
                return (odds/-110) * -1
            return (100/odds) * -1
        except (ZeroDivisionError, TypeError):
            return 0

class PropsScraper:
    """Scrape NFL props data from ScoresAndOdds"""
    # Class constants
    DEFAULT_ODDS = -110
    DEFAULT_LINE = 100
    DEFAULT_VALUE = 0

    def __init__(self, week: int):
        self.week = week
        self.driver = None
        self.data_dict = defaultdict(dict)
    
    def setup_driver(self):
        """Initialize Selenium WebDriver"""
        self.driver = webdriver.Firefox()
        self.driver.get('https://www.scoresandodds.com/nfl/props')
        self.driver.implicitly_wait(120)

    @staticmethod
    def convert_odds(odds_text: str) -> float:
        """Convert odds text to numeric value"""
        if odds_text.lower() == 'even':
            return PropsScraper.DEFAULT_ODDS
        try:
            return float(odds_text)
        except (ValueError, TypeError):
            print(f"Invalid odds value: {odds_text}, using default {PropsScraper.DEFAULT_ODDS}")
            return PropsScraper.DEFAULT_ODDS

    def parse_odds_row(self, html) -> Tuple[str, float]:
        """Parse a single row of odds data"""
        try:
            # Parse name
            name = html.find("div", class_="props-name").text.strip()
            name = ' '.join(name.split()[:2])
            
            # Parse line and odds
            try:
                line = html.find("span", class_="data-moneyline").text.strip()
            except (AttributeError, TypeError):
                print(f"No line found for {name}")
                return name, 0
                
            try:
                line_odds_text = html.find("small", class_="data-odds best").text.strip()
                line_odds = self.convert_odds(line_odds_text)
            except (AttributeError, TypeError):
                print(f"No odds found for {name}, using default -110")
                line_odds = -110
            
            # Parse line value
            try:
                if isinstance(line, str) and line[0] in ['o', 'u']:
                    line = float(line[1:])
                elif line == 'even':
                    line = 100
                else:
                    line = float(line)
            except ValueError:
                print(f"Invalid line value for {name}: {line}, using 100")
                line = 100
                    
            # Calculate final line
            try:
                if line_odds < 0:
                    final_line = (line_odds/-110) * line
                else:
                    final_line = (100/line_odds) * line
                return name, final_line
            except ZeroDivisionError:
                print(f"Invalid odds calculation for {name}: line={line}, odds={line_odds}")
                return name, 0
                
        except Exception as e:
            print(f"Error parsing odds for {name if 'name' in locals() else 'unknown'}: {e}")
            return name if 'name' in locals() else "unknown", 0

    
    def scrape_props(self):
        """Scrape all props data"""
        try:
            for i in range(len(STAT_LIST) - 1):
                # Get current page data
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                odds_list = soup.find_all('ul', class_="table-list")[0].find_all("li")
                
                # Parse odds data
                for entry in odds_list:
                    name, line = self.parse_odds_row(entry)
                    self.data_dict[STAT_LIST[i]][name] = line
                
                # Navigate to next stat
                self._navigate_to_next_stat(i)
                
            # Get final stat page
            self._process_final_stat()
            
        finally:
            self.cleanup()
    
    def _navigate_to_next_stat(self, index: int):
        """Navigate to the next stat page"""
        current_stat = STAT_LIST[index]
        next_stat = STAT_LIST[index + 1]
        
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f"//span[contains(text(), '{current_stat}')]"))
        ).click()
        
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f"//span[contains(text(), '{next_stat}')]"))
        ).click()
        
        time.sleep(1)
    
    def _process_final_stat(self):
        """Process the final stat page"""
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        odds_list = soup.find_all('ul', class_="table-list")[0].find_all("li")
        
        for entry in odds_list:
            name, line = self.parse_odds_row(entry)
            self.data_dict[STAT_LIST[-1]][name] = line
    
    def cleanup(self):
        """Close browser and cleanup"""
        if self.driver:
            self.driver.quit()
    
    def create_dataframe(self) -> pd.DataFrame:
        """Convert scraped data to DataFrame"""
        # Get all unique names
        all_names = set()
        for stat in STAT_LIST:
            all_names.update(self.data_dict[stat].keys())
        
        # Create DataFrame
        df = pd.DataFrame({"Name": list(all_names)})
        
        # Add stats columns
        for stat in STAT_LIST:
            stat_df = pd.DataFrame(self.data_dict[stat].items(), columns=["Name", stat])
            df = pd.merge(df, stat_df, how='left', on='Name')
        
        return df

def main():
    """Main function"""
    # Parse arguments
    parser = argparse.ArgumentParser(description='Scrape NFL props and calculate DFS points')
    parser.add_argument("week", type=int, help="NFL Week")
    args = parser.parse_args()
    
    # Scrape props
    scraper = PropsScraper(args.week)
    try:
        scraper.setup_driver()
        scraper.scrape_props()
        master_df = scraper.create_dataframe()
        
        # Calculate DFS points
        calculator = DFSPointsCalculator()
        for stat, dfs_col in STAT_DICT.items():
            master_df[dfs_col] = master_df[stat].apply(
                getattr(calculator, stat.lower().replace(' ', '_'))
            )
        
        # Calculate total
        master_df["DFS Total"] = master_df[list(STAT_DICT.values())].sum(axis=1)
        
        # Save results
        output_path = f"2024/WEEK{args.week}/NFL_Proj_DFS.csv"
        master_df.to_csv(output_path, index=False)
        print(f"Successfully wrote file: {output_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()