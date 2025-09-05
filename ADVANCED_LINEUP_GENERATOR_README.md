# Advanced DFS Lineup Generator

A sophisticated DraftKings NFL lineup generator that incorporates learnings from optimal lineup pattern analysis, featuring enhanced stack analysis, team diversity optimization, and risk-adjusted scoring.

## 🎯 Key Features

### Pattern Analysis Integration
- **Optimal Stack Ranges**: Prioritizes QB-WR/TE stacks between $10,000-$15,000 (based on historical analysis)
- **Team Diversity**: Optimizes for 5-7 teams per lineup (optimal range from pattern analysis)
- **FLEX Position Strategy**: Prefers WR in FLEX position but allows RB/TE when appropriate
- **Stack Correlation Scoring**: Evaluates QB-WR vs QB-TE correlation potential

### Enhanced Player Analysis
- **Multi-Score Optimization**: Choose between projected, risk-adjusted, or boom score optimization
- **Risk-Adjusted Scoring**: Incorporates bust, nominal, and boom projections
- **Upside Potential**: Calculates boom score differential for high-ceiling players
- **Value Optimization**: Balances projected points with salary efficiency
- **Boom Percentage Weighting**: Factors in likelihood of boom scenarios
- **Sub-$4000 Requirement**: All lineups must include at least one player ≤$4000 (excluding defense)
### Advanced Lineup Generation
- **4-Stack Strategy**: Uses 4 optimal stacks (2 by projected points, 2 by value) with equal representation
- **Stack-First Approach**: Every lineup starts with an optimal QB-WR/TE stack
- **Quality Scoring System**: Composite score considering multiple factors
- **Team Diversity Scoring**: Rewards optimal team distribution
- **FLEX Position Quality**: Scores based on position preference (WR > RB > TE)
- **Sub-$4000 Enforcement**: All lineups must include at least one value player ≤$4000

## 📊 Pattern Analysis Learnings Incorporated

Based on analysis of 17 weeks of optimal lineups:

- **Stack Performance**: Average stack score of 59.90 points, optimal salary range $10,000-$15,000
- **Team Utilization**: 5-7 teams per lineup is optimal for diversity and correlation
- **Position Spending**: WR (40.8%), RB (30.4%), QB (14.1%), TE (8.7%), DST (6.0%)
- **FLEX Strategy**: WR used 52.9% of the time, RB 23.5%, TE 23.5%
- **Value Ratios**: Average value ratio of 5.15, with 6.0+ being excellent

## 🚀 Usage

### Week-Based Usage (Recommended)
```bash
python advanced_lineup_generator.py --week 1 --num-lineups 20
```

The script will automatically:
- Look for data in `2025/WEEK1/` folder
- Find `espn_fantasy_projections.csv` for projections
- Find `DKSalaries*.csv` for DraftKings salary data
- Save generated lineups to the week folder

### Optimization Strategy Options
```bash
# Optimize by projected score (default)
python advanced_lineup_generator.py --week 1 --num-lineups 20 --optimize-by projected

# Optimize by risk-adjusted score (considering bust/boom scenarios)
python advanced_lineup_generator.py --week 1 --num-lineups 20 --optimize-by risk_adjusted

# Optimize by boom score (maximize ceiling potential)
python advanced_lineup_generator.py --week 1 --num-lineups 20 --optimize-by boom_score
```

### Manual File Specification
```bash
python advanced_lineup_generator.py --week 1 --projections custom_projections.csv --dk-data custom_salaries.csv --num-lineups 20 --output my_lineups.csv --optimize-by projected
```

### Test the Generator
```bash
python demo_lineup_generator.py
```

## 📁 File Structure

```
advanced_lineup_generator.py     # Main lineup generator
demo_lineup_generator.py         # Demo and test script
ADVANCED_LINEUP_GENERATOR_README.md # This documentation

2025/
├── WEEK1/
│   ├── espn_fantasy_projections.csv     # ESPN projections
│   ├── DKSalaries - 2025-08-11T122205.682.csv  # DraftKings salaries
│   └── generated_lineups.csv            # Generated lineups (output)
├── WEEK2/
│   ├── espn_fantasy_projections.csv
│   └── DKSalaries*.csv
└── ...
```

## 🔧 Core Classes

### Player Class
Enhanced player representation with:
- Projected, bust, and boom scores
- Risk-adjusted scoring
- Upside potential calculation
- Team and opponent information

### Stack Class
Advanced stack analysis featuring:
- Stack correlation scoring
- Optimal salary range validation
- Risk-adjusted stack scoring
- QB-WR vs QB-TE differentiation

### LineUp Class
Comprehensive lineup management with:
- Team diversity scoring
- FLEX position quality assessment
- Quality scoring system
- Validation and optimization methods

### AdvancedLineupGenerator Class
Main generator with methods for:
- Optimal stack identification
- Lineup generation from stacks
- Lineup optimization
- Export and analysis

## 📈 Quality Scoring System

The generator uses a composite quality score that adapts based on optimization strategy:

### Primary Score Components:
1. **Primary Score** (65%): Chosen optimization target (projected/risk_adjusted/boom_score)
2. **Salary Utilization Bonus** (15%): Rewards efficient use of salary cap
3. **Salary Efficiency** (5%): Points per dollar ratio based on primary score

### Pattern Analysis Bonuses (15% combined):
4. **Team Diversity** (5%): Optimal team distribution (5-7 teams get full bonus)
5. **FLEX Quality** (5%): Position preference scoring (WR > RB > TE)
6. **Upside Potential** (5%): Boom score differential and percentages

### Validation Requirements:
- Must include at least one player ≤$4000 salary (excluding defense)
- Minimum $48,000 salary utilization (96% of cap)
- Maximum 3 players per team
- 4+ different teams represented

## 🎲 Stack Analysis Features

### Stack Correlation Scoring
- **QB-WR**: Base correlation of 0.8 + boom percentage adjustment
- **QB-TE**: Base correlation of 0.6 + boom percentage adjustment
- **Boom Adjustment**: Higher boom percentages increase correlation potential

### Optimal Stack Criteria
- Salary between $10,000-$15,000
- Same team QB-WR/TE combination
- High projected combined score
- Strong correlation potential

## 🔍 Risk Management

### Risk-Adjusted Scoring
```
Risk_Adjusted = (Bust_Score × Bust%) + (Projected_Score × Nominal%) + (Boom_Score × Boom%)
```

### Upside Potential
```
Upside_Potential = Boom_Score - Projected_Score
```

## 📊 Output Format

Generated lineups are exported to CSV with columns:

### Player Positions:
- QB, RB1, RB2, WR1, WR2, WR3, TE, FLEX, DST

### Scoring Metrics:
- **Salary**: Total lineup salary
- **Projected_Score**: Sum of projected points
- **Risk_Adjusted_Score**: Sum of risk-adjusted points (considering bust/boom scenarios)
- **Boom_Score**: Sum of boom scenario points
- **Bust_Score**: Sum of bust scenario points
- **Avg_Boom_Percentage**: Average boom percentage across all players
- **Avg_Bust_Percentage**: Average bust percentage across all players

### Quality Metrics:
- **Quality_Score**: Composite quality score (based on optimization strategy)
- **Teams**: Number of different teams represented

## 🎯 Strategy Insights

### Stack Strategy
- Focus on QB-WR stacks (20/21 optimal stacks were QB-WR)
- Target salary range $10,000-$15,000
- Prioritize high boom percentage combinations

### Team Diversity
- Aim for 5-7 teams per lineup
- Avoid over-concentration on single teams
- Balance correlation with diversification

### Position Strategy
- WR is preferred FLEX option (52.9% usage)
- RB can be effective FLEX (23.5% usage)
- TE FLEX is viable but less common (23.5% usage)

### Salary Allocation
- WR: ~40% of salary (highest priority)
- RB: ~30% of salary
- QB: ~14% of salary
- TE: ~9% of salary
- DST: ~6% of salary

## 🔧 Customization

### Adjusting Stack Criteria
```python
# Modify stack salary range
optimal_stacks = generator.find_optimal_stacks(
    max_stacks=10,
    min_salary=8000,  # Lower minimum
    max_salary=16000  # Higher maximum
)
```

### Custom Quality Scoring
```python
# Current quality scoring implementation (lines 403-437 in advanced_lineup_generator.py)
def get_quality_score(self, optimize_by: str = "projected") -> float:
    # Choose primary score based on optimization strategy
    if optimize_by == "risk_adjusted":
        primary_score = self.risk_adjusted_score
    elif optimize_by == "boom_score":
        primary_score = self.boom_score if self.boom_score > 0 else self.projected_score
    else:  # default to projected
        primary_score = self.projected_score
    
    # Primary score (65% weight)
    primary_score_weight = primary_score * 0.65
    
    # Salary utilization bonus (15% weight)
    salary_utilization = min(1.0, self.salary / 50000)
    salary_bonus = salary_utilization * 15
    
    # Salary efficiency (5% weight)
    salary_efficiency = (primary_score / self.salary) * 10000 * 0.05
    
    # Pattern analysis bonuses (15% combined)
    diversity_bonus = self.team_diversity_score * 0.05
    flex_bonus = self.flex_position_quality * 0.05
    upside_bonus = self.upside_potential_score * 0.05
    
    return primary_score_weight + salary_bonus + salary_efficiency + diversity_bonus + flex_bonus + upside_bonus
```

## 📈 Performance Metrics

The generator tracks and optimizes for:
- **Average Score**: Target varies by optimization strategy (200+ projected, risk-adjusted, or boom)
- **Salary Utilization**: Minimum $48,000 (96% of cap), targeting full $50,000 utilization
- **Team Diversity**: Target 5-7 teams per lineup (optimal range)
- **Stack Performance**: Target 50+ combined stack points in optimal $10-15K range
- **Sub-$4000 Requirement**: Every lineup must include at least one player ≤$4000 (excluding defense)
- **Quality Score**: Composite metric adapting to chosen optimization strategy

## 🚨 Requirements

### Python Dependencies:
- Python 3.7+
- pandas
- numpy
- tqdm

### Data Requirements:
**ESPN projections CSV** with required columns:
- `player_name`, `team`, `position`, `opponent`
- `projected_points` or `projected_score` (for basic scoring)
- `bust_score`, `boom_score` (optional, for advanced scoring)
- `bust_percentage`, `boom_percentage` (optional, for risk analysis)

**DraftKings salary CSV** with columns:
- `Name`, `Position`, `Salary`, `Name + ID`, `Game Info`

### Optimization Strategy Notes:
- **projected**: Works with basic or advanced data
- **risk_adjusted**: Requires bust/boom data; falls back to projected if unavailable
- **boom_score**: Requires boom data; falls back to projected if unavailable

## 📝 Example Output

```
================================================================================
LINEUP GENERATION SUMMARY
================================================================================
Total Lineups: 20
Average Projected Score: 215.34
Average Salary: $47,892
Average Team Diversity: 6.2
Average Quality Score: 0.847

================================================================================
TOP 5 LINEUPS
================================================================================

1. Lineup(Score=228.45, Salary=$48,200, Teams=6)
   QB: Josh Allen (Buf)
   RB: Saquon Barkley (Phi) | Jahmyr Gibbs (Det)
   WR: Ja'Marr Chase (Cin) | Justin Jefferson (Min) | CeeDee Lamb (Dal)
   TE: Brock Bowers (LV)
   FLEX: Amon-Ra St. Brown (Det) - WR
   DST: Broncos D/ST (Den)
   Score: 228.45 | Salary: $48,200 | Teams: 6 | Quality: 0.892
```

## 🔄 Future Enhancements

- **Game Theory Integration**: Consider ownership projections
- **Weather Impact**: Factor in weather conditions
- **Injury Adjustments**: Real-time injury updates
- **Advanced Correlation**: Historical QB-WR performance data
- **Multi-Stack Support**: Multiple stacks per lineup
- **Tournament vs Cash**: Different strategies for different contest types
- **Position-Specific Optimization**: Different optimization strategies by position
- **Stack Correlation Modeling**: Dynamic correlation adjustments based on game script
