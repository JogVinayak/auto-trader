# RSI W-Pattern / M-Pattern Strategy

## Overview

The RSI W-Pattern and M-Pattern strategy detects bullish and bearish reversal patterns in the Relative Strength Index (RSI) indicator.

### W-Pattern (Bullish Reversal)
- Forms when RSI creates a **double bottom** in oversold territory (below threshold, default 30)
- Second bottom must be **equal to or higher** than the first bottom (within tolerance)
- **BUY signal** triggers when RSI breaks above the middle peak between the two bottoms
- Indicates weakening selling pressure and potential bullish reversal

### M-Pattern (Bearish Reversal)
- Forms when RSI creates a **double top** in overbought territory (above threshold, default 70)
- Second top must be **equal to or lower** than the first top (within tolerance)
- **SELL signal** triggers when RSI breaks below the middle valley between the two tops
- Indicates weakening buying pressure and potential bearish reversal

## Strategy Parameters

All parameters can be adjusted via the UI Settings Modal or API:

| Parameter | Default | Min | Max | Step | Description |
|-----------|---------|-----|-----|------|-------------|
| **rsi_period** | 14 | 5 | 30 | 1 | Period for RSI calculation |
| **oversold_threshold** | 30 | 20 | 40 | 1 | RSI level below which to detect W-patterns |
| **overbought_threshold** | 70 | 60 | 80 | 1 | RSI level above which to detect M-patterns |
| **min_distance** | 3 | 2 | 10 | 1 | Minimum candles between pattern points |
| **max_distance** | 10 | 5 | 30 | 1 | Maximum candles between pattern points |
| **tolerance** | 3.0 | 1 | 10 | 0.5 | RSI point tolerance for pattern validation |

## Installation & Setup

### 1. Database Migration

The strategy requires database schema updates. Run the migration script:

```bash
cd stock-auto-trader/backend
python3 migrate_rsi_w_pattern.py
```

This will:
- Add `RSI_W_PATTERN` to the PostgreSQL `strategytype` enum
- Add 6 new columns to the `strategy_settings` table
- Verify all changes were applied successfully

### 2. Restart Backend

After migration, restart your backend server:

```bash
cd stock-auto-trader/backend
python3 main.py
# or
uvicorn main:app --reload
```

### 3. Frontend (Already Updated)

The frontend components have been updated to support the new strategy:
- Strategy card displays with 📐 icon
- Settings modal includes all 6 configurable parameters
- Chart displays RSI with custom thresholds

## Usage

### Via Web UI

1. **View Signals**
   - The RSI W-Pattern strategy appears alongside other strategies in the dashboard
   - Shows current signal (BUY/SELL/HOLD), strength, and reason

2. **Customize Settings**
   - Click the settings icon on any strategy card
   - Select "RSI W PATTERN" from the dropdown
   - Adjust parameters using sliders
   - Click "Save Settings" to apply

3. **Chart Visualization**
   - RSI indicator is displayed in a separate panel below the price chart
   - Oversold and overbought threshold lines show your custom levels
   - Pattern detection is highlighted in the signal description

### Via API

#### Get Signals
```bash
# Get all strategies including RSI W-Pattern
curl "http://localhost:8000/signals/RELIANCE.NS?timeframe=1d"

# Get only RSI W-Pattern signals
curl "http://localhost:8000/signals/RELIANCE.NS?strategy=RSI_W_PATTERN&timeframe=1d"
```

**Response Example:**
```json
{
  "symbol": "RELIANCE.NS",
  "timeframe": "1d",
  "current_price": 2456.30,
  "signals": [
    {
      "strategy": "RSI_W_PATTERN",
      "signal": "BUY",
      "strength": 85,
      "reason": "W-Pattern confirmed: RSI broke above middle peak (42.5). First bottom: 28.3, Second bottom: 29.1",
      "indicators": {
        "rsi": 44.2,
        "oversold_threshold": 30,
        "overbought_threshold": 70,
        "pattern": "W",
        "pattern_details": {
          "pattern": "W",
          "first_bottom": {"index": 45, "rsi": 28.3},
          "second_bottom": {"index": 52, "rsi": 29.1},
          "peak": {"index": 48, "rsi": 42.5},
          "current_rsi": 44.2
        }
      }
    }
  ]
}
```

#### Get Current Settings
```bash
curl "http://localhost:8000/strategy-settings/RSI_W_PATTERN"
```

**Response:**
```json
{
  "rsi_period": 14,
  "oversold_threshold": 30,
  "overbought_threshold": 70,
  "min_distance": 3,
  "max_distance": 10,
  "tolerance": 3.0
}
```

#### Update Settings
```bash
curl -X POST "http://localhost:8000/strategy-settings/RSI_W_PATTERN" \
  -H "Content-Type: application/json" \
  -d '{
    "rsi_period": 14,
    "oversold_threshold": 35,
    "overbought_threshold": 65,
    "min_distance": 5,
    "max_distance": 15,
    "tolerance": 2.5
  }'
```

## Strategy Logic

### Pattern Detection Algorithm

1. **Calculate RSI** using EMA smoothing over specified period
2. **Find Local Extrema** (minima and maxima) using a sliding window
3. **Filter Extrema** by oversold/overbought thresholds
4. **Validate Pattern**:
   - Check distance between points (min_distance ≤ distance ≤ max_distance)
   - Verify second bottom/top meets criteria (within tolerance)
5. **Confirm Breakout**:
   - W-Pattern: Current RSI must break above middle peak
   - M-Pattern: Current RSI must break below middle valley

### Signal Strength Calculation

- **W-Pattern**: `strength = min(100, (current_rsi - peak_rsi) * 5 + 70)`
- **M-Pattern**: `strength = min(100, (valley_rsi - current_rsi) * 5 + 70)`

Strength ranges from 0-100, with higher values indicating stronger patterns.

## Trading Guidelines

### Entry Signals

**BUY (W-Pattern)**:
- Wait for RSI to form double bottom in oversold zone
- Confirm second bottom is higher or equal to first
- Enter when RSI breaks above the middle peak
- Consider price action confirmation (higher low on price chart)

**SELL (M-Pattern)**:
- Wait for RSI to form double top in overbought zone
- Confirm second top is lower or equal to first
- Enter when RSI breaks below the middle valley
- Consider price action confirmation (lower high on price chart)

### Risk Management

- **Stop Loss**: Place below recent swing low (BUY) or above swing high (SELL)
- **Position Sizing**: Use signal strength to determine position size
- **Confluence**: Combine with price support/resistance levels
- **Timeframe**: Works best on higher timeframes (1h, 4h, 1d) for reliability

### Best Practices

1. **Use Multiple Timeframes**: Confirm patterns on higher timeframes
2. **Volume Confirmation**: Look for increasing volume on pattern completion
3. **Trend Context**: More reliable in trending markets
4. **Parameter Tuning**:
   - Lower oversold/overbought thresholds for ranging markets
   - Increase min_distance for cleaner patterns
   - Adjust tolerance based on market volatility

## Implementation Details

### Backend Files
- `strategies/rsi_w_pattern.py` - Strategy implementation
- `models.py` - Database model with enum and settings columns
- `main.py` - API endpoints for signals and settings
- `migrate_rsi_w_pattern.py` - Database migration script

### Frontend Files
- `components/StrategyCard.jsx` - Strategy display with 📐 icon
- `components/StrategySettingsModal.jsx` - Parameter configuration UI
- `components/TradingChartWithIndicators.jsx` - RSI chart visualization
- `components/StrategyCard.css` - Strategy icon styling

## Troubleshooting

### Database Error: "column does not exist"
**Solution**: Run the migration script:
```bash
cd stock-auto-trader/backend
python3 migrate_rsi_w_pattern.py
```

### Database Error: "invalid input value for enum"
**Solution**: The migration script now handles this automatically. Re-run it.

### No Signals Generated
**Possible Causes**:
- Insufficient candle data (need at least rsi_period + max_distance + 10 candles)
- No patterns detected in current market conditions
- Thresholds too strict - try adjusting oversold/overbought levels

### Pattern Detection Too Sensitive/Not Sensitive Enough
**Tune Parameters**:
- **Too many signals**: Increase min_distance, decrease tolerance
- **Too few signals**: Increase oversold/overbought thresholds, increase max_distance

## Example Use Cases

### Conservative Trading (Lower Risk)
```json
{
  "oversold_threshold": 25,
  "overbought_threshold": 75,
  "min_distance": 5,
  "max_distance": 15,
  "tolerance": 2.0
}
```

### Aggressive Trading (More Signals)
```json
{
  "oversold_threshold": 35,
  "overbought_threshold": 65,
  "min_distance": 3,
  "max_distance": 20,
  "tolerance": 5.0
}
```

### Swing Trading (Longer Patterns)
```json
{
  "rsi_period": 21,
  "oversold_threshold": 30,
  "overbought_threshold": 70,
  "min_distance": 8,
  "max_distance": 25,
  "tolerance": 3.0
}
```

## Support

For issues or questions:
- Check the main project documentation
- Review API responses for detailed error messages
- Verify database migration completed successfully

---

**Strategy Type**: Reversal
**Indicator**: RSI (Relative Strength Index)
**Timeframes**: 1m, 5m, 1h, 1d (works best on 1h+)
**Market Conditions**: Trending markets with clear reversals
