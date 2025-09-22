"""ESPN Fantasy Projections Scraper for DFS Lineup Optimization"""

import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import logging
import warnings
from typing import Dict, List, Optional, Tuple
from utils import clean_player_name

# Suppress urllib3 connection warnings that flood console on Ctrl+C
warnings.filterwarnings("ignore", message=".*Connection refused.*")
warnings.filterwarnings("ignore", message=".*Max retries exceeded.*")
warnings.filterwarnings("ignore", message=".*Failed to establish a new connection.*")

# Suppress urllib3 warnings specifically
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    urllib3.disable_warnings(urllib3.exceptions.MaxRetryError)
    urllib3.disable_warnings(urllib3.exceptions.NewConnectionError)
    urllib3.disable_warnings()
except ImportError:
    pass

# Suppress urllib3 logging warnings
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)
logging.getLogger("urllib3.util.retry").setLevel(logging.ERROR)

# Suppress selenium logging warnings
logging.getLogger("selenium").setLevel(logging.ERROR)
logging.getLogger("selenium.webdriver").setLevel(logging.ERROR)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ESPNFantasyScraper:
    """ESPN fantasy scraper with manual login support"""
    
    def __init__(self):
        """Initialize the scraper"""
        self.driver = None
        self.wait = None
        self.base_url = "https://fantasy.espn.com/football/players/add?leagueId=819459"
        self.dk_salaries_players = set()  # Cache of DraftKings player names
        
    def setup_driver(self):
        """Set up Chrome WebDriver with appropriate options"""
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        # Uncomment below line if you want to run headless
        # options.add_argument("--headless")
        
        try:
            # Use webdriver-manager to automatically download and manage Chrome driver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            # Remove webdriver property to avoid detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 10)
            logger.info("Chrome WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise
    
    def navigate_to_fantasy_page(self):
        """Navigate to the ESPN fantasy players page and wait for manual login"""
        try:
            logger.info("Navigating to ESPN fantasy page...")
            self.driver.get(self.base_url)
            
            # Wait for user to manually complete login
            logger.info("Waiting for you to complete login manually...")
            logger.info("Please login to ESPN if prompted, then press Enter in this terminal when ready to continue.")
            
            # Wait for user input to continue
            input("Press Enter after you've completed login and can see the players page...")
            
            # Wait longer for the page to fully load and avoid application errors
            logger.info("Waiting for page to fully load...")
            time.sleep(5)  # Give extra time for JavaScript to load
            
            # Wait for the page to load with player data
            logger.info("Waiting for page to load with player data...")
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "Table__TR"))
            )
            
            # Additional wait to ensure all data is loaded
            time.sleep(3)
            
            logger.info("Successfully navigated to ESPN fantasy page")
            
        except Exception as e:
            logger.error(f"Failed to navigate to fantasy page: {e}")
            logger.error("Make sure you can see the players table on the page")
            raise
    
    def extract_player_data_from_row(self, row) -> Optional[Dict]:
        """
        Extract player data directly from table row without clicking (coarse analysis)
        
        Args:
            row: Selenium element for the player row
            
        Returns:
            Dictionary containing player data and projection
        """
        try:
            # Get player name
            try:
                player_name_elem = row.find_element(By.CSS_SELECTOR, "a.AnchorLink.link.clr-link.pointer")
                player_name = player_name_elem.text.strip()
                if not player_name:
                    return None
            except Exception as e:
                logger.warning(f"Could not get player name: {e}")
                return None
            
            # Get team
            try:
                team_elem = row.find_element(By.CLASS_NAME, "playerinfo__playerteam")
                team = team_elem.text.strip()
            except Exception as e:
                logger.warning(f"Could not get team: {e}")
                team = ""
            
            # Get position
            try:
                pos_elem = row.find_element(By.CLASS_NAME, "playerinfo__playerpos")
                position = pos_elem.text.strip()
            except Exception as e:
                logger.warning(f"Could not get position: {e}")
                position = ""
            
            # Get opponent
            try:
                opponent_elem = row.find_element(By.CSS_SELECTOR, "span.pro-team-abbrev")
                opponent = opponent_elem.text.strip()
            except Exception as e:
                logger.warning(f"Could not get opponent: {e}")
                opponent = ""
            
            # Get projected points from 6th column (td:nth-child(6))
            try:
                # The projected points are in the 6th column
                projected_elem = row.find_element(By.CSS_SELECTOR, "td:nth-child(6) span")
                projected_points = projected_elem.text.strip()
            except Exception as e:
                logger.warning(f"Could not get projected points: {e}")
                projected_points = ""
            
            return {
                'player_name': clean_player_name(player_name),
                'team': team,
                'position': position,
                'opponent': opponent,
                'projected_points': projected_points,
                'bust_score': '0',
                'projected_score': '0',
                'boom_score': '0',
                'bust_percentage': '0',
                'boom_percentage': '0'
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract data from row: {e}")
            return None

    def extract_player_data_from_popup(self, player_element) -> Optional[Dict]:
        """
        Extract bust, projected, and boom values from player popup
        
        Args:
            player_element: Selenium element for the player row
            
        Returns:
            Dictionary containing player data and projections
        """
        try:
            # Get player name and basic info with fallbacks
            try:
                # Try multiple selectors to find the player name
                player_name_elem = None
                selectors = [
                    "a.AnchorLink.link.clr-link.pointer:not(.playerinfo__news)",
                    "a.AnchorLink.link.clr-link:not(.playerinfo__news)",
                    "a.AnchorLink.link:not(.playerinfo__news)",
                    "a.AnchorLink:not(.playerinfo__news)",
                    "a[class*='AnchorLink']:not(.playerinfo__news)"
                ]
                
                for selector in selectors:
                    try:
                        # Find all matching elements and take the first one that's not the news link
                        elements = player_element.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            if elem and elem.text.strip() and "playerinfo__news" not in elem.get_attribute("class"):
                                player_name_elem = elem
                                break
                        if player_name_elem:
                            break
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                
                if not player_name_elem:
                    logger.warning("No player name element found")
                    return None
                    
                player_name = player_name_elem.text.strip()
                if not player_name:
                    logger.warning("Empty player name found")
                    return None
            except Exception as e:
                logger.warning(f"Could not get player name: {e}")
                return None
            
            # Get team and position with fallbacks
            try:
                team_pos_elem = player_element.find_element(By.CLASS_NAME, "playerinfo__playerteam")
                team = team_pos_elem.text.strip()
            except Exception as e:
                logger.warning(f"Could not get team: {e}")
                team = ""
            
            try:
                pos_elem = player_element.find_element(By.CLASS_NAME, "playerinfo__playerpos")
                position = pos_elem.text.strip()
            except Exception as e:
                logger.warning(f"Could not get position: {e}")
                position = ""
            
            # Get opponent with fallback
            try:
                opponent_elem = player_element.find_element(By.CSS_SELECTOR, "span.pro-team-abbrev")
                opponent = opponent_elem.text.strip()
            except Exception as e:
                logger.warning(f"Could not get opponent: {e}")
                opponent = ""
            
            # Get projected points from main table with fallback
            try:
                projected_elem = player_element.find_element(By.CSS_SELECTOR, "td:nth-child(6) span")
                projected_points = projected_elem.text.strip()
            except Exception as e:
                logger.warning(f"Could not get projected points: {e}")
                projected_points = ""
            
            # Click on player name to open popup - use JavaScript to avoid click interception
            self.driver.execute_script("arguments[0].click();", player_name_elem)
            time.sleep(2)  # Give more time for popup to appear
            
            # Wait for popup to appear and extract data
            popup_data = self.extract_popup_projections()
            
            if popup_data and player_name:  # Ensure we have at least a player name
                return {
                    'player_name': clean_player_name(player_name),
                    'team': team,
                    'position': position,
                    'opponent': opponent,
                    'projected_points': projected_points,
                    'bust_score': popup_data.get('bust_score'),
                    'projected_score': popup_data.get('projected_score'),
                    'boom_score': popup_data.get('boom_score'),
                    'bust_percentage': popup_data.get('bust_percentage'),
                    'boom_percentage': popup_data.get('boom_percentage')
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to extract data for player: {e}")
            return None
    
    def debug_popup_content(self):
        """Debug function to see what elements are present when popup appears"""
        try:
            # Get all elements that might be part of the popup
            possible_popup_elements = self.driver.find_elements(By.CSS_SELECTOR, "[class*='lightbox'], [class*='popup'], [class*='modal'], [class*='overlay']")
            
            logger.info(f"Found {len(possible_popup_elements)} possible popup elements:")
            for i, elem in enumerate(possible_popup_elements):
                try:
                    class_name = elem.get_attribute("class")
                    text = elem.text[:100] if elem.text else "No text"
                    logger.info(f"  Element {i}: class='{class_name}', text='{text}'")
                except:
                    logger.info(f"  Element {i}: Could not get details")
            
            # Also look for key-values specifically
            key_values = self.driver.find_elements(By.CSS_SELECTOR, "[class*='key-values']")
            logger.info(f"Found {len(key_values)} key-values elements")
            
        except Exception as e:
            logger.error(f"Debug failed: {e}")

    def ensure_popup_closed(self):
        """
        Ensure any open popup is closed and page is in good state
        """
        try:
            # Check for various popup indicators
            popup_selectors = [
                "div[class*='lightbox']",
                "div.jsx-3684495974.lightbox__closebtn",
                "iframe[src*='watsonfantasyfootball.espn.com']"
            ]
            
            for selector in popup_selectors:
                try:
                    popup = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if popup.is_displayed():
                        logger.info(f"Found open popup with selector: {selector}")
                        
                        # Try to close it
                        try:
                            close_btn = self.driver.find_element(By.CSS_SELECTOR, "div.jsx-3684495974.lightbox__closebtn")
                            close_btn.click()
                            logger.info("Closed popup using close button")
                        except:
                            # Fallback: press ESC key
                            from selenium.webdriver.common.keys import Keys
                            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                            logger.info("Closed popup using ESC key")
                        
                        time.sleep(1)
                        break
                except:
                    continue
            
            # Switch back to default content if we were in an iframe
            try:
                self.driver.switch_to.default_content()
                logger.info("Switched back to main content")
            except:
                pass
                
        except Exception as e:
            logger.warning(f"Error ensuring popup closed: {e}")
    

    def navigate_to_next_page(self) -> bool:
        """
        Navigate to the next page of players
        
        Returns:
            True if successfully navigated to next page, False if no more pages
        """
        try:
            # Scroll to bottom to ensure pagination is visible
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Try multiple selectors for the next button
            next_button_selectors = [
                "button.Pagination__Button--next:not([disabled])",
                "button[class*='Pagination__Button--next']:not([disabled])",
                "button[aria-label*='next']:not([disabled])",
                "button[aria-label*='Next']:not([disabled])",
                ".Pagination__Button--next:not([disabled])",
                "[class*='pagination'] button:not([disabled])"
            ]
            
            next_button = None
            for selector in next_button_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem.is_displayed() and elem.is_enabled():
                            # Check if it's actually a next button
                            text = elem.text.lower().strip()
                            aria_label = elem.get_attribute("aria-label") or ""
                            class_name = elem.get_attribute("class") or ""
                            
                            if ("next" in text or "next" in aria_label.lower() or 
                                "next" in class_name.lower() or ">" in text):
                                next_button = elem
                                logger.info(f"Found next button: {text}")
                                break
                    if next_button:
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            # Fallback: look for pagination buttons with ">" or numeric page buttons
            if not next_button:
                pagination_buttons = self.driver.find_elements(By.CSS_SELECTOR, 
                    "[class*='pagination'] button, [class*='Pagination'] button")
                
                for button in pagination_buttons:
                    if button.is_displayed() and button.is_enabled():
                        text = button.text.strip()
                        if text in [">", "Next", "→"] or "next" in button.get_attribute("class").lower():
                            next_button = button
                            logger.info(f"Found pagination button: {text}")
                            break
            
            if next_button and next_button.is_enabled():
                # Use JavaScript click to avoid any click interception issues
                self.driver.execute_script("arguments[0].click();", next_button)
                time.sleep(3)  # Wait for page to load
                
                # Wait for new page content to load
                try:
                    self.wait.until(
                        EC.presence_of_element_located((By.CLASS_NAME, "Table__TR"))
                    )
                    logger.info("Successfully navigated to next page")
                    return True
                except TimeoutException:
                    logger.warning("Page navigation may have failed - no table rows found")
                    return False
            else:
                logger.info("No more pages available")
                return False
                
        except Exception as e:
            logger.warning(f"Error navigating to next page: {e}")
            return False

    def extract_popup_projections(self) -> Optional[Dict]:
        """
        Extract projection data from the popup modal
        
        Returns:
            Dictionary with bust, projected, and boom values
        """
        try:
            # Wait for popup to appear - try multiple selectors
            popup = None
            selectors_to_try = [
                (By.CSS_SELECTOR, "iframe[src*='watsonfantasyfootball.espn.com']"),
                (By.CSS_SELECTOR, "div.main-content.projections"),
                (By.CSS_SELECTOR, "div.key-values"),
                (By.CSS_SELECTOR, "div[class*='lightbox']"),
                (By.CSS_SELECTOR, "svg#chart"),
                (By.CLASS_NAME, "key-values"),
                (By.CSS_SELECTOR, ".key-values"),
                (By.CSS_SELECTOR, "[class*='key-values']"),
                (By.CSS_SELECTOR, "[class*='player-card']")
            ]
            
            for selector_type, selector in selectors_to_try:
                try:
                    popup = self.wait.until(
                        EC.presence_of_element_located((selector_type, selector))
                    )
                    logger.info(f"Found popup using selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not popup:
                logger.warning("Could not find popup with any selector")
                # Debug what's actually on the page
                self.debug_popup_content()
                return None
            
            # Debug what's in the popup we found
            logger.info(f"Found popup element with class: {popup.get_attribute('class')}")
            
            # Debug: Show what type of element we found
            element_tag = popup.tag_name
            element_src = popup.get_attribute('src') if element_tag == 'iframe' else 'N/A'
            logger.info(f"Popup element type: {element_tag}, src: {element_src}")
            
            # If we found an iframe, we need to switch to it first
            if element_tag == 'iframe':
                logger.info("Found iframe, switching to it...")
                try:
                    self.driver.switch_to.frame(popup)
                    logger.info("Successfully switched to iframe")
                    
                    # Wait for iframe content to load
                    time.sleep(3)
                    
                    # Now look for elements within the iframe
                    iframe_popup = self.driver
                except Exception as e:
                    logger.error(f"Failed to switch to iframe: {e}")
                    self.driver.switch_to.default_content()
                    iframe_popup = popup
            else:
                iframe_popup = popup
            
            # Look for the line-gauge-chart div first (this contains the projection chart)
            line_gauge_chart = iframe_popup.find_elements(By.CSS_SELECTOR, "div.line-gauge-chart")
            if line_gauge_chart:
                logger.info(f"Found line-gauge-chart div")
                chart_container = line_gauge_chart[0]
            else:
                logger.info("No line-gauge-chart found, looking for other charts...")
                chart_container = iframe_popup
            
            # Look for any SVG elements in the chart container
            svg_elements = chart_container.find_elements(By.TAG_NAME, "svg")
            logger.info(f"Found {len(svg_elements)} SVG elements in chart container")
            for i, svg in enumerate(svg_elements):
                logger.info(f"SVG {i}: id='{svg.get_attribute('id')}', class='{svg.get_attribute('class')}'")
            
            # Try to extract data from iframe first (Watson Fantasy Football)
            try:
                # Look for the iframe containing the Watson Fantasy Football data
                iframe = popup.find_element(By.CSS_SELECTOR, "iframe[src*='watsonfantasyfootball.espn.com']")
                logger.info("Found Watson Fantasy Football iframe")
                
                # Switch to the iframe
                self.driver.switch_to.frame(iframe)
                logger.info("Switched to iframe")
                
                # Wait for iframe content to load
                time.sleep(3)
                
                # Debug: See what's actually in the iframe
                logger.info("Debugging iframe content...")
                all_divs = self.driver.find_elements(By.TAG_NAME, "div")
                logger.info(f"Found {len(all_divs)} div elements in iframe")
                
                # Look for any elements with 'projection' in the class
                projection_elements = self.driver.find_elements(By.CSS_SELECTOR, "[class*='projection']")
                logger.info(f"Found {len(projection_elements)} elements with 'projection' in class")
                for i, elem in enumerate(projection_elements):
                    logger.info(f"Projection element {i}: class='{elem.get_attribute('class')}'")
                
                # Look for any elements with 'key-value' in the class
                key_value_elements = self.driver.find_elements(By.CSS_SELECTOR, "[class*='key-value']")
                logger.info(f"Found {len(key_value_elements)} elements with 'key-value' in class")
                for i, elem in enumerate(key_value_elements):
                    logger.info(f"Key-value element {i}: class='{elem.get_attribute('class')}', text='{elem.text[:50]}'")
                
                # Look for boom-bust-chart div
                boom_bust_chart = self.driver.find_elements(By.CSS_SELECTOR, "div.boom-bust-chart")
                logger.info(f"Found {len(boom_bust_chart)} boom-bust-chart divs")
                
                # Look for the projections section within the iframe
                try:
                    projections_section = self.driver.find_element(By.CSS_SELECTOR, "div.main-content.projections")
                    logger.info("Found projections section in iframe")
                except NoSuchElementException:
                    logger.info("No projections section found, trying alternative selectors...")
                    # Try other possible selectors
                    for selector in ["div.projections", "div[class*='projection']", "div.boom-bust-chart"]:
                        try:
                            projections_section = self.driver.find_element(By.CSS_SELECTOR, selector)
                            logger.info(f"Found alternative section with selector: {selector}")
                            break
                        except NoSuchElementException:
                            continue
                    else:
                        logger.error("No projections section found with any selector")
                        raise
                
                # Then find the key-values div within the projections section
                key_values_div = projections_section.find_element(By.CSS_SELECTOR, "div.key-values")
                logger.info("Found key-values div, extracting data...")
                
                # Extract bust percentage
                bust_elem = key_values_div.find_element(By.CSS_SELECTOR, ".key-value.bust .value")
                bust_percentage = bust_elem.text.replace('%', '').strip()
                logger.info(f"Found bust percentage: {bust_percentage}")
                
                # Extract projected score
                projected_elem = key_values_div.find_element(By.CSS_SELECTOR, ".key-value.projection .value")
                projected_score = projected_elem.text.replace(' pts', '').strip()
                logger.info(f"Found projected score: {projected_score}")
                
                # Extract boom percentage
                boom_elem = key_values_div.find_element(By.CSS_SELECTOR, ".key-value.boom .value")
                boom_percentage = boom_elem.text.replace('%', '').strip()
                logger.info(f"Found boom percentage: {boom_percentage}")
                
                # Switch back to main content
                self.driver.switch_to.default_content()
                logger.info("Switched back to main content")
                
                return {
                    'bust_score': bust_percentage,
                    'projected_score': projected_score,
                    'boom_score': boom_percentage
                }
                
            except NoSuchElementException as e:
                logger.info(f"Watson iframe extraction failed: {e}")
                
                # Fallback: Try to extract from the SVG chart directly since we know it's there
                try:
                    logger.info("Trying to extract from SVG chart as fallback...")
                    svg_chart = self.driver.find_element(By.CSS_SELECTOR, "svg#chart")
                    
                    # Extract text elements from SVG
                    text_elements = svg_chart.find_elements(By.TAG_NAME, "text")
                    logger.info(f"Found {len(text_elements)} text elements in SVG chart")
                    
                    bust_score = None
                    projected_score = None
                    boom_score = None
                    bust_percentage = None
                    boom_percentage = None
                    score_data = []  # Initialize score_data
                    percentage_data = []  # Initialize percentage_data
                    
                    # Look for the text elements with the scores
                    for text_elem in text_elements:
                        text_content = text_elem.text.strip()
                        x_attr = text_elem.get_attribute("x")
                        
                        logger.info(f"Text element: '{text_content}' at x={x_attr}")
                        
                        # Skip empty text and "pts" labels
                        if not text_content or text_content == "pts":
                            continue
                        
                        # Check if it's a percentage (contains %)
                        logger.info(f"Processing text: '{text_content}' - contains %: {'%' in text_content}")
                        if "%" in text_content:
                            logger.info(f"Found percentage text: '{text_content}'")
                            try:
                                # Extract numeric value from percentage
                                percentage_value = float(text_content.replace("%", ""))
                                percentage_data.append(percentage_value)
                                logger.info(f"Added percentage: {percentage_value}%")
                            except ValueError:
                                logger.warning(f"Failed to parse percentage: {text_content}")
                                continue
                        # Try to parse as float (score values)
                        try:
                            score_value = float(text_content)
                            
                            # Determine which score this is based on position
                            if x_attr:
                                x_pos = float(x_attr)
                                score_data.append((x_pos, score_value))
                                logger.info(f"Added score: {score_value} at x={x_pos}")
                            else:
                                # Fallback: assign based on order if we can't determine position
                                if bust_score is None:
                                    bust_score = score_value
                                    logger.info(f"Fallback: assigned bust score: {bust_score}")
                                elif projected_score is None:
                                    projected_score = score_value
                                    logger.info(f"Fallback: assigned projected score: {projected_score}")
                                elif boom_score is None:
                                    boom_score = score_value
                                    logger.info(f"Fallback: assigned boom score: {boom_score}")
                                    
                        except ValueError:
                            # Not a numeric value, skip
                            continue
                    
                    # Sort by x-position and assign in order: bust < projected < boom
                    if score_data:
                        score_data.sort(key=lambda x: x[0])  # Sort by x-position
                        logger.info(f"Sorted scores by x-position: {score_data}")
                        
                        # Assign in order: lowest x = bust, middle x = projected, highest x = boom
                        if len(score_data) >= 1:
                            bust_score = score_data[0][1]  # Lowest x-position
                            logger.info(f"Assigned bust score: {bust_score}")
                        
                        if len(score_data) >= 2:
                            projected_score = score_data[1][1]  # Middle x-position
                            logger.info(f"Assigned projected score: {projected_score}")
                        
                        if len(score_data) >= 3:
                            boom_score = score_data[2][1]  # Highest x-position
                            logger.info(f"Assigned boom score: {boom_score}")
                    
                    # Convert scores to strings for return
                    bust_percentage = percentage_data[0]
                    boom_percentage = percentage_data[1]
                    
                    # Switch back to main content
                    self.driver.switch_to.default_content()
                    logger.info("Switched back to main content")
                    
                    return {
                        'bust_score': bust_score,
                        'projected_score': projected_score,
                        'boom_score': boom_score,
                        'bust_percentage': bust_percentage,
                        'boom_percentage': boom_percentage
                    }
                    
                except Exception as svg_error:
                    logger.info(f"SVG fallback also failed: {svg_error}")
                    # Switch back to main content in case we were in an iframe
                    self.driver.switch_to.default_content()
                
                
            
            # Fallback: Extract data from SVG chart
            try:
                # Find any SVG element in the popup
                svg_elements = popup.find_elements(By.TAG_NAME, "svg")
                if not svg_elements:
                    logger.warning("No SVG elements found in popup")
                    return None
                
                # Look for the chart SVG (prefer svg#chart for line-gauge-chart)
                svg_chart = None
                for svg in svg_elements:
                    svg_id = svg.get_attribute('id')
                    svg_class = svg.get_attribute('class')
                    
                    # Prefer the chart with id="chart" (line-gauge-chart)
                    if svg_id == 'chart':
                        svg_chart = svg
                        logger.info(f"Found chart SVG: id='{svg_id}', class='{svg_class}'")
                        break
                    elif 'recharts-surface' in svg_class:
                        svg_chart = svg
                        logger.info(f"Found recharts SVG: class='{svg_class}'")
                        break
                
                if not svg_chart:
                    # Fallback to first SVG that's not an icon
                    for svg in svg_elements:
                        svg_class = svg.get_attribute('class')
                        if 'icon' not in svg_class and 'svg' not in svg_class:
                            svg_chart = svg
                            logger.info(f"Using fallback SVG: class='{svg_class}'")
                            break
                
                if not svg_chart:
                    logger.warning("No suitable chart SVG found")
                    return None
                
                # Extract text elements from SVG
                text_elements = svg_chart.find_elements(By.TAG_NAME, "text")
                logger.info(f"Found {len(text_elements)} text elements in SVG chart")
                
                # Also look for other elements that might contain data
                all_elements = svg_chart.find_elements(By.XPATH, ".//*")
                logger.info(f"Found {len(all_elements)} total elements in SVG chart")
                
                # Log all text content from the SVG
                for elem in all_elements:
                    try:
                        text_content = elem.text.strip()
                        if text_content:
                            tag_name = elem.tag_name
                            logger.info(f"SVG element {tag_name}: '{text_content}'")
                    except:
                        pass
                
                bust_score = None
                projected_score = None
                boom_score = None
                bust_percentage = None
                boom_percentage = None
                score_data = []  # Initialize score_data early
                percentage_data = []  # Initialize percentage_data
                
                # Collect all numeric values with their x-positions
                for text_elem in text_elements:
                    text_content = text_elem.text.strip()
                    x_attr = text_elem.get_attribute("x")
                    
                    logger.info(f"Text element: '{text_content}' at x={x_attr}")
                    
                    # Skip empty text and "pts" labels
                    if not text_content or text_content == "pts":
                        logger.info(f"Skipping empty text: '{text_content}'")
                        continue
                    
                    # Check if it's a percentage (contains %)
                    logger.info(f"Processing text: '{text_content}' - contains %: {'%' in text_content}")
                    if "%" in text_content:
                        logger.info(f"Found percentage text: '{text_content}'")
                        try:
                            # Extract numeric value from percentage
                            percentage_value = float(text_content.replace("%", ""))
                            percentage_data.append(percentage_value)
                            logger.info(f"Added percentage: {percentage_value}%")
                        except ValueError:
                            logger.warning(f"Failed to parse percentage: {text_content}")
                            continue
                    # Also check for percentage values without % symbol (fallback)
                    elif text_content.isdigit() and len(text_content) <= 3:  # Likely a percentage without % symbol
                        try:
                            percentage_value = float(text_content)
                            if 0 <= percentage_value <= 100:  # Reasonable percentage range
                                percentage_data.append(percentage_value)
                                logger.info(f"Added percentage (no % symbol): {percentage_value}%")
                        except ValueError:
                            pass  # Not a valid number, continue to next check
                    else:
                        # Try to parse as float (score values)
                        try:
                            score_value = float(text_content)
                            x_pos = float(x_attr) if x_attr else None
                            
                            if x_pos is not None:
                                score_data.append((x_pos, score_value))
                                logger.info(f"Added score: {score_value} at x={x_pos}")
                            else:
                                # Fallback: assign based on order if we can't determine position
                                if bust_score is None:
                                    bust_score = score_value
                                    logger.info(f"Fallback: assigned bust score: {bust_score}")
                                elif projected_score is None:
                                    projected_score = score_value
                                    logger.info(f"Fallback: assigned projected score: {projected_score}")
                                elif boom_score is None:
                                    boom_score = score_value
                                    logger.info(f"Fallback: assigned boom score: {boom_score}")
                                    
                        except ValueError:
                            # Not a numeric value, skip
                            continue
                
                # Sort by x-position and assign in order: bust < projected < boom
                if score_data:
                    score_data.sort(key=lambda x: x[0])  # Sort by x-position
                    logger.info(f"Sorted scores by x-position: {score_data}")
                    
                    # Assign in order: lowest x = bust, middle x = projected, highest x = boom
                    if len(score_data) >= 1:
                        bust_score = score_data[0][1]  # Lowest x-position
                        logger.info(f"Assigned bust score: {bust_score}")
                    
                    if len(score_data) >= 2:
                        projected_score = score_data[1][1]  # Middle x-position
                        logger.info(f"Assigned projected score: {projected_score}")
                    
                    if len(score_data) >= 3:
                        boom_score = score_data[2][1]  # Highest x-position
                        logger.info(f"Assigned boom score: {boom_score}")
                
                # Assign percentages (bust percentage comes first)
                logger.info(f"Collected percentage data: {percentage_data}")
                if len(percentage_data) >= 1:
                    bust_percentage = percentage_data[0]  # First percentage
                    logger.info(f"Assigned bust percentage: {bust_percentage}%")
                
                if len(percentage_data) >= 2:
                    boom_percentage = percentage_data[1]  # Second percentage
                    logger.info(f"Assigned boom percentage: {boom_percentage}%")
                
                # Switch back to main content
                self.driver.switch_to.default_content()
                logger.info("Switched back to main content")
                
                return {
                    'bust_score': str(bust_score) if bust_score is not None else None,
                    'projected_score': str(projected_score) if projected_score is not None else None,
                    'boom_score': str(boom_score) if boom_score is not None else None,
                    'bust_percentage': str(bust_percentage) if bust_percentage is not None else None,
                    'boom_percentage': str(boom_percentage) if boom_percentage is not None else None
                }
                
            except Exception as e:
                logger.warning(f"Failed to extract from SVG chart: {e}")
                # Reset variables in case of error
                bust_score = None
                projected_score = None
                boom_score = None
                
                # Fallback: try to find data in other elements
                logger.info("Trying fallback extraction methods...")
                
                # Look for any text elements that might contain the scores
                all_text_elements = popup.find_elements(By.TAG_NAME, "text")
                logger.info(f"Found {len(all_text_elements)} text elements in popup")
                
                for text_elem in all_text_elements:
                    text_content = text_elem.text.strip()
                    if text_content and text_content != "pts":
                        logger.info(f"Text element: '{text_content}'")
                
                # Also look for any div elements that might contain the data
                div_elements = popup.find_elements(By.TAG_NAME, "div")
                for div_elem in div_elements:
                    text_content = div_elem.text.strip()
                    if text_content and len(text_content) < 20:  # Short text that might be scores
                        logger.info(f"Div element: '{text_content}'")
                
                bust_percentage = None
                projected_score = None
                boom_percentage = None
            
            # Close popup using the close button
            try:
                close_btn = self.driver.find_element(By.CSS_SELECTOR, "div.jsx-3684495974.lightbox__closebtn")
                close_btn.click()
                logger.info("Closed popup using close button")
            except NoSuchElementException:
                # Fallback: try clicking outside or pressing ESC
                try:
                    self.driver.find_element(By.TAG_NAME, "body").click()
                    logger.info("Closed popup by clicking outside")
                except:
                    # Final fallback: press ESC key
                    from selenium.webdriver.common.keys import Keys
                    self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                    logger.info("Closed popup using ESC key")
            
            # Wait for popup to close
            time.sleep(1)
            
            return {
                'bust_score': bust_score,
                'projected_score': projected_score,
                'boom_score': boom_score,
                'bust_percentage': bust_percentage,
                'boom_percentage': boom_percentage
            }
            
        except TimeoutException:
            logger.warning("Popup did not appear within timeout")
            return None
        except Exception as e:
            logger.warning(f"Failed to extract popup data: {e}")
            return None
    
    def scrape_all_players(self, output_file: str = "espn_fantasy_projections.csv", max_pages: int = None, coarse_mode: bool = False) -> pd.DataFrame:
        """
        Scrape projections for all players across multiple pages
        
        Args:
            output_file: Name of the output CSV file
            max_pages: Maximum number of pages to scrape (None for all pages)
            coarse_mode: If True, use simplified extraction (no clicking). If False, use detailed extraction with popups.
            
        Returns:
            DataFrame with all player projections
        """
        # Load existing data to avoid duplicates
        existing_df = self.load_existing_data(output_file)
        players_data = []
        page_num = 1
        seen_players = set()  # Track unique players to detect when we're getting duplicates
        consecutive_no_new_players = 0  # Track consecutive pages with no new players
        max_consecutive_no_new = 8  # Maximum consecutive pages with no new players before stopping
        
        try:
            while True:
                logger.info(f"Processing page {page_num}")
                
                # Wait for page to load
                time.sleep(2)
                
                # Find all player rows on current page
                player_rows = self.driver.find_elements(By.CSS_SELECTOR, "tr.Table__TR")
                logger.info(f"Found {len(player_rows)} player rows on page {page_num}")
                
                if not player_rows:
                    logger.warning(f"No player rows found on page {page_num}")
                    break
                
                # Track players before processing this page
                players_before = len(seen_players)
                
                # Process all players on current page
                page_new_players = self._process_players_on_page(player_rows, existing_df, players_data, output_file, coarse_mode, seen_players)
                
                # Check if we got any new players
                players_after = len(seen_players)
                new_players_this_page = players_after - players_before
                
                logger.info(f"Page {page_num}: {new_players_this_page} new players found (total unique: {players_after})")
                
                if new_players_this_page == 0:
                    consecutive_no_new_players += 1
                    logger.warning(f"No new players found on page {page_num} ({consecutive_no_new_players}/{max_consecutive_no_new})")
                    
                    if consecutive_no_new_players >= max_consecutive_no_new:
                        logger.info(f"Stopping: {consecutive_no_new_players} consecutive pages with no new players")
                        break
                else:
                    consecutive_no_new_players = 0  # Reset counter
                
                # Check if we should continue to next page
                if max_pages and page_num >= max_pages:
                    logger.info(f"Reached maximum pages limit ({max_pages})")
                    break
                
                # Safety check: don't go beyond reasonable page count
                if page_num >= 50:  # ESPN shouldn't have more than 50 pages
                    logger.warning(f"Reached safety limit of 50 pages - stopping")
                    break
                
                # Try to navigate to next page
                logger.info(f"Attempting to navigate to page {page_num + 1}...")
                if not self.navigate_to_next_page():
                    logger.info("No more pages available - pagination complete")
                    break
                
                page_num += 1
                logger.info(f"Successfully moved to page {page_num}")
            
            # Combine existing and new data after all pages are processed
            return self._combine_and_summarize_data(existing_df, players_data)
        
        except Exception as e:
            logger.error(f"Failed to scrape players: {e}")
            raise
    
    def _process_players_on_page(self, player_rows, existing_df, players_data, output_file, coarse_mode=False, seen_players=None):
        """Process all players on a single page"""
        if seen_players is None:
            seen_players = set()
            
        dk_filtered_count = 0
        already_scraped_count = 0
        processed_count = 0
        new_players_count = 0
        
        for i, row in enumerate(player_rows):
            try:
                # Skip header rows or rows without player data
                if not row.get_attribute("data-idx"):
                    continue
                
                # Get player name
                player_name = self._extract_player_name(row, i)
                if not player_name:
                    continue
                
                # Check if player already scraped
                if self.is_player_already_scraped(player_name, existing_df):
                    logger.info(f"Skipping {player_name} - already scraped")
                    already_scraped_count += 1
                    continue
                
                # Check if player is in DraftKings salaries before processing
                if not self.is_player_in_dk_salaries(player_name):
                    logger.info(f"Skipping {player_name} - not in DKSalaries for this week")
                    dk_filtered_count += 1
                    continue
                
                # Track if this is a new player we haven't seen before
                is_new_player = player_name not in seen_players
                if is_new_player:
                    seen_players.add(player_name)
                    new_players_count += 1
                    logger.info(f"Processing NEW player {i+1}/{len(player_rows)}: {player_name}")
                else:
                    logger.info(f"Processing DUPLICATE player {i+1}/{len(player_rows)}: {player_name}")
                
                processed_count += 1
                
                # Extract player data based on mode
                if coarse_mode:
                    # Use simplified extraction (no clicking)
                    player_data = self.extract_player_data_from_row(row)
                else:
                    # Use detailed extraction (with popup clicking)
                    player_data = self.extract_player_data_from_popup(row)
                
                if player_data:
                    # Append to CSV immediately
                    self.append_player_to_csv(player_data, output_file)
                    players_data.append(player_data)
                    
                    # Print detailed player data for verification
                    self._print_player_summary(player_data)
                else:
                    logger.warning(f"Failed to extract data for {player_name}")
                
                # Only ensure popup is closed if not in coarse mode
                if not coarse_mode:
                    self.ensure_popup_closed()
                    time.sleep(1.5)  # Combined delay
                else:
                    time.sleep(0.1)  # Minimal delay for coarse mode
                
            except Exception as e:
                logger.warning(f"Failed to process player row {i}: {e}")
                continue
        
        # Log summary of page processing
        logger.info(f"Page summary - Processed: {processed_count}, New players: {new_players_count}, "
                   f"Already scraped: {already_scraped_count}, DK filtered: {dk_filtered_count}, Total rows: {len(player_rows)}")
        
        return new_players_count
    
    def _extract_player_name(self, row, row_index):
        """Extract player name from row with multiple selector fallbacks"""
        try:
            selectors = [
                "a.AnchorLink.link.clr-link.pointer:not(.playerinfo__news)",
                "a.AnchorLink.link.clr-link:not(.playerinfo__news)",
                "a.AnchorLink.link:not(.playerinfo__news)",
                "a.AnchorLink:not(.playerinfo__news)",
                "a[class*='AnchorLink']:not(.playerinfo__news)"
            ]
            
            for selector in selectors:
                try:
                    elements = row.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem and elem.text.strip() and "playerinfo__news" not in elem.get_attribute("class"):
                            player_name = elem.text.strip()
                            if player_name:
                                return player_name
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            logger.warning(f"No player name element found for row {row_index}")
            return None
            
        except Exception as e:
            logger.warning(f"Could not get player name for row {row_index}: {e}")
            return None
    
    def _print_player_summary(self, player_data):
        """Print summary of extracted player data"""
        print(f"\n{'='*50}")
        print(f"PLAYER: {player_data['player_name']}")
        print(f"TEAM: {player_data['team']} | POSITION: {player_data['position']}")
        print(f"OPPONENT: {player_data['opponent']}")
        print(f"PROJECTED POINTS: {player_data['projected_points']}")
        print(f"BUST SCORE: {player_data['bust_score']} ({player_data.get('bust_percentage', 'N/A')}%)")
        print(f"PROJECTED SCORE: {player_data['projected_score']}")
        print(f"BOOM SCORE: {player_data['boom_score']} ({player_data.get('boom_percentage', 'N/A')}%)")
        print(f"{'='*50}")
    
    def _combine_and_summarize_data(self, existing_df, players_data):
        """Combine existing and new data and print summary"""
        if not existing_df.empty:
            all_players_df = pd.concat([existing_df, pd.DataFrame(players_data)], ignore_index=True)
            logger.info(f"Combined {len(existing_df)} existing + {len(players_data)} new players")
        else:
            all_players_df = pd.DataFrame(players_data)
        
        logger.info(f"Total players in dataset: {len(all_players_df)}")
        
        # Print summary of collected data
        if len(all_players_df) > 0:
            print(f"\n{'='*60}")
            print(f"SCRAPING SUMMARY")
            print(f"{'='*60}")
            print(f"Total players in dataset: {len(all_players_df)}")
            print(f"New players scraped: {len(players_data)}")
            print(f"Positions found: {all_players_df['position'].value_counts().to_dict()}")
            print(f"Teams represented: {len(all_players_df['team'].unique())}")
            print(f"Sample of players:")
            for i, row in all_players_df.head(5).iterrows():
                print(f"  {row['player_name']} ({row['team']} {row['position']}) - {row['projected_points']} pts")
            print(f"{'='*60}")
        
        return all_players_df
    
    def save_to_csv(self, df: pd.DataFrame, filename: str = "espn_fantasy_projections.csv"):
        """Save scraped data to CSV file"""
        try:
            df.to_csv(filename, index=False)
            logger.info(f"Data saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save data to CSV: {e}")
            raise
    
    def append_player_to_csv(self, player_data: Dict, filename: str = "espn_fantasy_projections.csv"):
        """Append a single player's data to CSV file"""
        try:
            # Create DataFrame with single player
            df_new = pd.DataFrame([player_data])
            
            # Append to existing file or create new one
            df_new.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)
            logger.info(f"Appended {player_data['player_name']} to {filename}")
        except Exception as e:
            logger.error(f"Failed to append player data to CSV: {e}")
            raise
    
    def load_existing_data(self, filename: str = "espn_fantasy_projections.csv") -> pd.DataFrame:
        """Load existing data from CSV file"""
        try:
            if os.path.exists(filename):
                df = pd.read_csv(filename)
                logger.info(f"Loaded existing data: {len(df)} players from {filename}")
                return df
            else:
                logger.info(f"No existing data file found: {filename}")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Failed to load existing data: {e}")
            return pd.DataFrame()
    
    def is_player_already_scraped(self, player_name: str, existing_df: pd.DataFrame) -> bool:
        """Check if a player has already been scraped"""
        if existing_df.empty:
            return False
        return player_name in existing_df['player_name'].values
    
    def load_dk_salaries(self, week: int) -> None:
        """
        Load DraftKings salaries for the specified week to filter relevant players
        
        Args:
            week: Week number (e.g., 1, 2, 3)
        """
        try:
            # Try different possible file patterns for the week
            possible_paths = [
                f"2025/WEEK{week}/DKSalaries - *.csv",  # Current 2025 format
                f"2025/WEEK{week}/DKSalaries-Week{week}.csv",  # Alternative format
                f"2024/WEEK{week}/DKSalaries-Week{week}.csv",  # 2024 format fallback
            ]
            
            dk_file_path = None
            
            # Find the DKSalaries file for this week
            for pattern in possible_paths:
                import glob
                matching_files = glob.glob(pattern)
                if matching_files:
                    dk_file_path = matching_files[0]  # Take the first match
                    break
            
            if not dk_file_path:
                logger.warning(f"No DKSalaries file found for week {week}. Will scrape all players.")
                return
            
            # Load the DKSalaries CSV
            dk_df = pd.read_csv(dk_file_path)
            
            # Extract player names from the 'Name' column (3rd column) and clean them
            if 'Name' in dk_df.columns:
                # Apply name cleaning to all DKSalaries player names
                cleaned_names = dk_df['Name'].apply(lambda x: clean_player_name(str(x).strip()) if pd.notna(x) else "")
                self.dk_salaries_players = set(cleaned_names.tolist())
                
                # Remove any empty names
                self.dk_salaries_players.discard("")
                
                logger.info(f"Loaded {len(self.dk_salaries_players)} players from DKSalaries: {dk_file_path}")
                
                # Log a few sample names for verification
                sample_names = list(self.dk_salaries_players)[:5]
                logger.info(f"Sample DK player names (cleaned): {sample_names}")
            else:
                logger.warning(f"'Name' column not found in {dk_file_path}. Available columns: {dk_df.columns.tolist()}")
                
        except Exception as e:
            logger.warning(f"Failed to load DKSalaries for week {week}: {e}")
            logger.warning("Will scrape all players without filtering.")
    
    def is_player_in_dk_salaries(self, player_name: str) -> bool:
        """
        Check if a player exists in the DraftKings salaries
        
        Args:
            player_name: Name of the player to check
            
        Returns:
            True if player is in DK salaries, False otherwise
        """
        if not self.dk_salaries_players:
            # If no DK data loaded, assume all players are relevant
            return True
        
        # Clean the ESPN player name first
        cleaned_player_name = clean_player_name(player_name)
        
        # Direct match first (cleaned names)
        if cleaned_player_name in self.dk_salaries_players:
            return True
        
        # Try fuzzy matching for additional variations
        player_name_lower = cleaned_player_name.lower().strip()
        
        for dk_name in self.dk_salaries_players:
            dk_name_lower = dk_name.lower().strip()
            
            # Exact match (case insensitive)
            if player_name_lower == dk_name_lower:
                return True
            
            # Handle additional common variations like Jr., Sr., II, III
            # Remove suffixes for comparison
            suffixes = [' jr.', ' sr.', ' ii', ' iii', ' iv', ' jr', ' sr']
            player_clean = player_name_lower
            dk_clean = dk_name_lower
            
            for suffix in suffixes:
                player_clean = player_clean.replace(suffix, '')
                dk_clean = dk_clean.replace(suffix, '')
            
            if player_clean == dk_clean:
                return True
        
        return False
    
    def run_scraper(self, output_file: str = "espn_fantasy_projections.csv", max_pages: int = None, coarse_mode: bool = False, week: int = None):
        """
        Main method to run the complete scraping process
        
        Args:
            output_file: Name of the output CSV file
            max_pages: Maximum number of pages to scrape (None for all pages)
            coarse_mode: If True, use simplified extraction (no clicking). If False, use detailed extraction with popups.
            week: Week number to load DKSalaries for filtering (optional)
        """
        try:
            logger.info("Starting ESPN fantasy projections scraper")
            
            # Load DraftKings salaries for filtering if week is provided
            if week:
                logger.info(f"Loading DKSalaries for week {week} to filter relevant players")
                self.load_dk_salaries(week)
            
            # Setup and navigate directly
            self.setup_driver()
            self.navigate_to_fantasy_page()
            
            # Scrape data
            df = self.scrape_all_players(output_file, max_pages, coarse_mode)
            
            # Save results
            self.save_to_csv(df, output_file)
            
            logger.info("Scraping completed successfully")
            return df
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            raise
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("WebDriver closed")

def main():
    """Main function to run the scraper"""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="Scrape ESPN fantasy projections")
    parser.add_argument("--week", type=int, required=True, help="Week number (e.g., 1, 2, 3)")
    parser.add_argument("--output", "-o", default="espn_fantasy_projections.csv",
                       help="Output CSV filename")
    parser.add_argument("--max-pages", "-m", type=int, default=10,
                       help="Maximum number of pages to scrape (default: 10)")
    parser.add_argument("--mode", choices=["fine", "coarse"], default="fine",
                       help="Analysis mode: 'fine' for detailed extraction with popups (default), 'coarse' for simplified extraction from table rows only")
    
    args = parser.parse_args()
    
    # Create week folder if it doesn't exist
    week_folder = f"2025/WEEK{args.week}"
    os.makedirs(week_folder, exist_ok=True)
    
    # Set output file path to week folder
    output_file = f"{week_folder}/{args.output}"
    
    # Determine analysis mode
    coarse_mode = (args.mode == "coarse")
    
    print(f"Scraping ESPN fantasy projections for Week {args.week}")
    print(f"Analysis mode: {args.mode.upper()}")
    print(f"Output folder: {week_folder}")
    print(f"Output file: {output_file}")
    print(f"Maximum pages to scrape: {args.max_pages}")
    
    if coarse_mode:
        print("Using simplified extraction (projection points only, no boom/bust data)")
    else:
        print("Using detailed extraction (includes boom/bust data from popups)")
    
    scraper = ESPNFantasyScraper()
    df = scraper.run_scraper(output_file, args.max_pages, coarse_mode, args.week)
    
    print(f"Scraped data for {len(df)} players")
    print(f"Data saved to {output_file}")

if __name__ == "__main__":
    main()
