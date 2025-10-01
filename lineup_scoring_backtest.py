#!/usr/bin/env python3
"""
Backtesting Script for Lineup Scoring Methods

This script analyzes which scoring attribute from advanced_lineup_generator 
(Projected_Score, Risk_Adjusted_Score, or Boom_Score) best correlates with 
actual DFS results at the lineup level.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import re
from scipy.stats import pearsonr, spearmanr, beta
from typing import Dict, List, Tuple, Optional
from itertools import combinations
import warnings
from utils import clean_player_name
warnings.filterwarnings('ignore')

class LineupScoringBacktest:
    def __init__(self, base_dir: str = "/Users/seanraymor/Documents/PythonScripts/DKNFL/2025"):
        self.base_dir = Path(base_dir)
        self.results = []
        
    
    def load_week_data(self, week_folder: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load generated lineups and actual scores for a week"""
        
        # Load generated lineups
        lineups_file = week_folder / "generated_lineups.csv"
        if not lineups_file.exists():
            raise FileNotFoundError(f"No generated_lineups.csv found in {week_folder}")
        
        lineups_df = pd.read_csv(lineups_file)
        
        # Load actual scores
        actual_file = week_folder / "box_score_debug.csv"
        if not actual_file.exists():
            raise FileNotFoundError(f"No box_score_debug.csv found in {week_folder}")
        
        actual_df = pd.read_csv(actual_file)
        actual_df['Name_Clean'] = actual_df['Name'].apply(clean_player_name)
        
        return lineups_df, actual_df
    
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
    
    def extract_player_names_from_lineup(self, lineup_row: pd.Series) -> List[str]:
        """Extract clean player names from a lineup row"""
        positions = ['QB', 'RB1', 'RB2', 'WR1', 'WR2', 'WR3', 'TE', 'FLEX', 'DST']
        players = []
        
        for pos in positions:
            if pos in lineup_row:
                player_name = clean_player_name(lineup_row[pos])
                if player_name:
                    players.append(player_name)
        
        return players
    
    def calculate_actual_lineup_score(self, players: List[str], actual_df: pd.DataFrame) -> float:
        """Calculate actual DFS score for a lineup"""
        total_score = 0.0
        matched_players = 0
        
        for player in players:
            # Try exact match first
            matches = actual_df[actual_df['Name_Clean'] == player]
            
            # If no exact match, try partial matching
            if matches.empty:
                # Look for player name within the actual names
                matches = actual_df[actual_df['Name_Clean'].str.contains(player, case=False, na=False)]
                
                # If still no match, try the other way around
                if matches.empty:
                    for _, row in actual_df.iterrows():
                        if player.lower() in row['Name_Clean'].lower() or row['Name_Clean'].lower() in player.lower():
                            matches = pd.DataFrame([row])
                            break
            
            if not matches.empty:
                # Take the first match if multiple found
                player_score = matches.iloc[0]['DFS Total']
                if pd.notna(player_score):
                    total_score += float(player_score)
                    matched_players += 1
        
        # Return score only if we matched most players (at least 7 out of 9)
        if matched_players >= 7:
            return total_score
        else:
            return np.nan
    
    def analyze_week(self, week_folder: Path) -> Dict:
        """Analyze correlation for a single week"""
        try:
            lineups_df, actual_df = self.load_week_data(week_folder)
            
            week_results = {
                'week': week_folder.name,
                'total_lineups': len(lineups_df),
                'successful_matches': 0,
                'projected_correlation': np.nan,
                'risk_adjusted_correlation': np.nan,
                'boom_correlation': np.nan,
                'quality_correlation': np.nan,
                'projected_spearman': np.nan,
                'risk_adjusted_spearman': np.nan,
                'boom_spearman': np.nan,
                'quality_spearman': np.nan
            }
            
            # Calculate actual scores for each lineup
            actual_scores = []
            projected_scores = []
            risk_adjusted_scores = []
            boom_scores = []
            quality_scores = []
            
            for idx, lineup in lineups_df.iterrows():
                players = self.extract_player_names_from_lineup(lineup)
                actual_score = self.calculate_actual_lineup_score(players, actual_df)
                
                if not np.isnan(actual_score):
                    actual_scores.append(actual_score)
                    projected_scores.append(lineup['Projected_Score'])
                    risk_adjusted_scores.append(lineup['Risk_Adjusted_Score'])
                    boom_scores.append(lineup['Boom_Score'])
                    quality_scores.append(lineup['Quality_Score'])
            
            week_results['successful_matches'] = len(actual_scores)
            
            if len(actual_scores) >= 5:  # Need at least 5 successful matches for meaningful correlation
                # Calculate Pearson correlations
                proj_corr, _ = pearsonr(projected_scores, actual_scores)
                risk_corr, _ = pearsonr(risk_adjusted_scores, actual_scores)
                boom_corr, _ = pearsonr(boom_scores, actual_scores)
                quality_corr, _ = pearsonr(quality_scores, actual_scores)
                
                # Calculate Spearman correlations (rank-based)
                proj_spear, _ = spearmanr(projected_scores, actual_scores)
                risk_spear, _ = spearmanr(risk_adjusted_scores, actual_scores)
                boom_spear, _ = spearmanr(boom_scores, actual_scores)
                quality_spear, _ = spearmanr(quality_scores, actual_scores)
                
                week_results.update({
                    'projected_correlation': proj_corr,
                    'risk_adjusted_correlation': risk_corr,
                    'boom_correlation': boom_corr,
                    'quality_correlation': quality_corr,
                    'projected_spearman': proj_spear,
                    'risk_adjusted_spearman': risk_spear,
                    'boom_spearman': boom_spear,
                    'quality_spearman': quality_spear,
                    'actual_scores': actual_scores,
                    'projected_scores': projected_scores,
                    'risk_adjusted_scores': risk_adjusted_scores,
                    'boom_scores': boom_scores,
                    'quality_scores': quality_scores
                })
            
            return week_results
            
        except Exception as e:
            print(f"Error analyzing {week_folder}: {e}")
            return {
                'week': week_folder.name,
                'error': str(e),
                'total_lineups': 0,
                'successful_matches': 0
            }
    
    def run_backtest(self) -> pd.DataFrame:
        """Run backtest across all available weeks"""
        week_folders = [d for d in self.base_dir.iterdir() if d.is_dir() and d.name.startswith('WEEK')]
        week_folders.sort()
        
        print(f"Found {len(week_folders)} week folders to analyze...")
        
        for week_folder in week_folders:
            print(f"Analyzing {week_folder.name}...")
            week_result = self.analyze_week(week_folder)
            self.results.append(week_result)
        
        return pd.DataFrame(self.results)
    
    def generate_report(self, results_df: pd.DataFrame):
        """Generate comprehensive analysis report"""
        
        print("\n" + "="*60)
        print("LINEUP SCORING BACKTEST RESULTS")
        print("="*60)
        
        # Filter out weeks with errors or insufficient data
        valid_results = results_df[
            (results_df['successful_matches'] >= 5) & 
            (~results_df['projected_correlation'].isna())
        ]
        
        if len(valid_results) == 0:
            print("No valid results found. Check data quality and player name matching.")
            return
        
        print(f"\nValid weeks analyzed: {len(valid_results)}")
        print(f"Total weeks attempted: {len(results_df)}")
        
        # Calculate average correlations
        metrics = ['projected', 'risk_adjusted', 'boom', 'quality']
        correlations = {}
        spearman_correlations = {}
        
        for metric in metrics:
            pearson_col = f'{metric}_correlation'
            spearman_col = f'{metric}_spearman'
            
            correlations[metric] = valid_results[pearson_col].mean()
            spearman_correlations[metric] = valid_results[spearman_col].mean()
        
        # Display results
        print("\n" + "-"*40)
        print("AVERAGE PEARSON CORRELATIONS:")
        print("-"*40)
        for metric in metrics:
            print(f"{metric.replace('_', ' ').title():15}: {correlations[metric]:.4f}")
        
        print("\n" + "-"*40)
        print("AVERAGE SPEARMAN CORRELATIONS:")
        print("-"*40)
        for metric in metrics:
            print(f"{metric.replace('_', ' ').title():15}: {spearman_correlations[metric]:.4f}")
        
        # Find best performing metric
        best_pearson = max(correlations.items(), key=lambda x: x[1])
        best_spearman = max(spearman_correlations.items(), key=lambda x: x[1])
        
        print(f"\n" + "="*40)
        print("SUMMARY:")
        print("="*40)
        print(f"Best Pearson Correlation:  {best_pearson[0].replace('_', ' ').title()} ({best_pearson[1]:.4f})")
        print(f"Best Spearman Correlation: {best_spearman[0].replace('_', ' ').title()} ({best_spearman[1]:.4f})")
        
        # Week-by-week breakdown
        print(f"\n" + "-"*60)
        print("WEEK-BY-WEEK BREAKDOWN:")
        print("-"*60)
        print(f"{'Week':<8} {'Lineups':<8} {'Matched':<8} {'Proj':<8} {'Risk':<8} {'Boom':<8} {'Quality':<8}")
        print("-"*68)
        
        for _, row in valid_results.iterrows():
            print(f"{row['week']:<8} {row['total_lineups']:<8} {row['successful_matches']:<8} "
                  f"{row['projected_correlation']:<8.3f} {row['risk_adjusted_correlation']:<8.3f} "
                  f"{row['boom_correlation']:<8.3f} {row['quality_correlation']:<8.3f}")
    
    def create_visualizations(self, results_df: pd.DataFrame):
        """Create correlation visualizations"""
        
        valid_results = results_df[
            (results_df['successful_matches'] >= 5) & 
            (~results_df['projected_correlation'].isna())
        ]
        
        if len(valid_results) == 0:
            print("No valid results for visualization.")
            return
        
        # Set up the plotting style
        plt.style.use('seaborn-v0_8' if 'seaborn-v0_8' in plt.style.available else 'default')
        
        # Create correlation comparison plot
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Lineup Scoring Method Correlation Analysis', fontsize=16, fontweight='bold')
        
        # 1. Correlation by week
        ax1 = axes[0, 0]
        weeks = valid_results['week'].values
        x_pos = range(len(weeks))
        
        ax1.plot(x_pos, valid_results['projected_correlation'], 'o-', label='Projected Score', linewidth=2, markersize=6)
        ax1.plot(x_pos, valid_results['risk_adjusted_correlation'], 's-', label='Risk Adjusted', linewidth=2, markersize=6)
        ax1.plot(x_pos, valid_results['boom_correlation'], '^-', label='Boom Score', linewidth=2, markersize=6)
        ax1.plot(x_pos, valid_results['quality_correlation'], 'd-', label='Quality Score', linewidth=2, markersize=6)
        
        ax1.set_title('Correlation by Week (Pearson)', fontweight='bold')
        ax1.set_xlabel('Week')
        ax1.set_ylabel('Correlation Coefficient')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(weeks, rotation=45)
        
        # 2. Average correlations bar chart
        ax2 = axes[0, 1]
        methods = ['Projected', 'Risk Adjusted', 'Boom', 'Quality']
        pearson_avgs = [
            valid_results['projected_correlation'].mean(),
            valid_results['risk_adjusted_correlation'].mean(),
            valid_results['boom_correlation'].mean(),
            valid_results['quality_correlation'].mean()
        ]
        spearman_avgs = [
            valid_results['projected_spearman'].mean(),
            valid_results['risk_adjusted_spearman'].mean(),
            valid_results['boom_spearman'].mean(),
            valid_results['quality_spearman'].mean()
        ]
        
        x = np.arange(len(methods))
        width = 0.35
        
        ax2.bar(x - width/2, pearson_avgs, width, label='Pearson', alpha=0.8)
        ax2.bar(x + width/2, spearman_avgs, width, label='Spearman', alpha=0.8)
        
        ax2.set_title('Average Correlations', fontweight='bold')
        ax2.set_ylabel('Correlation Coefficient')
        ax2.set_xticks(x)
        ax2.set_xticklabels(methods)
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for i, (p, s) in enumerate(zip(pearson_avgs, spearman_avgs)):
            ax2.text(i - width/2, p + 0.01, f'{p:.3f}', ha='center', va='bottom', fontsize=9)
            ax2.text(i + width/2, s + 0.01, f'{s:.3f}', ha='center', va='bottom', fontsize=9)
        
        # 3. Scatter plot for best week
        if len(valid_results) > 0:
            # Find week with highest projected correlation for detailed view
            best_week_idx = valid_results['projected_correlation'].idxmax()
            best_week_data = valid_results.loc[best_week_idx]
            
            if 'actual_scores' in best_week_data and best_week_data['actual_scores'] is not None:
                ax3 = axes[1, 0]
                
                actual = best_week_data['actual_scores']
                projected = best_week_data['projected_scores']
                
                ax3.scatter(projected, actual, alpha=0.6, s=50)
                ax3.plot([min(projected), max(projected)], [min(actual), max(actual)], 'r--', alpha=0.5)
                
                corr_val = best_week_data['projected_correlation']
                ax3.set_title(f'Projected vs Actual - {best_week_data["week"]}\n(r = {corr_val:.3f})', fontweight='bold')
                ax3.set_xlabel('Projected Score')
                ax3.set_ylabel('Actual Score')
                ax3.grid(True, alpha=0.3)
        
        # 4. Distribution of correlations
        ax4 = axes[1, 1]
        
        data_to_plot = [
            valid_results['projected_correlation'].dropna(),
            valid_results['risk_adjusted_correlation'].dropna(),
            valid_results['boom_correlation'].dropna(),
            valid_results['quality_correlation'].dropna()
        ]
        
        ax4.boxplot(data_to_plot, labels=['Projected', 'Risk Adj.', 'Boom', 'Quality'])
        ax4.set_title('Distribution of Correlations', fontweight='bold')
        ax4.set_ylabel('Correlation Coefficient')
        ax4.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        # Save the plot
        output_file = self.base_dir.parent / 'lineup_scoring_correlation_analysis.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"\nVisualization saved to: {output_file}")
        
        plt.show()
    
    def find_optimal_stacks(self, merged_df: pd.DataFrame, min_salary: int = 10000, max_salary: int = 15000) -> List[Dict]:
        """Find optimal QB-WR/TE stacks based on actual scores"""
        stacks = []
        
        # Get players by position
        qbs = merged_df[merged_df['Position'] == 'QB'].to_dict('records')
        wrs = merged_df[merged_df['Position'] == 'WR'].to_dict('records')
        tes = merged_df[merged_df['Position'] == 'TE'].to_dict('records')
        
        # Create all possible QB-WR combinations (same team)
        for qb in qbs:
            for wr in wrs:
                if qb.get('TeamAbbrev') == wr.get('TeamAbbrev'):  # Same team stack
                    stack_salary = qb['Salary'] + wr['Salary']
                    if min_salary <= stack_salary <= max_salary:
                        stack_score = qb['DFS Total'] + wr['DFS Total']
                        stacks.append({
                            'qb': qb,
                            'pass_catcher': wr,
                            'salary': stack_salary,
                            'actual_score': stack_score,
                            'type': 'QB-WR'
                        })
        
        # Create QB-TE combinations (same team)
        for qb in qbs:
            for te in tes:
                if qb.get('TeamAbbrev') == te.get('TeamAbbrev'):  # Same team stack
                    stack_salary = qb['Salary'] + te['Salary']
                    if min_salary <= stack_salary <= max_salary:
                        stack_score = qb['DFS Total'] + te['DFS Total']
                        stacks.append({
                            'qb': qb,
                            'pass_catcher': te,
                            'salary': stack_salary,
                            'actual_score': stack_score,
                            'type': 'QB-TE'
                        })
        
        # Sort by actual score and return top stacks
        stacks.sort(key=lambda x: x['actual_score'], reverse=True)
        return stacks[:20]  # Return top 20 stacks for optimization

    def find_optimal_lineup(self, week_folder: Path, salary_cap: int = 50000) -> Dict:
        """Find the optimal lineup based on actual scores using stack strategy"""
        try:
            # Load data
            _, actual_df = self.load_week_data(week_folder)
            
            # Load salary data - check for DraftKings salary file
            salary_files = list(week_folder.glob("*DKSalaries*.csv"))
            if not salary_files:
                print(f"No DraftKings salary file found in {week_folder}")
                return {"error": "No salary file found"}
            
            salary_df = pd.read_csv(salary_files[0])
            
            # Clean up the data and merge
            actual_df['Name_Clean'] = actual_df['Name'].apply(clean_player_name)
            salary_df['Name_Clean'] = salary_df['Name'].apply(clean_player_name)
            
            # Merge actual scores with salary data
            merged_df = salary_df.merge(actual_df[['Name_Clean', 'DFS Total']], 
                                      left_on='Name_Clean', right_on='Name_Clean', how='left')
            
            # Fill missing scores with 0
            merged_df['DFS Total'] = merged_df['DFS Total'].fillna(0)
            
            print(f"Finding optimal stack-based lineup for {week_folder.name}...")
            
            # Find optimal stacks
            optimal_stacks = self.find_optimal_stacks(merged_df)
            if not optimal_stacks:
                print("No valid stacks found, falling back to non-stack optimization")
                return self.find_optimal_lineup_no_stack(week_folder, salary_cap)
            
            print(f"Found {len(optimal_stacks)} viable stacks, optimizing lineups...")
            
            # Group by position for remaining players
            position_groups = merged_df.groupby('Position')
            available_players = {}
            for pos, group in position_groups:
                available_players[pos] = group.sort_values('DFS Total', ascending=False).to_dict('records')
            
            rb_options = available_players.get('RB', [])[:15]  # Top 15 RBs
            wr_options = available_players.get('WR', [])[:20]  # Top 20 WRs
            te_options = available_players.get('TE', [])[:10]  # Top 10 TEs
            dst_options = available_players.get('DST', [])[:8]  # Top 8 DSTs
            
            # Flex options (additional RB/WR/TE)
            flex_options = (rb_options + wr_options + te_options)
            flex_options.sort(key=lambda x: x['DFS Total'], reverse=True)
            flex_options = flex_options[:25]  # Top 25 flex options
            
            best_lineup = None
            best_score = 0
            iteration_count = 0
            max_iterations = 30000
            
            # Try each stack
            for stack in optimal_stacks[:10]:  # Try top 10 stacks
                qb = stack['qb']
                pass_catcher = stack['pass_catcher']
                stack_salary = stack['salary']
                remaining_salary = salary_cap - stack_salary
                
                # Filter out players already in stack
                excluded_names = {qb['Name_Clean'], pass_catcher['Name_Clean']}
                
                available_rbs = [p for p in rb_options if p['Name_Clean'] not in excluded_names]
                available_wrs = [p for p in wr_options if p['Name_Clean'] not in excluded_names]
                available_tes = [p for p in te_options if p['Name_Clean'] not in excluded_names]
                available_flex = [p for p in flex_options if p['Name_Clean'] not in excluded_names]
                
                # Determine remaining position needs
                if pass_catcher['Position'] == 'WR':
                    # Need 2 more WRs, 1 TE
                    needed_wrs = 2
                    needed_tes = 1
                else:  # pass_catcher is TE
                    # Need 3 WRs, no additional TE
                    needed_wrs = 3
                    needed_tes = 0
                
                # Try combinations for this stack
                for rb_combo in combinations(available_rbs, 2):
                    if sum(p['Salary'] for p in rb_combo) > remaining_salary - 15000:  # Leave room for other positions
                        continue
                        
                    for wr_combo in combinations(available_wrs, needed_wrs):
                        if needed_tes > 0:
                            for te in available_tes:
                                for dst in dst_options:
                                    for flex in available_flex:
                                        iteration_count += 1
                                        if iteration_count > max_iterations:
                                            break
                                        
                                        # Create lineup
                                        if pass_catcher['Position'] == 'WR':
                                            lineup_players = [qb, rb_combo[0], rb_combo[1], 
                                                            pass_catcher, wr_combo[0], wr_combo[1],
                                                            te, flex, dst]
                                        else:  # pass_catcher is TE
                                            lineup_players = [qb, rb_combo[0], rb_combo[1], 
                                                            wr_combo[0], wr_combo[1], wr_combo[2],
                                                            pass_catcher, flex, dst]
                                        
                                        # Check for duplicates
                                        player_names = [p['Name_Clean'] for p in lineup_players]
                                        if len(set(player_names)) != len(player_names):
                                            continue
                                        
                                        # Check salary cap
                                        total_salary = sum(p['Salary'] for p in lineup_players)
                                        if total_salary > salary_cap:
                                            continue
                                        
                                        # Calculate total score
                                        total_score = sum(p['DFS Total'] for p in lineup_players)
                                        
                                        if total_score > best_score:
                                            best_score = total_score
                                            if pass_catcher['Position'] == 'WR':
                                                best_lineup = {
                                                    'QB': qb,
                                                    'RB1': rb_combo[0],
                                                    'RB2': rb_combo[1],
                                                    'WR1': pass_catcher,  # Stack WR
                                                    'WR2': wr_combo[0],
                                                    'WR3': wr_combo[1],
                                                    'TE': te,
                                                    'FLEX': flex,
                                                    'DST': dst,
                                                    'total_score': total_score,
                                                    'total_salary': total_salary,
                                                    'players': lineup_players,
                                                    'stack': f"{qb['Name']} + {pass_catcher['Name']} ({stack['type']})"
                                                }
                                            else:  # TE stack
                                                best_lineup = {
                                                    'QB': qb,
                                                    'RB1': rb_combo[0],
                                                    'RB2': rb_combo[1],
                                                    'WR1': wr_combo[0],
                                                    'WR2': wr_combo[1],
                                                    'WR3': wr_combo[2],
                                                    'TE': pass_catcher,  # Stack TE
                                                    'FLEX': flex,
                                                    'DST': dst,
                                                    'total_score': total_score,
                                                    'total_salary': total_salary,
                                                    'players': lineup_players,
                                                    'stack': f"{qb['Name']} + {pass_catcher['Name']} ({stack['type']})"
                                                }
                                    
                                    if iteration_count > max_iterations:
                                        break
                                if iteration_count > max_iterations:
                                    break
                            if iteration_count > max_iterations:
                                break
                        else:
                            # No TE needed (pass_catcher is TE), different loop structure
                            for dst in dst_options:
                                for flex in available_flex:
                                    iteration_count += 1
                                    if iteration_count > max_iterations:
                                        break
                                    
                                    # Create lineup (pass_catcher is TE)
                                    lineup_players = [qb, rb_combo[0], rb_combo[1], 
                                                    wr_combo[0], wr_combo[1], wr_combo[2],
                                                    pass_catcher, flex, dst]
                                    
                                    # Check for duplicates
                                    player_names = [p['Name_Clean'] for p in lineup_players]
                                    if len(set(player_names)) != len(player_names):
                                        continue
                                    
                                    # Check salary cap
                                    total_salary = sum(p['Salary'] for p in lineup_players)
                                    if total_salary > salary_cap:
                                        continue
                                    
                                    # Calculate total score
                                    total_score = sum(p['DFS Total'] for p in lineup_players)
                                    
                                    if total_score > best_score:
                                        best_score = total_score
                                        best_lineup = {
                                            'QB': qb,
                                            'RB1': rb_combo[0],
                                            'RB2': rb_combo[1],
                                            'WR1': wr_combo[0],
                                            'WR2': wr_combo[1],
                                            'WR3': wr_combo[2],
                                            'TE': pass_catcher,  # Stack TE
                                            'FLEX': flex,
                                            'DST': dst,
                                            'total_score': total_score,
                                            'total_salary': total_salary,
                                            'players': lineup_players,
                                            'stack': f"{qb['Name']} + {pass_catcher['Name']} ({stack['type']})"
                                        }
                                
                                if iteration_count > max_iterations:
                                    break
                            if iteration_count > max_iterations:
                                break
                        if iteration_count > max_iterations:
                            break
                    if iteration_count > max_iterations:
                        break
                if iteration_count > max_iterations:
                    break
            
            if best_lineup:
                print(f"Optimal stack-based lineup found with {best_score:.2f} points using ${best_lineup['total_salary']:,}")
                print(f"Stack: {best_lineup['stack']}")
                return {
                    'week': week_folder.name,
                    'optimal_score': best_score,
                    'optimal_salary': best_lineup['total_salary'],
                    'lineup': best_lineup,
                    'iterations_checked': iteration_count
                }
            else:
                return {
                    'week': week_folder.name,
                    'error': 'No valid stack-based lineup found',
                    'iterations_checked': iteration_count
                }
                
        except Exception as e:
            print(f"Error finding optimal stack-based lineup for {week_folder}: {e}")
            return {
                'week': week_folder.name,
                'error': str(e)
            }

    def find_optimal_lineup_no_stack(self, week_folder: Path, salary_cap: int = 50000) -> Dict:
        """Fallback method: Find optimal lineup without stack strategy"""
        # This is the original non-stack method (shortened for brevity)
        return {
            'week': week_folder.name,
            'error': 'No stack optimization available, implement fallback if needed'
        }
    
    def save_optimal_lineup_csv(self, week_folder: Path, optimal_lineup: Dict):
        """Save optimal lineup to CSV in the week folder"""
        try:
            # Create lineup data for CSV
            lineup_data = []
            positions = ['QB', 'RB1', 'RB2', 'WR1', 'WR2', 'WR3', 'TE', 'FLEX', 'DST']
            
            for pos in positions:
                if pos in optimal_lineup:
                    player = optimal_lineup[pos]
                    # Extract home/away from Game Info if available
                    home_away = ""
                    if 'Game Info' in player:
                        home_away = self.extract_home_away(player['Game Info'], player.get('TeamAbbrev', ''))
                    
                    lineup_data.append({
                        'Position': pos,
                        'Player_Name': player['Name'],
                        'Team': player.get('TeamAbbrev', 'N/A'),
                        'Home_Away': home_away,
                        'Salary': player['Salary'],
                        'Actual_Points': player['DFS Total'],
                        'Points_Per_Dollar': (player['DFS Total'] / player['Salary']) * 1000 if player['Salary'] > 0 else 0
                    })
            
            # Add summary row
            lineup_data.append({
                'Position': 'TOTAL',
                'Player_Name': f"Stack: {optimal_lineup.get('stack', 'No stack')}",
                'Team': f"{len(set(p.get('TeamAbbrev', 'N/A') for p in [optimal_lineup[pos] for pos in positions if pos in optimal_lineup]))} teams",
                'Home_Away': '',
                'Salary': optimal_lineup['total_salary'],
                'Actual_Points': optimal_lineup['total_score'],
                'Points_Per_Dollar': (optimal_lineup['total_score'] / optimal_lineup['total_salary']) * 1000
            })
            
            # Create DataFrame and save
            df = pd.DataFrame(lineup_data)
            output_file = week_folder / f"optimal_lineup_{week_folder.name.lower()}.csv"
            df.to_csv(output_file, index=False)
            
            print(f"Optimal lineup saved to: {output_file}")
            
        except Exception as e:
            print(f"Error saving optimal lineup CSV: {e}")

    def estimate_placement_from_score(self, actual_score: float, optimal_score: float, total_entries: int = 85350) -> int:
        """
        Estimate DraftKings placement based on actual score and optimal score.
        
        Uses real Week 2 data points for calibration:
        - 249.3 points (89.1% optimal) = 1st place
        - 211 points (75.4% optimal) = ~208th place
        - 188 points (67.2% optimal) = ~2,783rd place
        - Bottom payout (55% optimal) = ~85,350th place
        """
        if np.isnan(actual_score) or actual_score <= 0:
            return total_entries  # Last place if no valid score
        
        # Calculate percentage of optimal score
        score_pct = actual_score / optimal_score
        
        # Define key data points from real DraftKings results
        # (score_percentage, placement)
        calibration_points = [
            (0.891, 1),        # 1st place: 249.3 / 279.66 = 89.1%
            (0.754, 208),      # Your 211-point lineup
            (0.672, 2783),     # Your 188-point lineup
            (0.550, 85350)     # Bottom payout threshold (55% optimal)
        ]
        
        # If score is better than 1st place calibration point, extrapolate
        if score_pct >= calibration_points[0][0]:
            # Linear extrapolation for scores above 1st place
            # Assume top 1% of scores are very tightly packed
            excess_pct = (score_pct - calibration_points[0][0]) / (1.0 - calibration_points[0][0])
            return max(1, int(1 + excess_pct * 0))  # Stay at 1st place for scores >= 89.1%
        
        # If score is worse than bottom payout, place at bottom
        if score_pct <= calibration_points[-1][0]:
            return total_entries
        
        # Interpolate between calibration points
        for i in range(len(calibration_points) - 1):
            upper_score, upper_place = calibration_points[i]
            lower_score, lower_place = calibration_points[i + 1]
            
            if lower_score <= score_pct <= upper_score:
                # Use exponential interpolation to handle the non-linear spacing
                # Convert to log space for more realistic distribution
                if upper_place == lower_place:
                    return upper_place
                
                # Calculate position within this range
                range_pct = (score_pct - lower_score) / (upper_score - lower_score)
                
                # Use exponential interpolation for more realistic placement distribution
                # Higher scores have exponentially better placements
                log_upper = np.log(upper_place + 1)
                log_lower = np.log(lower_place + 1)
                log_interpolated = log_lower + range_pct * (log_upper - log_lower)
                estimated_place = int(np.exp(log_interpolated) - 1)
                
                return max(1, min(estimated_place, total_entries))
        
        # Fallback (shouldn't reach here with proper calibration points)
        return total_entries

    def get_optimal_score_for_week(self, week_folder: Path) -> float:
        """Get the optimal score from the optimal lineup CSV file"""
        try:
            optimal_file = week_folder / f"optimal_lineup_{week_folder.name.lower()}.csv"
            if optimal_file.exists():
                optimal_df = pd.read_csv(optimal_file)
                # Look for the total row
                total_row = optimal_df[optimal_df['Position'] == 'TOTAL']
                if not total_row.empty:
                    return float(total_row.iloc[0]['Actual_Points'])
            
            # Fallback: calculate optimal lineup if file doesn't exist
            optimal_result = self.find_optimal_lineup(week_folder)
            if 'error' not in optimal_result:
                return optimal_result['optimal_score']
                
        except Exception as e:
            print(f"Error getting optimal score for {week_folder}: {e}")
        
        # Final fallback: return a reasonable estimate
        return 300.0  # Typical high DFS score

    def create_actual_scoring_csv(self, week_folder: Path) -> str:
        """Create a CSV file with actual scoring for generated lineups"""
        try:
            lineups_df, actual_df = self.load_week_data(week_folder)
            
            # Get optimal score for payout calculations
            optimal_score = self.get_optimal_score_for_week(week_folder)
            print(f"Using optimal score of {optimal_score:.2f} for payout calculations")
            
            # Prepare data for the output CSV
            scoring_data = []
            
            for idx, lineup in lineups_df.iterrows():
                # Extract player names from lineup
                players = self.extract_player_names_from_lineup(lineup)
                
                # Calculate actual score for this lineup
                actual_score = self.calculate_actual_lineup_score(players, actual_df)
                
                # Calculate projected placement and payout
                if not np.isnan(actual_score) and actual_score > 0:
                    estimated_place = self.estimate_placement_from_score(actual_score, optimal_score)
                    projected_payout = draftkings_payout(estimated_place)
                else:
                    estimated_place = 85350  # Last place
                    projected_payout = 0
                
                # Create row with lineup info and actual score
                row_data = {
                    'Lineup_ID': idx + 1,
                    'QB': lineup.get('QB', ''),
                    'RB1': lineup.get('RB1', ''),
                    'RB2': lineup.get('RB2', ''),
                    'WR1': lineup.get('WR1', ''),
                    'WR2': lineup.get('WR2', ''),
                    'WR3': lineup.get('WR3', ''),
                    'TE': lineup.get('TE', ''),
                    'FLEX': lineup.get('FLEX', ''),
                    'DST': lineup.get('DST', ''),
                    'Salary': lineup.get('Salary', 0),
                    'Projected_Score': lineup.get('Projected_Score', 0),
                    'Risk_Adjusted_Score': lineup.get('Risk_Adjusted_Score', 0),
                    'Boom_Score': lineup.get('Boom_Score', 0),
                    'Quality_Score': lineup.get('Quality_Score', 0),
                    'Actual_Score': actual_score if not np.isnan(actual_score) else 0,
                    'Score_Difference': (actual_score - lineup.get('Projected_Score', 0)) if not np.isnan(actual_score) else np.nan,
                    'Actual_vs_Projected_Pct': ((actual_score / lineup.get('Projected_Score', 1)) * 100) if not np.isnan(actual_score) and lineup.get('Projected_Score', 0) > 0 else np.nan,
                    'Estimated_Placement': estimated_place,
                    'Projected_Payout': projected_payout,
                    'Score_vs_Optimal_Pct': ((actual_score / optimal_score) * 100) if not np.isnan(actual_score) and optimal_score > 0 else 0
                }
                
                # Add individual player actual scores if we can match them
                player_scores = {}
                positions = ['QB', 'RB1', 'RB2', 'WR1', 'WR2', 'WR3', 'TE', 'FLEX', 'DST']
                
                for pos in positions:
                    if pos in lineup and lineup[pos]:
                        player_name = clean_player_name(lineup[pos])
                        if player_name:
                            # Try to find this player's actual score
                            matches = actual_df[actual_df['Name_Clean'] == player_name]
                            if matches.empty:
                                matches = actual_df[actual_df['Name_Clean'].str.contains(player_name, case=False, na=False)]
                            
                            if not matches.empty:
                                player_score = matches.iloc[0]['DFS Total']
                                if pd.notna(player_score):
                                    player_scores[f'{pos}_Actual_Score'] = float(player_score)
                                else:
                                    player_scores[f'{pos}_Actual_Score'] = 0
                            else:
                                player_scores[f'{pos}_Actual_Score'] = 0
                        else:
                            player_scores[f'{pos}_Actual_Score'] = 0
                
                # Add player scores to row data
                row_data.update(player_scores)
                
                scoring_data.append(row_data)
            
            # Create DataFrame
            scoring_df = pd.DataFrame(scoring_data)
            
            # Sort by actual score descending to show best lineups first
            scoring_df = scoring_df.sort_values('Actual_Score', ascending=False).reset_index(drop=True)
            
            # Save to CSV
            output_file = week_folder / f"generated_lineups_actual_scoring_{week_folder.name.lower()}.csv"
            scoring_df.to_csv(output_file, index=False)
            
            # Print summary statistics
            total_payout = scoring_df['Projected_Payout'].sum()
            avg_payout = scoring_df['Projected_Payout'].mean()
            paying_lineups = len(scoring_df[scoring_df['Projected_Payout'] > 0])
            
            print(f"Generated lineups with actual scoring saved to: {output_file}")
            print(f"Payout Summary: {paying_lineups}/{len(scoring_df)} lineups projected to pay (${total_payout:,} total, ${avg_payout:.2f} avg)")
            return str(output_file)
            
        except Exception as e:
            error_msg = f"Error creating actual scoring CSV for {week_folder}: {e}"
            print(error_msg)
            return error_msg

    def get_payout_stats_for_week(self, week_folder: Path) -> Dict:
        """Get payout statistics from the generated lineups actual scoring CSV"""
        try:
            csv_file = week_folder / f"generated_lineups_actual_scoring_{week_folder.name.lower()}.csv"
            if not csv_file.exists():
                return None
                
            df = pd.read_csv(csv_file)
            
            if 'Projected_Payout' not in df.columns:
                return None
            
            total_payout = df['Projected_Payout'].sum()
            avg_payout = df['Projected_Payout'].mean()
            paying_lineups = len(df[df['Projected_Payout'] > 0])
            total_lineups = len(df)
            
            # Get best performing lineup
            best_lineup = df.loc[df['Projected_Payout'].idxmax()]
            best_payout = best_lineup['Projected_Payout']
            best_placement = best_lineup['Estimated_Placement']
            
            return {
                'total_payout': int(total_payout),
                'avg_payout': avg_payout,
                'paying_lineups': paying_lineups,
                'total_lineups': total_lineups,
                'best_payout': int(best_payout),
                'best_placement': int(best_placement)
            }
            
        except Exception as e:
            print(f"Error getting payout stats for {week_folder}: {e}")
            return None

    def compare_generated_vs_optimal(self, week_folder: Path) -> Dict:
        """Compare generated lineups against the optimal lineup"""
        try:
            # Get optimal lineup
            optimal_result = self.find_optimal_lineup(week_folder)
            if 'error' in optimal_result:
                return optimal_result
            
            # Save optimal lineup to CSV in week folder
            self.save_optimal_lineup_csv(week_folder, optimal_result['lineup'])
            
            # Load generated lineups and calculate their actual scores
            week_data = self.analyze_week(week_folder)
            if 'error' in week_data or 'actual_scores' not in week_data:
                return {'error': 'Could not analyze generated lineups'}
            
            actual_scores = week_data['actual_scores']
            best_generated_score = max(actual_scores)
            avg_generated_score = np.mean(actual_scores)
            
            optimal_score = optimal_result['optimal_score']
            
            # Calculate performance metrics
            best_vs_optimal = (best_generated_score / optimal_score) * 100
            avg_vs_optimal = (avg_generated_score / optimal_score) * 100
            
            return {
                'week': week_folder.name,
                'optimal_score': optimal_score,
                'best_generated_score': best_generated_score,
                'avg_generated_score': avg_generated_score,
                'best_vs_optimal_pct': best_vs_optimal,
                'avg_vs_optimal_pct': avg_vs_optimal,
                'score_gap': optimal_score - best_generated_score,
                'avg_score_gap': optimal_score - avg_generated_score,
                'optimal_lineup': optimal_result['lineup']
            }
            
        except Exception as e:
            return {
                'week': week_folder.name,
                'error': f'Comparison failed: {str(e)}'
            }

    def compare_stack_generation_methods(self, week_folder: Path) -> Dict:
        """Compare projected points vs boom score for stack generation using existing AdvancedLineupGenerator"""
        try:
            # Import the AdvancedLineupGenerator to reuse its stack generation logic
            from advanced_lineup_generator import AdvancedLineupGenerator
            
            # Load the required data files
            espn_file = week_folder / "espn_fantasy_projections.csv"
            if not espn_file.exists():
                return {"error": "No ESPN projections file found"}
            
            projections_df = pd.read_csv(espn_file)
            
            # Find DraftKings salary file
            dk_files = list(week_folder.glob("*DKSalaries*.csv"))
            dk_data = None
            if dk_files:
                dk_data = pd.read_csv(dk_files[0])
            
            # Initialize generator with required data
            generator = AdvancedLineupGenerator(projections_df, dk_data, str(week_folder))
            
            # Generate stacks using projected points method (default)
            generator.optimize_by = "projected_score"
            projected_stacks = generator.find_optimal_stacks()
            
            # Generate stacks using boom score method
            generator.optimize_by = "boom_score"  
            boom_stacks = generator.find_optimal_stacks()
            
            if not projected_stacks or not boom_stacks:
                return {"error": "No valid stacks found"}
            
            # Load actual scores to calculate performance
            _, actual_df = self.load_week_data(week_folder)
            actual_df['Name_Clean'] = actual_df['Name'].apply(clean_player_name)
            
            def calculate_stack_actual_score(stack):
                """Calculate actual DFS score for a stack"""
                qb_name = clean_player_name(stack.qb.name)
                wrte_name = clean_player_name(stack.wrte.name)
                
                qb_score = 0
                wrte_score = 0
                
                # Find QB actual score
                qb_matches = actual_df[actual_df['Name_Clean'] == qb_name]
                if not qb_matches.empty:
                    qb_score = qb_matches.iloc[0]['DFS Total']
                
                # Find WR/TE actual score  
                wrte_matches = actual_df[actual_df['Name_Clean'] == wrte_name]
                if not wrte_matches.empty:
                    wrte_score = wrte_matches.iloc[0]['DFS Total']
                
                return qb_score + wrte_score
            
            def get_player_actual_score(player_name):
                """Get actual DFS score for a single player"""
                clean_name = clean_player_name(player_name)
                matches = actual_df[actual_df['Name_Clean'] == clean_name]
                if not matches.empty:
                    return matches.iloc[0]['DFS Total']
                return 0
            
            # Calculate actual scores for both methods
            projected_actual_scores = [calculate_stack_actual_score(stack) for stack in projected_stacks]
            boom_actual_scores = [calculate_stack_actual_score(stack) for stack in boom_stacks]
            
            # Calculate metrics
            projected_avg_actual = np.mean(projected_actual_scores)
            boom_avg_actual = np.mean(boom_actual_scores)
            projected_best_actual = max(projected_actual_scores)
            boom_best_actual = max(boom_actual_scores)
            
            # Print detailed breakdown of top stacks
            print(f"\nTop 4 Projected Stacks for {week_folder.name}:")
            for i, (stack, score) in enumerate(zip(projected_stacks, projected_actual_scores)):
                qb_actual = get_player_actual_score(stack.qb.name)
                wrte_actual = get_player_actual_score(stack.wrte.name)
                print(f"  {i+1}. {stack.qb.name} + {stack.wrte.name} ({score:.2f} pts)")
                print(f"     QB: {stack.qb.projected_score:.2f} proj, {stack.qb.boom_score:.2f} boom, {qb_actual:.2f} actual")
                print(f"     {stack.wrte.position}: {stack.wrte.projected_score:.2f} proj, {stack.wrte.boom_score:.2f} boom, {wrte_actual:.2f} actual")
                print(f"     Stack: {stack.projected_score:.2f} proj total, {stack.boom_score:.2f} boom total")
                print(f"     Salary: ${stack.salary:,.0f}")
            
            print(f"\nTop 4 Boom Stacks for {week_folder.name}:")
            for i, (stack, score) in enumerate(zip(boom_stacks, boom_actual_scores)):
                qb_actual = get_player_actual_score(stack.qb.name)
                wrte_actual = get_player_actual_score(stack.wrte.name)
                print(f"  {i+1}. {stack.qb.name} + {stack.wrte.name} ({score:.2f} pts)")
                print(f"     QB: {stack.qb.projected_score:.2f} proj, {stack.qb.boom_score:.2f} boom, {qb_actual:.2f} actual")
                print(f"     {stack.wrte.position}: {stack.wrte.projected_score:.2f} proj, {stack.wrte.boom_score:.2f} boom, {wrte_actual:.2f} actual")
                print(f"     Stack: {stack.projected_score:.2f} proj total, {stack.boom_score:.2f} boom total")
                print(f"     Salary: ${stack.salary:,.0f}")
            
            return {
                'week': week_folder.name,
                'projected_method': {
                    'avg_actual_score': projected_avg_actual,
                    'best_actual_score': projected_best_actual,
                    'top_stacks': [{'qb': stack.qb.name, 'wrte': stack.wrte.name, 'actual_score': score} 
                                 for stack, score in zip(projected_stacks, projected_actual_scores)]
                },
                'boom_method': {
                    'avg_actual_score': boom_avg_actual,
                    'best_actual_score': boom_best_actual,
                    'top_stacks': [{'qb': stack.qb.name, 'wrte': stack.wrte.name, 'actual_score': score} 
                                 for stack, score in zip(boom_stacks, boom_actual_scores)]
                },
                'winner': 'projected' if projected_avg_actual > boom_avg_actual else 'boom',
                'avg_score_difference': abs(projected_avg_actual - boom_avg_actual),
                'best_score_difference': abs(projected_best_actual - boom_best_actual)
            }
            
        except Exception as e:
            return {
                'week': week_folder.name,
                'error': f'Stack comparison failed: {str(e)}'
            }

def generate_actual_scoring_csv_for_week(week_name: str, base_dir: str = "/Users/seanraymor/Documents/PythonScripts/DKNFL/2025") -> str:
    """Standalone function to generate actual scoring CSV for a specific week"""
    backtest = LineupScoringBacktest(base_dir)
    week_folder = Path(base_dir) / week_name
    
    if not week_folder.exists():
        error_msg = f"Week folder {week_folder} does not exist"
        print(error_msg)
        return error_msg
    
    return backtest.create_actual_scoring_csv(week_folder)

def main():
    """Main execution function"""
    
    # Initialize and run backtest
    backtest = LineupScoringBacktest()
    
    print("Starting lineup scoring backtest...")
    results_df = backtest.run_backtest()
    
    # Generate report
    backtest.generate_report(results_df)
    
    # Create visualizations
    backtest.create_visualizations(results_df)
    
    # Save detailed results
    output_file = backtest.base_dir.parent / 'lineup_scoring_backtest_results.csv'
    results_df.to_csv(output_file, index=False)
    print(f"\nDetailed results saved to: {output_file}")
    
    # Generate actual scoring CSVs for all weeks
    print("\n" + "="*60)
    print("GENERATING ACTUAL SCORING CSVs")
    print("="*60)
    
    week_folders = [d for d in backtest.base_dir.iterdir() if d.is_dir() and d.name.startswith('WEEK')]
    week_folders.sort()
    
    for week_folder in week_folders:
        print(f"\nGenerating actual scoring CSV for {week_folder.name}...")
        try:
            csv_file = backtest.create_actual_scoring_csv(week_folder)
            print(f"Success: {csv_file}")
        except Exception as e:
            print(f"Error: {e}")
    
    # Find optimal lineups and compare
    print("\n" + "="*60)
    print("OPTIMAL LINEUP ANALYSIS")
    print("="*60)
    
    comparison_results = []
    stack_comparison_results = []
    for week_folder in week_folders:
        print(f"\nAnalyzing optimal lineup for {week_folder.name}...")
        comparison = backtest.compare_generated_vs_optimal(week_folder)
        comparison_results.append(comparison)
        
        # Compare stack generation methods
        print(f"Comparing stack generation methods for {week_folder.name}...")
        stack_comparison = backtest.compare_stack_generation_methods(week_folder)
        stack_comparison_results.append(stack_comparison)
        
        if 'error' not in comparison:
            print(f"Optimal Score: {comparison['optimal_score']:.2f}")
            print(f"Best Generated: {comparison['best_generated_score']:.2f} ({comparison['best_vs_optimal_pct']:.1f}% of optimal)")
            print(f"Avg Generated: {comparison['avg_generated_score']:.2f} ({comparison['avg_vs_optimal_pct']:.1f}% of optimal)")
            print(f"Score Gap: {comparison['score_gap']:.2f} points from optimal")
            
            # Get payout stats for this week
            try:
                payout_stats = backtest.get_payout_stats_for_week(week_folder)
                if payout_stats:
                    print(f"Projected Payout: ${payout_stats['total_payout']:,} total, ${payout_stats['avg_payout']:.2f} avg ({payout_stats['paying_lineups']}/{payout_stats['total_lineups']} lineups pay)")
                    print(f"Best Payout: ${payout_stats['best_payout']:,} (place {payout_stats['best_placement']:,})")
            except Exception as e:
                print(f"Payout calculation error: {e}")
            
            # Display optimal lineup
            optimal_lineup = comparison['optimal_lineup']
            stack_info = optimal_lineup.get('stack', 'No stack identified')
            print(f"\nOptimal Lineup ({optimal_lineup['total_score']:.2f} pts, ${optimal_lineup['total_salary']:,}):")
            print(f"Stack: {stack_info}")
            print(f"  QB:   {optimal_lineup['QB']['Name']:<20} ({optimal_lineup['QB'].get('TeamAbbrev', 'N/A'):<3}) ${optimal_lineup['QB']['Salary']:>5,} ({optimal_lineup['QB']['DFS Total']:>5.1f} pts)")
            print(f"  RB1:  {optimal_lineup['RB1']['Name']:<20} ({optimal_lineup['RB1'].get('TeamAbbrev', 'N/A'):<3}) ${optimal_lineup['RB1']['Salary']:>5,} ({optimal_lineup['RB1']['DFS Total']:>5.1f} pts)")
            print(f"  RB2:  {optimal_lineup['RB2']['Name']:<20} ({optimal_lineup['RB2'].get('TeamAbbrev', 'N/A'):<3}) ${optimal_lineup['RB2']['Salary']:>5,} ({optimal_lineup['RB2']['DFS Total']:>5.1f} pts)")
            print(f"  WR1:  {optimal_lineup['WR1']['Name']:<20} ({optimal_lineup['WR1'].get('TeamAbbrev', 'N/A'):<3}) ${optimal_lineup['WR1']['Salary']:>5,} ({optimal_lineup['WR1']['DFS Total']:>5.1f} pts)")
            print(f"  WR2:  {optimal_lineup['WR2']['Name']:<20} ({optimal_lineup['WR2'].get('TeamAbbrev', 'N/A'):<3}) ${optimal_lineup['WR2']['Salary']:>5,} ({optimal_lineup['WR2']['DFS Total']:>5.1f} pts)")
            print(f"  WR3:  {optimal_lineup['WR3']['Name']:<20} ({optimal_lineup['WR3'].get('TeamAbbrev', 'N/A'):<3}) ${optimal_lineup['WR3']['Salary']:>5,} ({optimal_lineup['WR3']['DFS Total']:>5.1f} pts)")
            print(f"  TE:   {optimal_lineup['TE']['Name']:<20} ({optimal_lineup['TE'].get('TeamAbbrev', 'N/A'):<3}) ${optimal_lineup['TE']['Salary']:>5,} ({optimal_lineup['TE']['DFS Total']:>5.1f} pts)")
            print(f"  FLEX: {optimal_lineup['FLEX']['Name']:<20} ({optimal_lineup['FLEX'].get('TeamAbbrev', 'N/A'):<3}) ${optimal_lineup['FLEX']['Salary']:>5,} ({optimal_lineup['FLEX']['DFS Total']:>5.1f} pts)")
            print(f"  DST:  {optimal_lineup['DST']['Name']:<20} ({optimal_lineup['DST'].get('TeamAbbrev', 'N/A'):<3}) ${optimal_lineup['DST']['Salary']:>5,} ({optimal_lineup['DST']['DFS Total']:>5.1f} pts)")
        else:
            print(f"Error: {comparison.get('error', 'Unknown error')}")
        
        # Display stack comparison results
        if 'error' not in stack_comparison:
            print(f"\nStack Generation Comparison for {week_folder.name}:")
            print(f"  Projected Points Method: Avg {stack_comparison['projected_method']['avg_actual_score']:.2f} pts, Best {stack_comparison['projected_method']['best_actual_score']:.2f} pts")
            print(f"  Boom Score Method:        Avg {stack_comparison['boom_method']['avg_actual_score']:.2f} pts, Best {stack_comparison['boom_method']['best_actual_score']:.2f} pts")
            print(f"  Winner: {stack_comparison['winner'].title()} Method (by {stack_comparison['avg_score_difference']:.2f} pts avg)")
        else:
            print(f"Stack comparison error: {stack_comparison.get('error', 'Unknown error')}")
    
    # Save comparison results
    if comparison_results:
        comparison_df = pd.DataFrame(comparison_results)
        comparison_output = backtest.base_dir.parent / 'optimal_lineup_comparison.csv'
        comparison_df.to_csv(comparison_output, index=False)
        print(f"\nOptimal lineup comparison saved to: {comparison_output}")
    
    # Generate stack comparison summary
    if stack_comparison_results:
        print("\n" + "="*60)
        print("STACK GENERATION METHOD COMPARISON SUMMARY")
        print("="*60)
        
        # Filter out weeks with errors
        valid_stack_comparisons = [sc for sc in stack_comparison_results if 'error' not in sc]
        
        if valid_stack_comparisons:
            # Calculate overall statistics
            projected_wins = sum(1 for sc in valid_stack_comparisons if sc['winner'] == 'projected')
            boom_wins = sum(1 for sc in valid_stack_comparisons if sc['winner'] == 'boom')
            
            projected_avg_scores = [sc['projected_method']['avg_actual_score'] for sc in valid_stack_comparisons]
            boom_avg_scores = [sc['boom_method']['avg_actual_score'] for sc in valid_stack_comparisons]
            
            projected_best_scores = [sc['projected_method']['best_actual_score'] for sc in valid_stack_comparisons]
            boom_best_scores = [sc['boom_method']['best_actual_score'] for sc in valid_stack_comparisons]
            
            print(f"Weeks analyzed: {len(valid_stack_comparisons)}")
            print(f"Projected Points Method wins: {projected_wins}")
            print(f"Boom Score Method wins: {boom_wins}")
            print(f"Projected Points Method - Avg: {np.mean(projected_avg_scores):.2f} pts, Best: {np.mean(projected_best_scores):.2f} pts")
            print(f"Boom Score Method - Avg: {np.mean(boom_avg_scores):.2f} pts, Best: {np.mean(boom_best_scores):.2f} pts")
            
            # Determine overall winner
            overall_winner = "Projected Points" if np.mean(projected_avg_scores) > np.mean(boom_avg_scores) else "Boom Score"
            avg_difference = abs(np.mean(projected_avg_scores) - np.mean(boom_avg_scores))
            
            print(f"\n🏆 OVERALL WINNER: {overall_winner} Method")
            print(f"   Average difference: {avg_difference:.2f} points per week")
            
            # Save stack comparison results
            stack_comparison_df = pd.DataFrame(stack_comparison_results)
            stack_output = backtest.base_dir.parent / 'stack_generation_comparison.csv'
            stack_comparison_df.to_csv(stack_output, index=False)
            print(f"\nStack generation comparison saved to: {stack_output}")
        else:
            print("No valid stack comparison data available.")

def draftkings_payout(place: int) -> int:
    """
    Returns the DraftKings payout based on finishing place.
    Payout structure comes from the provided contest screenshots.
    """
    payout_structure = [
        (1, 1, 80000),
        (2, 2, 40000),
        (3, 3, 20000),
        (4, 5, 10000),
        (6, 10, 5000),
        (11, 20, 2000),
        (21, 50, 1000),
        (51, 100, 400),
        (101, 150, 200),
        (151, 225, 150),
        (226, 350, 100),
        (351, 550, 75),
        (551, 850, 50),
        (851, 1500, 30),
        (1501, 2750, 20),
        (2751, 4750, 15),
        (4751, 7750, 12),
        (7751, 12500, 10),
        (12501, 21000, 8),
        (21001, 39000, 6),
        (39001, 85350, 5),
    ]

    for low, high, prize in payout_structure:
        if low <= place <= high:
            return prize

    return 0  # no payout if outside paid places


if __name__ == "__main__":
    main()
