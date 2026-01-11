import pandas as pd
from typing import Dict, List
from .base import BaseStrategy, Signal


class MTFEMAStrategy(BaseStrategy):
    """
    Multi-Timeframe EMA Trend Analysis Strategy (BigBeluga style)

    Analyzes EMA trends across multiple timeframes to determine overall market direction.

    BUY  : 65%+ of EMA/timeframe combinations are bullish
    SELL : 35% or less are bullish (65%+ bearish)
    HOLD : Mixed conditions
    """

    name = "MTF_EMA"
    description = "Multi-Timeframe EMA Trend Analysis"

    # 7 EMA periods as per Pine Script
    EMA_PERIODS = [20, 30, 40, 50, 60, 200, 300]

    # 10 Timeframes
    TIMEFRAMES = {
        "1m": "1T",
        "5m": "5T",
        "15m": "15T",
        "30m": "30T",
        "1h": "1H",
        "2h": "2H",
        "3h": "3H",
        "4h": "4H",
        "5h": "5H",
        "1D": "1D"
    }

    # Colors (for frontend reference)
    BULLISH_COLOR = "#00FF00"  # lime
    BEARISH_COLOR = "#800080"  # purple

    def __init__(
        self,
        ema_periods: List[int] = None,
        bullish_threshold: float = 0.65,
        bearish_threshold: float = 0.35
    ):
        self.ema_periods = ema_periods or self.EMA_PERIODS
        self.bullish_threshold = bullish_threshold
        self.bearish_threshold = bearish_threshold

    def calculate(self, df: pd.DataFrame) -> Dict:
        min_required = max(self.ema_periods) + 5  # 305 for EMA 300
        if len(df) < min_required:
            return self.get_result(
                Signal.HOLD, 0, f"Insufficient data ({len(df)} candles, need {min_required})"
            )

        # Ensure timestamp is datetime index for resampling
        if 'timestamp' in df.columns:
            df = df.set_index('timestamp')

        # ========== MULTI-TIMEFRAME DASHBOARD ==========
        trend_dashboard = {}
        bullish_count = 0
        bearish_count = 0
        total_cells = 0

        for tf_name, tf_rule in self.TIMEFRAMES.items():
            try:
                # Resample to this timeframe
                resampled = df.resample(tf_rule).agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()

                if len(resampled) < max(self.ema_periods) + 3:
                    continue

                tf_trends = {}
                for period in self.ema_periods:
                    ema = resampled['close'].ewm(span=period, adjust=False).mean()
                    # Trend: current EMA > EMA 2 bars ago (Pine: ema > ema[2])
                    trend_up = ema.iloc[-1] > ema.iloc[-3] if len(ema) >= 3 else False

                    tf_trends[f"EMA_{period}"] = "up" if trend_up else "down"
                    total_cells += 1
                    if trend_up:
                        bullish_count += 1
                    else:
                        bearish_count += 1

                trend_dashboard[tf_name] = tf_trends

            except Exception:
                # Skip timeframe if resampling fails
                continue

        # ========== CURRENT TIMEFRAME EMA LINES ==========
        df_reset = df.reset_index()
        ema_lines = {}
        ema_trends = {}
        ema_values = {}
        crossover_signals = []

        for period in self.ema_periods:
            ema = df['close'].ewm(span=period, adjust=False).mean()
            ema_values[f"ema_{period}"] = round(ema.iloc[-1], 2)

            # Store line data for charting (last 100 points)
            ema_lines[f"ema_{period}"] = [round(x, 4) for x in ema.tail(100).tolist()]

            # Trend direction
            trend_up = bool(ema.iloc[-1] > ema.iloc[-3]) if len(ema) >= 3 else False
            ema_trends[f"ema_{period}"] = trend_up

            # Crossover detection (EMA crosses its 2-bar-ago value)
            if len(ema) >= 4:
                prev_cross = ema.iloc[-2] - ema.iloc[-4]  # prev bar vs 2 bars before
                curr_cross = ema.iloc[-1] - ema.iloc[-3]  # current vs 2 bars ago

                if prev_cross <= 0 and curr_cross > 0:
                    crossover_signals.append({
                        "ema": period,
                        "type": "up",
                        "index": len(ema) - 1
                    })
                elif prev_cross >= 0 and curr_cross < 0:
                    crossover_signals.append({
                        "ema": period,
                        "type": "down",
                        "index": len(ema) - 1
                    })

        # Timestamps for chart alignment
        timestamps = [str(t) for t in df_reset['timestamp'].tail(100).tolist()]

        # ========== SIGNAL CALCULATION ==========
        bullish_ratio = bullish_count / total_cells if total_cells > 0 else 0.5

        indicators = {
            "trend_dashboard": trend_dashboard,
            "ema_lines": ema_lines,
            "ema_trends": ema_trends,
            "ema_values": ema_values,
            "crossover_signals": crossover_signals,
            "timestamps": timestamps,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "total_cells": total_cells,
            "bullish_ratio": round(bullish_ratio * 100, 2),
            "price": round(df['close'].iloc[-1], 2)
        }

        # Signal logic
        if bullish_ratio >= self.bullish_threshold:
            strength = min(100, int(bullish_ratio * 100))
            return self.get_result(
                Signal.BUY,
                strength,
                f"Strong bullish trend: {bullish_count}/{total_cells} EMAs rising across timeframes",
                indicators
            )
        elif bullish_ratio <= self.bearish_threshold:
            strength = min(100, int((1 - bullish_ratio) * 100))
            return self.get_result(
                Signal.SELL,
                strength,
                f"Strong bearish trend: {bearish_count}/{total_cells} EMAs falling across timeframes",
                indicators
            )

        return self.get_result(
            Signal.HOLD,
            50,
            f"Mixed trend: {bullish_count} bullish, {bearish_count} bearish across timeframes",
            indicators
        )

    def calculate_mtf(self, current_df: pd.DataFrame, mtf_data: Dict[str, pd.DataFrame]) -> Dict:
        """
        Calculate MTF EMA using actual candle data from each timeframe.

        Args:
            current_df: DataFrame for current timeframe (for EMA lines on chart)
            mtf_data: Dict of DataFrames keyed by timeframe name (1m, 5m, 1h, 1D)
        """
        min_required = max(self.ema_periods) + 5

        # Ensure current_df has timestamp index
        if 'timestamp' in current_df.columns:
            current_df = current_df.set_index('timestamp')

        # ========== MULTI-TIMEFRAME DASHBOARD ==========
        trend_dashboard = {}
        bullish_count = 0
        bearish_count = 0
        total_cells = 0

        # Available timeframes from database
        # Note: 2h, 3h, 4h, 5h are resampled from 1h data
        available_tfs = ["1m", "5m", "15m", "30m", "1h", "2h", "3h", "4h", "5h", "1D"]

        for tf_name in available_tfs:
            if tf_name not in mtf_data:
                continue

            tf_df = mtf_data[tf_name]
            if len(tf_df) < min_required:
                continue

            tf_trends = {}
            for period in self.ema_periods:
                ema = tf_df['close'].ewm(span=period, adjust=False).mean()
                # Trend: current EMA > EMA 2 bars ago
                trend_up = bool(ema.iloc[-1] > ema.iloc[-3]) if len(ema) >= 3 else False

                tf_trends[f"EMA_{period}"] = "up" if trend_up else "down"
                total_cells += 1
                if trend_up:
                    bullish_count += 1
                else:
                    bearish_count += 1

            trend_dashboard[tf_name] = tf_trends

        # ========== CURRENT TIMEFRAME EMA LINES ==========
        df_reset = current_df.reset_index()
        ema_lines = {}
        ema_trends = {}
        ema_values = {}
        crossover_signals = []

        for period in self.ema_periods:
            ema = current_df['close'].ewm(span=period, adjust=False).mean()
            ema_values[f"ema_{period}"] = round(ema.iloc[-1], 2)
            ema_lines[f"ema_{period}"] = [round(x, 4) for x in ema.tail(100).tolist()]

            trend_up = bool(ema.iloc[-1] > ema.iloc[-3]) if len(ema) >= 3 else False
            ema_trends[f"ema_{period}"] = trend_up

            # Crossover detection
            if len(ema) >= 4:
                prev_cross = ema.iloc[-2] - ema.iloc[-4]
                curr_cross = ema.iloc[-1] - ema.iloc[-3]

                if prev_cross <= 0 and curr_cross > 0:
                    crossover_signals.append({"ema": period, "type": "up", "index": len(ema) - 1})
                elif prev_cross >= 0 and curr_cross < 0:
                    crossover_signals.append({"ema": period, "type": "down", "index": len(ema) - 1})

        timestamps = [str(t) for t in df_reset['timestamp'].tail(100).tolist()]

        # ========== SIGNAL CALCULATION ==========
        bullish_ratio = bullish_count / total_cells if total_cells > 0 else 0.5

        indicators = {
            "trend_dashboard": trend_dashboard,
            "ema_lines": ema_lines,
            "ema_trends": ema_trends,
            "ema_values": ema_values,
            "crossover_signals": crossover_signals,
            "timestamps": timestamps,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "total_cells": total_cells,
            "bullish_ratio": round(bullish_ratio * 100, 2),
            "price": round(current_df['close'].iloc[-1], 2)
        }

        if bullish_ratio >= self.bullish_threshold:
            strength = min(100, int(bullish_ratio * 100))
            return self.get_result(
                Signal.BUY, strength,
                f"Strong bullish trend: {bullish_count}/{total_cells} EMAs rising across timeframes",
                indicators
            )
        elif bullish_ratio <= self.bearish_threshold:
            strength = min(100, int((1 - bullish_ratio) * 100))
            return self.get_result(
                Signal.SELL, strength,
                f"Strong bearish trend: {bearish_count}/{total_cells} EMAs falling across timeframes",
                indicators
            )

        return self.get_result(
            Signal.HOLD, 50,
            f"Mixed trend: {bullish_count} bullish, {bearish_count} bearish across timeframes",
            indicators
        )
