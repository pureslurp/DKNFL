#!/usr/bin/env python3
"""
Test script for the improved optimal lineup analysis - Multiple Weeks
"""

import sys
import os
import glob
import csv
import json
from pathlib import Path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from optimal_lineup_analysis import OptimalLineupAnalyzer

def find_weeks_with_box_scores():
    """Find all weeks that have box_score_debug.csv files"""
    data_path = Path("2024")
    weeks_with_scores = []
    
    for week_dir in sorted(data_path.glob("WEEK*")):
        week_num = int(week_dir.name.replace("WEEK", ""))
        box_score_file = week_dir / "box_score_debug.csv"
        
        if box_score_file.exists():
            weeks_with_scores.append(week_num)
            print(f"✅ Week {week_num}: box_score_debug.csv found")
        else:
            print(f"❌ Week {week_num}: box_score_debug.csv missing")
    
    return sorted(weeks_with_scores)

def save_lineups_to_csv(results, filename="optimal_lineups_summary.csv"):
    """Save all optimal lineups to a CSV file"""
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = [
            'Week', 'Player_Name', 'Position', 'Team', 'Opponent', 
            'Salary', 'Actual_Score', 'Value_Ratio', 'Is_Flex'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for week, lineup in results.items():
            for player in lineup.players:
                # Determine if this player is the FLEX
                is_flex = (player == lineup.flex)
                
                writer.writerow({
                    'Week': week,
                    'Player_Name': player.name,
                    'Position': player.position,
                    'Team': player.team,
                    'Opponent': player.opponent,
                    'Salary': player.salary,
                    'Actual_Score': player.actual_score,
                    'Value_Ratio': player.value_ratio,
                    'Is_Flex': is_flex
                })
    
    print(f"💾 Lineup data saved to: {filename}")

def save_weekly_summary_to_csv(results, filename="weekly_summary.csv"):
    """Save weekly summary statistics to a CSV file"""
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = [
            'Week', 'Total_Score', 'Total_Salary', 'Salary_Utilization_Pct',
            'Team_Count', 'Stack_Count', 'Defense_Conflict'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for week, lineup in results.items():
            utilization = (lineup.total_salary / 50000) * 100
            writer.writerow({
                'Week': week,
                'Total_Score': lineup.total_score,
                'Total_Salary': lineup.total_salary,
                'Salary_Utilization_Pct': utilization,
                'Team_Count': lineup.team_count,
                'Stack_Count': lineup.stack_count,
                'Defense_Conflict': lineup.defense_opponent_conflict
            })
    
    print(f"💾 Weekly summary saved to: {filename}")

def analyze_flex_positions(results):
    """Analyze FLEX position usage patterns"""
    flex_positions = []
    flex_players = []
    
    for week, lineup in results.items():
        flex_player = lineup.flex
        if flex_player:
            flex_positions.append(flex_player.position)
            flex_players.append({
                'week': week,
                'name': flex_player.name,
                'position': flex_player.position,
                'team': flex_player.team,
                'salary': flex_player.salary,
                'score': flex_player.actual_score,
                'value_ratio': flex_player.value_ratio
            })
    
    if not flex_positions:
        return None
    
    # Count position frequency
    from collections import Counter
    position_counts = Counter(flex_positions)
    
    return {
        'position_counts': dict(position_counts),
        'most_common_position': position_counts.most_common(1)[0] if position_counts else None,
        'flex_players': flex_players,
        'total_flex_players': len(flex_players)
    }

def test_multiple_weeks():
    """Test optimal lineup analysis for all weeks with box score data"""
    print("=== Multi-Week Optimal Lineup Analysis ===\n")
    
    analyzer = OptimalLineupAnalyzer("2024")
    
    # Find weeks with box score data
    weeks_with_scores = find_weeks_with_box_scores()
    
    if not weeks_with_scores:
        print("❌ No weeks found with box_score_debug.csv files!")
        return False
    
    print(f"\n🎯 Analyzing {len(weeks_with_scores)} weeks with actual score data...\n")
    
    results = {}
    total_score = 0
    total_salary = 0
    
    for week in weeks_with_scores:
        print(f"📊 {'='*60}")
        print(f"📊 WEEK {week} ANALYSIS")
        print(f"📊 {'='*60}")
        
        try:
            optimal = analyzer.analyze_week(week)
            
            if optimal:
                results[week] = optimal
                total_score += optimal.total_score
                total_salary += optimal.total_salary
                
                print(f"\n🎉 OPTIMAL LINEUP FOUND FOR WEEK {week}")
                print("=" * 60)
                print(f"Total Score: {optimal.total_score:.2f} points")
                print(f"Total Salary: ${optimal.total_salary:,}")
                print(f"Salary Utilization: {(optimal.total_salary/50000)*100:.1f}%")
                print(f"Team Diversity: {optimal.team_count} unique teams")
                print(f"Stack Count: {optimal.stack_count}")
                
                if optimal.defense_opponent_conflict:
                    print("⚠️  WARNING: Defense playing against lineup player")
                else:
                    print("✅ No defense conflicts")
                
                print("\nDETAILED LINEUP BREAKDOWN")
                print("=" * 60)
                print(f"{'Position':<8} | {'Player Name':<25} | {'Team':<4} | {'Score':<6} | {'Salary':<8} | {'Value Ratio':<12} | {'FLEX':<5}")
                print("-" * 85)
                
                for player in optimal.players:
                    is_flex = (player == optimal.flex)
                    flex_indicator = "✓" if is_flex else ""
                    print(f"{player.position:<8} | {player.name:<25} | {player.team:<4} | {player.actual_score:<6.2f} | ${player.salary:<7,} | {player.value_ratio:<12.2f} | {flex_indicator:<5}")
                
                print(f"\n💰 POSITION SPENDING BREAKDOWN:")
                print("-" * 40)
                spending = optimal.position_spending
                for pos, salary in spending.items():
                    percentage = (salary / optimal.total_salary) * 100
                    print(f"{pos:<8}: ${salary:>6,} ({percentage:>5.1f}%)")
                
                if optimal.all_stacks:
                    print(f"\n📊 STACK ANALYSIS:")
                    print("-" * 40)
                    for qb, wr_te in optimal.all_stacks:
                        combined_score = qb.actual_score + wr_te.actual_score
                        combined_salary = qb.salary + wr_te.salary
                        stack_value = (combined_score / combined_salary) * 1000
                        print(f"Stack: {qb.name} + {wr_te.name}")
                        print(f"  Combined Score: {combined_score:.2f} points")
                        print(f"  Combined Salary: ${combined_salary:,}")
                        print(f"  Stack Value Ratio: {stack_value:.2f}")
                
                print(f"\n🏈 TEAMS IN LINEUP:")
                print("-" * 40)
                team_counts = {}
                for player in optimal.players:
                    team_counts[player.team] = team_counts.get(player.team, 0) + 1
                
                for team, count in sorted(team_counts.items()):
                    print(f"{team}: {count} player{'s' if count > 1 else ''}")
                
            else:
                print(f"❌ No valid lineup found for Week {week}")
                
        except Exception as e:
            print(f"❌ Error analyzing Week {week}: {e}")
        
        print("\n" + "="*60 + "\n")
    
    # Summary
    if results:
        print(f"📈 SUMMARY ACROSS {len(results)} WEEKS")
        print("=" * 60)
        print(f"Total Combined Score: {total_score:.2f} points")
        print(f"Average Score per Week: {total_score/len(results):.2f} points")
        print(f"Total Combined Salary: ${total_salary:,}")
        print(f"Average Salary per Week: ${total_salary/len(results):,.0f}")
        
        print(f"\n📊 WEEK-BY-WEEK BREAKDOWN:")
        print("-" * 60)
        print(f"{'Week':<6} | {'Score':<8} | {'Salary':<10} | {'Utilization':<12} | {'Teams':<6} | {'Stacks':<7}")
        print("-" * 60)
        
        for week in sorted(results.keys()):
            lineup = results[week]
            utilization = (lineup.total_salary / 50000) * 100
            print(f"{week:<6} | {lineup.total_score:<8.2f} | ${lineup.total_salary:<9,} | {utilization:<12.1f}% | {lineup.team_count:<6} | {lineup.stack_count:<7}")
        
        # Analyze FLEX positions
        print(f"\n🎯 FLEX POSITION ANALYSIS:")
        print("-" * 40)
        flex_analysis = analyze_flex_positions(results)
        if flex_analysis:
            print(f"Total FLEX players analyzed: {flex_analysis['total_flex_players']}")
            print("FLEX Position Distribution:")
            for pos, count in flex_analysis['position_counts'].items():
                percentage = (count / flex_analysis['total_flex_players']) * 100
                print(f"  {pos}: {count} times ({percentage:.1f}%)")
            
            if flex_analysis['most_common_position']:
                pos, count = flex_analysis['most_common_position']
                print(f"\nMost common FLEX position: {pos} ({count} times)")
        else:
            print("No FLEX position data available")
        
        # Generate comprehensive pattern analysis
        print("\n" + "="*80)
        print("🔍 GENERATING COMPREHENSIVE PATTERN ANALYSIS...")
        print("="*80)
        
        analyzer = OptimalLineupAnalyzer("2024")
        pattern_analysis = analyzer.analyze_lineup_patterns_across_weeks(results)
        
        # Add FLEX analysis to pattern analysis
        if flex_analysis:
            pattern_analysis['flex_analysis'] = flex_analysis
        
        pattern_report = analyzer.generate_pattern_analysis_report(pattern_analysis)
        
        print(pattern_report)
        
        # Save the pattern analysis to a file
        with open("optimal_lineup_pattern_analysis.txt", "w") as f:
            f.write(pattern_report)
        print(f"\n💾 Pattern analysis saved to: optimal_lineup_pattern_analysis.txt")
        
        # Save lineups to CSV
        save_lineups_to_csv(results)
        save_weekly_summary_to_csv(results)
        
        return True
    else:
        print("❌ No valid lineups found for any week!")
        return False

def main():
    """Main test function"""
    print("Starting multi-week optimal lineup analysis...")
    success = test_multiple_weeks()
    
    if success:
        print("\n✅ Multi-week analysis completed successfully!")
        print("📁 Check the following files for detailed results:")
        print("   - optimal_lineups_summary.csv (detailed player data)")
        print("   - weekly_summary.csv (weekly statistics)")
        print("   - optimal_lineup_pattern_analysis.txt (pattern analysis)")
    else:
        print("\n❌ Multi-week analysis failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 