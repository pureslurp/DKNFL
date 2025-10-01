#!/usr/bin/env python3
"""
Home vs Away Performance Analysis

This script analyzes the performance of players at home vs away games
by examining box scores and DraftKings salary data across all weeks.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import warnings
from utils import clean_player_name
warnings.filterwarnings('ignore')

class HomeAwayAnalyzer:
    def __init__(self, base_dir: str = "/Users/seanraymor/Documents/PythonScripts/DKNFL/2025"):
        self.base_dir = Path(base_dir)
        self.weekly_results = {}
        self.overall_results = {}
        
    def extract_home_away(self, game_info: str, team: str) -> str:
        """Extract home/away status from game info"""
        if pd.isna(game_info) or pd.isna(team):
            return ""
        try:
            teams = game_info.split(' ')[0].split('@')
            if len(teams) == 2:
                away_team = teams[0]
                home_team = teams[1]
                return "Away" if team == away_team else "Home"
        except:
            pass
        return ""
    
    def load_week_data(self, week_folder: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load box scores and DraftKings salary data for a week"""
        # Load box scores
        box_score_file = week_folder / "box_score_debug.csv"
        if not box_score_file.exists():
            raise FileNotFoundError(f"No box_score_debug.csv found in {week_folder}")
        
        box_scores_df = pd.read_csv(box_score_file)
        
        # Load DraftKings salary data
        salary_files = list(week_folder.glob("*DKSalaries*.csv"))
        if not salary_files:
            raise FileNotFoundError(f"No DraftKings salary file found in {week_folder}")
        
        salary_df = pd.read_csv(salary_files[0])
        
        return box_scores_df, salary_df
    
    def merge_week_data(self, box_scores_df: pd.DataFrame, salary_df: pd.DataFrame) -> pd.DataFrame:
        """Merge box scores with salary data and add home/away info"""
        # Clean player names for matching using utils function
        box_scores_df['Name_Clean'] = box_scores_df['Name'].apply(clean_player_name)
        salary_df['Name_Clean'] = salary_df['Name'].apply(clean_player_name)
        
        # Merge on clean names
        merged_df = salary_df.merge(
            box_scores_df[['Name_Clean', 'DFS Total']], 
            left_on='Name_Clean', 
            right_on='Name_Clean', 
            how='left'
        )
        
        # Fill missing scores with 0
        merged_df['DFS Total'] = merged_df['DFS Total'].fillna(0)
        
        # Add home/away information
        merged_df['Home_Away'] = merged_df.apply(
            lambda row: self.extract_home_away(row['Game Info'], row['TeamAbbrev']), 
            axis=1
        )
        
        return merged_df
    
    def calculate_position_metrics(self, df: pd.DataFrame) -> Dict:
        """Calculate home vs away metrics by position"""
        metrics = {}
        
        # Filter to only players who actually played (non-zero scores)
        played_df = df[df['DFS Total'] > 0]
        print(f"Analyzing {len(played_df)} players who actually played (out of {len(df)} total)")
        
        # Overall metrics
        home_players = played_df[played_df['Home_Away'] == 'Home']
        away_players = played_df[played_df['Home_Away'] == 'Away']
        
        metrics['overall'] = {
            'home_count': len(home_players),
            'away_count': len(away_players),
            'home_avg_score': home_players['DFS Total'].mean() if len(home_players) > 0 else 0,
            'away_avg_score': away_players['DFS Total'].mean() if len(away_players) > 0 else 0,
            'home_median_score': home_players['DFS Total'].median() if len(home_players) > 0 else 0,
            'away_median_score': away_players['DFS Total'].median() if len(away_players) > 0 else 0,
            'home_std_score': home_players['DFS Total'].std() if len(home_players) > 0 else 0,
            'away_std_score': away_players['DFS Total'].std() if len(away_players) > 0 else 0
        }
        
        # Calculate home advantage
        if metrics['overall']['home_avg_score'] > 0 and metrics['overall']['away_avg_score'] > 0:
            metrics['overall']['home_advantage'] = (
                metrics['overall']['home_avg_score'] - metrics['overall']['away_avg_score']
            )
            metrics['overall']['home_advantage_pct'] = (
                (metrics['overall']['home_avg_score'] - metrics['overall']['away_avg_score']) / 
                metrics['overall']['away_avg_score'] * 100
            )
        else:
            metrics['overall']['home_advantage'] = 0
            metrics['overall']['home_advantage_pct'] = 0
        
        # Position-specific metrics
        for position in played_df['Position'].unique():
            if pd.isna(position):
                continue
                
            pos_df = played_df[played_df['Position'] == position]
            pos_home = pos_df[pos_df['Home_Away'] == 'Home']
            pos_away = pos_df[pos_df['Home_Away'] == 'Away']
            
            metrics[position] = {
                'home_count': len(pos_home),
                'away_count': len(pos_away),
                'home_avg_score': pos_home['DFS Total'].mean() if len(pos_home) > 0 else 0,
                'away_avg_score': pos_away['DFS Total'].mean() if len(pos_away) > 0 else 0,
                'home_median_score': pos_home['DFS Total'].median() if len(pos_home) > 0 else 0,
                'away_median_score': pos_away['DFS Total'].median() if len(pos_away) > 0 else 0,
                'home_std_score': pos_home['DFS Total'].std() if len(pos_home) > 0 else 0,
                'away_std_score': pos_away['DFS Total'].std() if len(pos_away) > 0 else 0
            }
            
            # Calculate home advantage for position
            if metrics[position]['home_avg_score'] > 0 and metrics[position]['away_avg_score'] > 0:
                metrics[position]['home_advantage'] = (
                    metrics[position]['home_avg_score'] - metrics[position]['away_avg_score']
                )
                metrics[position]['home_advantage_pct'] = (
                    (metrics[position]['home_avg_score'] - metrics[position]['away_avg_score']) / 
                    metrics[position]['away_avg_score'] * 100
                )
            else:
                metrics[position]['home_advantage'] = 0
                metrics[position]['home_advantage_pct'] = 0
        
        return metrics
    
    def analyze_week(self, week_folder: Path) -> Dict:
        """Analyze home vs away performance for a single week"""
        try:
            print(f"Analyzing {week_folder.name}...")
            
            # Load data
            box_scores_df, salary_df = self.load_week_data(week_folder)
            
            # Merge data
            merged_df = self.merge_week_data(box_scores_df, salary_df)
            
            # Calculate metrics
            metrics = self.calculate_position_metrics(merged_df)
            
            # Add week info
            metrics['week'] = week_folder.name
            metrics['total_players'] = len(merged_df)
            
            return metrics
            
        except Exception as e:
            print(f"Error analyzing {week_folder.name}: {e}")
            return None
    
    def save_weekly_csv(self, week_folder: Path, metrics: Dict, merged_df: pd.DataFrame):
        """Save weekly home/away analysis to CSV"""
        # Create summary data
        summary_data = []
        for category, data in metrics.items():
            if category == 'week' or category == 'total_players':
                continue
                
            summary_data.append({
                'Category': category,
                'Home_Count': data['home_count'],
                'Away_Count': data['away_count'],
                'Home_Avg_Score': round(data['home_avg_score'], 2),
                'Away_Avg_Score': round(data['away_avg_score'], 2),
                'Home_Median_Score': round(data['home_median_score'], 2),
                'Away_Median_Score': round(data['away_median_score'], 2),
                'Home_Advantage': round(data['home_advantage'], 2),
                'Home_Advantage_Pct': round(data['home_advantage_pct'], 2)
            })
        
        # Save summary data
        summary_df = pd.DataFrame(summary_data)
        summary_output = week_folder / f"home_away_summary_{week_folder.name.lower()}.csv"
        summary_df.to_csv(summary_output, index=False)
        
        print(f"Saved weekly analysis to {week_folder.name}")
        return summary_df
    
    def analyze_all_weeks(self):
        """Analyze home vs away performance for all weeks"""
        print("Starting home vs away analysis...")
        
        # Find all week folders
        week_folders = [f for f in self.base_dir.iterdir() if f.is_dir() and f.name.startswith('WEEK')]
        week_folders.sort()
        
        print(f"Found {len(week_folders)} week folders to analyze")
        
        all_weekly_summaries = []
        
        for week_folder in week_folders:
            try:
                # Load data for this week
                box_scores_df, salary_df = self.load_week_data(week_folder)
                merged_df = self.merge_week_data(box_scores_df, salary_df)
                
                # Analyze week
                metrics = self.analyze_week(week_folder)
                if metrics:
                    # Save weekly CSV
                    summary_df = self.save_weekly_csv(week_folder, metrics, merged_df)
                    
                    # Store for overall analysis
                    self.weekly_results[week_folder.name] = metrics
                    all_weekly_summaries.append(summary_df)
                    
            except Exception as e:
                print(f"Error processing {week_folder.name}: {e}")
                continue
        
        # Create overall summary
        if all_weekly_summaries:
            self.create_overall_summary(all_weekly_summaries)
        
        print(f"\nAnalysis complete! Processed {len(self.weekly_results)} weeks.")
    
    def create_overall_summary(self, all_weekly_summaries: List[pd.DataFrame]):
        """Create overall summary across all weeks"""
        # Combine all weekly summaries
        combined_df = pd.concat(all_weekly_summaries, ignore_index=True)
        
        # Calculate overall metrics by category
        overall_summary = []
        
        for category in combined_df['Category'].unique():
            cat_data = combined_df[combined_df['Category'] == category]
            
            # Aggregate metrics
            total_home_count = cat_data['Home_Count'].sum()
            total_away_count = cat_data['Away_Count'].sum()
            
            # Weighted averages
            home_weighted_avg = (cat_data['Home_Avg_Score'] * cat_data['Home_Count']).sum() / total_home_count if total_home_count > 0 else 0
            away_weighted_avg = (cat_data['Away_Avg_Score'] * cat_data['Away_Count']).sum() / total_away_count if total_away_count > 0 else 0
            
            home_advantage = home_weighted_avg - away_weighted_avg
            home_advantage_pct = (home_advantage / away_weighted_avg * 100) if away_weighted_avg > 0 else 0
            
            overall_summary.append({
                'Category': category,
                'Total_Home_Count': total_home_count,
                'Total_Away_Count': total_away_count,
                'Overall_Home_Avg_Score': round(home_weighted_avg, 2),
                'Overall_Away_Avg_Score': round(away_weighted_avg, 2),
                'Overall_Home_Advantage': round(home_advantage, 2),
                'Overall_Home_Advantage_Pct': round(home_advantage_pct, 2)
            })
        
        # Save overall summary
        overall_df = pd.DataFrame(overall_summary)
        overall_output = self.base_dir / 'home_away_overall_summary.csv'
        overall_df.to_csv(overall_output, index=False)
        
        print(f"Overall summary saved to: {overall_output}")
        
        # Print key insights
        print("\n" + "="*60)
        print("KEY INSIGHTS - HOME vs AWAY PERFORMANCE")
        print("="*60)
        
        for _, row in overall_df.iterrows():
            if row['Category'] == 'overall':
                print(f"\nOVERALL PERFORMANCE:")
                print(f"  Home Players: {row['Total_Home_Count']}")
                print(f"  Away Players: {row['Total_Away_Count']}")
                print(f"  Home Avg Score: {row['Overall_Home_Avg_Score']}")
                print(f"  Away Avg Score: {row['Overall_Away_Avg_Score']}")
                print(f"  Home Advantage: {row['Overall_Home_Advantage']} points ({row['Overall_Home_Advantage_Pct']:.1f}%)")
                break
        
        print(f"\nPOSITION-SPECIFIC INSIGHTS:")
        for _, row in overall_df.iterrows():
            if row['Category'] != 'overall':
                advantage = "Home" if row['Overall_Home_Advantage'] > 0 else "Away"
                print(f"  {row['Category']}: {advantage} advantage ({row['Overall_Home_Advantage']:.2f} pts, {row['Overall_Home_Advantage_Pct']:.1f}%)")

def main():
    analyzer = HomeAwayAnalyzer()
    analyzer.analyze_all_weeks()

if __name__ == "__main__":
    main()
