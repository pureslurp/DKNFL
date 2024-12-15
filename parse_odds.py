"""NFL Props Scraper and DFS Points Calculator"""

# Standard library imports
import argparse
import sys
import time
from collections import defaultdict
from typing import Dict, List, Tuple
import os

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

class PropsParser:
    """Handles the parsing of individual prop elements"""
    
    @staticmethod
    def parse_touchdown_odds(html) -> float:
        """
        Parse straight odds for touchdowns
        
        Args:
            html: BeautifulSoup element containing touchdown odds
            
        Returns:
            float: Touchdown odds or None if not found
        """
        try:
            # For touchdowns, odds are directly in data-moneyline
            odds_elem = html.find("span", class_="data-moneyline")
            if not odds_elem:
                print("  No data-moneyline element found")
                return None
                
            odds_text = odds_elem.text.strip()
            print(f"  Found touchdown odds text: {odds_text}")
            
            # Handle 'even' case if it exists
            if odds_text.lower() == 'even':
                return -110
                
            return float(odds_text)
            
        except Exception as e:
            print(f"  Error parsing touchdown odds: {e}")
            return None

    @staticmethod
    def parse_over_under(html) -> tuple[dict, dict]:
        """Parse over/under lines and odds"""
        try:
            odds_containers = html.find_all("div", class_="best-odds-container")
            over_data = under_data = None
            
            for container in odds_containers:
                line_elem = container.find("span", class_="data-moneyline")
                odds_elem = container.find("small", class_="data-odds best")
                
                if not line_elem or not odds_elem:
                    continue
                
                line_text = line_elem.text.strip()
                odds_text = odds_elem.text.strip()
                
                direction = line_text[0].lower()
                line = float(line_text[1:])
                odds = -110 if odds_text.lower() == 'even' else float(odds_text)
                
                if direction == 'o':
                    over_data = {'line': line, 'odds': odds}
                elif direction == 'u':
                    under_data = {'line': line, 'odds': odds}
            
            return over_data, under_data
        except Exception as e:
            print(f"Error parsing over/under: {e}")
            return None, None
        
    def calculate_projected_interceptions(self, over_data: dict, under_data: dict) -> float:
        """
        Calculate projected interceptions using odds-based probability
        
        Args:
            over_data: Dictionary with 'line' and 'odds' for over
            under_data: Dictionary with 'line' and 'odds' for under
            
        Returns:
            float: Projected interceptions
        """
        try:
            print(f"Calculating interceptions projection:")
            print(f"Over data: {over_data}")
            print(f"Under data: {under_data}")
            
            # Convert odds to probabilities
            over_prob = self.odds_to_probability(over_data['odds'])
            under_prob = self.odds_to_probability(under_data['odds'])
            
            # Normalize probabilities
            total_prob = over_prob + under_prob
            over_prob /= total_prob
            under_prob /= total_prob
            
            print(f"Probabilities - Over: {over_prob:.3f}, Under: {under_prob:.3f}")
            
            # Base value is the line (typically 0.5)
            base = over_data['line']
            
            # Calculate adjustment based on probability difference
            prob_diff = over_prob - under_prob  # Will be positive if over is favored
            max_adjustment = 0.5  # Maximum adjustment to make
            
            # Scale the adjustment based on probability difference
            adjustment = prob_diff * max_adjustment
            projected = base + adjustment
            
            print(f"Base: {base}, Prob diff: {prob_diff:.3f}, Adjustment: {adjustment:.3f}")
            print(f"Projected interceptions: {projected:.3f}")
            return projected
            
        except Exception as e:
            print(f"Error calculating interceptions: {e}")
            return None

    def calculate_projected_passing_tds(self, over_data: dict, under_data: dict) -> float:
        """
        Calculate projected passing TDs using odds-based probability
        
        Args:
            over_data: Dictionary with 'line' (typically 1.5) and 'odds' for over
            under_data: Dictionary with 'line' and 'odds' for under
            
        Returns:
            float: Projected passing TDs
        """
        line = over_data['line']  # Usually 1.5
        
        # Convert odds to probabilities
        over_prob = self.odds_to_probability(over_data['odds'])
        under_prob = self.odds_to_probability(under_data['odds'])
        
        # Normalize probabilities
        total_prob = over_prob + under_prob
        over_prob /= total_prob
        under_prob /= total_prob
        
        # Calculate expected TDs based on probabilities
        # If over 1.5, expect between 1.5 and 2.5 based on odds strength
        # If under 1.5, expect between 0.5 and 1.5 based on odds strength
        if over_prob > under_prob:
            # More likely to go over
            excess_prob = (over_prob - 0.5) * 2  # Scale from 0 to 1
            projected = line + (excess_prob * 1.0)  # Can add up to 1.0 TDs
        else:
            # More likely to go under
            excess_prob = (under_prob - 0.5) * 2  # Scale from 0 to 1
            projected = line - (excess_prob * 1.0)  # Can subtract up to 1.0 TDs
            
        return projected
    
    @staticmethod
    def odds_to_probability(odds: float) -> float:
        """Convert American odds to probability"""
        if odds < 0:
            return abs(odds) / (abs(odds) + 100)
        return 100 / (odds + 100)

    def calculate_projected_value(self, over_data: dict, under_data: dict) -> float:
        """Calculate projected value between over and under lines"""
        # Calculate midpoint and range
        midpoint = (over_data['line'] + under_data['line']) / 2
        line_range = (under_data['line'] - over_data['line']) / 2
        
        # Calculate odds-based adjustment
        odds_diff = abs(over_data['odds']) - abs(under_data['odds'])
        max_odds_diff = 50
        odds_adjustment = (odds_diff / max_odds_diff) * 0.5
        odds_adjustment = max(min(odds_adjustment, 0.5), -0.5)
        
        # Apply adjustment to midpoint within the range
        projected = midpoint + (line_range * odds_adjustment)
        
        return projected

    def parse_single_prop(self, html_element) -> dict:
        """Parse a single prop bet element"""
        try:
            line_elem = html_element.find("span", class_="data-moneyline")
            odds_elem = html_element.find("small", class_="data-odds best")
            
            if not line_elem or not odds_elem:
                return None
                
            line_text = line_elem.text.strip()
            odds_text = odds_elem.text.strip()
            
            # Parse direction and line
            direction = line_text[0].lower()
            line = float(line_text[1:])
            
            # Parse odds
            odds = -110 if odds_text.lower() == 'even' else float(odds_text)
            
            return {
                'direction': direction,
                'line': line,
                'odds': odds
            }
        except Exception as e:
            print(f"Error parsing prop element: {e}")
            return None


class PropsScraper:
    """Scraper for collecting all props from the website"""
    
    def __init__(self, week: int):
        self.week = week
        self.driver = None
        self.parser = PropsParser()
        self.current_stat_type = None  # Add this to track current stat type
    
    def setup_driver(self):
        """Initialize Selenium WebDriver"""
        self.driver = webdriver.Firefox()
        self.driver.get('https://www.scoresandodds.com/nfl/props')
        self.driver.implicitly_wait(120)
    
    def get_prop_value(self, html_element: BeautifulSoup, stat_type: str) -> float:
        """
        Get projected value for a prop based on stat type
        
        Args:
            html_element: BeautifulSoup element containing prop data
            stat_type: Type of stat being parsed
            
        Returns:
            float: Projected value or raw odds for touchdowns
        """
        try:
            if stat_type == "Touchdowns":
                return self.parser.parse_touchdown_odds(html_element)
            
            # Handle over/under props
            over_data, under_data = self.parser.parse_over_under(html_element)
            if not over_data or not under_data:
                return None
            
            if stat_type == "Passing TDS":
                return self.parser.calculate_projected_passing_tds(over_data, under_data)
            elif stat_type == "Interceptions":
                return self.parser.calculate_projected_interceptions(over_data, under_data)
            else:
                return self.parser.calculate_projected_value(over_data, under_data)
                
        except Exception as e:
            print(f"Error processing {stat_type} prop: {e}")
            return None

    def parse_props_element(self, html, stat_type: str) -> float:
        """Parse props element and return projected value"""
        try:
            # Find over/under containers
            odds_containers = html.find_all("div", class_="best-odds-container")
            
            over_data = under_data = None
            
            # Parse each container
            for container in odds_containers:
                prop_data = self.parser.parse_single_prop(container)
                if not prop_data:
                    continue
                
                if prop_data['direction'] == 'o':
                    over_data = {'line': prop_data['line'], 'odds': prop_data['odds']}
                elif prop_data['direction'] == 'u':
                    under_data = {'line': prop_data['line'], 'odds': prop_data['odds']}
            
            if not over_data or not under_data:
                return None
                
            # Use appropriate calculation method based on stat type
            if stat_type == "Passing TDS":
                return self.parser.calculate_projected_passing_tds(over_data, under_data)
            else:
                return self.parser.calculate_projected_value(over_data, under_data)
            
        except Exception as e:
            print(f"Error processing props element: {e}")
            return None
    
    def scrape_props(self) -> pd.DataFrame:
        """Scrape all props and return as DataFrame"""
        try:
            data_dict = defaultdict(dict)
            
            for i in range(len(STAT_LIST) - 1):
                self.current_stat_type = STAT_LIST[i]
                print(f"\nProcessing {self.current_stat_type}...")
                
                # Get current page data
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                odds_list = soup.find_all('ul', class_="table-list")[0].find_all("li")
                print(f"Found {len(odds_list)} props to process")
                
                # Parse each prop
                for entry in odds_list:
                    try:
                        name = entry.find("div", class_="props-name").text.strip()
                        name = ' '.join(name.split()[:2])
                        
                        value = self.get_prop_value(entry, self.current_stat_type)
                        print(f"  {name}: {value}")
                        
                        if value is not None:
                            data_dict[self.current_stat_type][name] = value
                        else:
                            print(f"  Warning: No value found for {name} ({self.current_stat_type})")
                            
                    except Exception as e:
                        print(f"  Error processing entry: {e}")
                
                print(f"Processed {len(data_dict[self.current_stat_type])} valid props for {self.current_stat_type}")
                
                # Print current data
                print("\nCurrent data dictionary:")
                for stat_type, values in data_dict.items():
                    print(f"{stat_type}: {len(values)} entries")
                    if len(values) > 0:
                        print(f"Sample: {list(values.items())[:2]}")
                
                self._navigate_to_next_stat(i)
            
            # Handle last stat type
            self.current_stat_type = STAT_LIST[-1]
            print(f"\nProcessing final stat type: {self.current_stat_type}")
            
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            odds_list = soup.find_all('ul', class_="table-list")[0].find_all("li")
            print(f"Found {len(odds_list)} props to process")
            
            for entry in odds_list:
                try:
                    name = entry.find("div", class_="props-name").text.strip()
                    name = ' '.join(name.split()[:2])
                    
                    value = self.get_prop_value(entry, self.current_stat_type)
                    print(f"  {name}: {value}")
                    
                    if value is not None:
                        data_dict[self.current_stat_type][name] = value
                    else:
                        print(f"  Warning: No value found for {name} ({self.current_stat_type})")
                        
                except Exception as e:
                    print(f"  Error processing entry: {e}")
            
            print("\nFinal data dictionary:")
            for stat_type, values in data_dict.items():
                print(f"{stat_type}: {len(values)} entries")
                if len(values) > 0:
                    print(f"Sample: {list(values.items())[:2]}")
            
            df = self._create_dataframe(data_dict)
            print("\nFinal DataFrame shape:", df.shape)
            print("Columns:", df.columns.tolist())
            return df
            
        except Exception as e:
            print(f"Error in scrape_props: {e}")
            raise
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
    
    def _create_dataframe(self, data_dict: dict) -> pd.DataFrame:
        """Convert scraped data to DataFrame"""
        # Get all unique names
        all_names = set()
        for stat in STAT_LIST:
            all_names.update(data_dict[stat].keys())
        
        # Create DataFrame
        df = pd.DataFrame({"Name": list(all_names)})
        
        # Add stats columns
        for stat in STAT_LIST:
            stat_df = pd.DataFrame(data_dict[stat].items(), columns=["Name", stat])
            df = pd.merge(df, stat_df, how='left', on='Name')
        
        return df
    
    def cleanup(self):
        """Close browser and cleanup"""
        if self.driver:
            self.driver.quit()




def main(argv):
    """
    Main function for NFL props scraping and DFS points calculation
    
    Args:
        argv: Command line arguments
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Scrape NFL props and calculate DFS points')
    parser.add_argument("week", type=int, help="NFL Week")
    args = parser.parse_args()
    
    try:
        # Step 1: Scrape props data
        print(f"Scraping props data for Week {args.week}...")
        scraper = PropsScraper(args.week)
        scraper.setup_driver()
        master_df = scraper.scrape_props()
        
        # Step 2: Calculate DFS points for each stat type
        print("\nCalculating DFS points...")
        calculator = DFSPointsCalculator()
        
        for stat, dfs_col in STAT_DICT.items():
            master_df[dfs_col] = master_df[stat].apply(
                getattr(calculator, stat.lower().replace(' ', '_'))
            )
        
        # Step 3: Calculate total DFS points
        master_df["DFS Total"] = master_df[list(STAT_DICT.values())].sum(axis=1)
        
        # Step 4: Save results
        output_dir = f"2024/WEEK{args.week}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Save combined data
        output_path = f"{output_dir}/NFL_Proj_DFS.csv"
        # Order columns: Name, raw props, DFS points columns, Total
        columns_order = (
            ["Name"] +                    # Name first
            list(STAT_DICT.keys()) +      # Raw props
            list(STAT_DICT.values()) +    # DFS points
            ["DFS Total"]                 # Total last
        )
        master_df[columns_order].to_csv(output_path, index=False)
        print(f"\nSaved data to: {output_path}")
        
        # Print summary
        print("\nSummary:")
        print(f"Total players processed: {len(master_df)}")
        print(f"Average DFS points: {master_df['DFS Total'].mean():.2f}")
        print(f"\nTop 5 projected players:")
        top_5 = master_df.nlargest(5, "DFS Total")[["Name", "DFS Total"]]
        print(top_5.to_string(index=False))
        
    except Exception as e:
        print(f"\nError: {e}")
        if "scraper" in locals():
            scraper.cleanup()
        sys.exit(1)
        
    finally:
        if "scraper" in locals():
            scraper.cleanup()

if __name__ == "__main__":
    
    main(sys.argv[1:])