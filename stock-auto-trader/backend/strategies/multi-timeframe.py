import pandas as pd
from typing import Dict
from .base import BaseStrategy, Signal


class MTFEMATrendStrategy(BaseStrategy):
    """
    Multi-Timeframe EMA Trend Strategy (BigBeluga style)

    BUY  : Majority EMA trends bullish across timeframes
    SELL : Majority EMA trends bearish across timeframes
    HOLD : Mixed conditions
    """

    name = "MTF_EMA_TREND"
    description = "Multi-timeframe EMA trend analysis strategy"

    EMA_PERIODS = [20, 30, 40, 50, 60, 200, 300]

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

    def calculate(self, df: pd.DataFrame) -> Dict:
        if len(df) < max(self.EMA_PERIODS) + 5:
            return self.get_result(
                Signal.HOLD, 0, "Insufficient data for EMA calculation"
            )

        dashboard = {}
        bullish_count = 0
        bearish_count = 0

        # ---------- MULTI-TIMEFRAME PROCESS ----------
        for tf_name, tf in self.TIMEFRAMES.items():
            resampled = (
                df.resample(tf)
                .agg({"close": "last"})
                .dropna()
            )

            if len(resampled) < max(self.EMA_PERIODS) + 3:
                continue

            tf_trend = {}
            tf_bullish = 0
            tf_bearish = 0

            for period in self.EMA_PERIODS:
                ema = resampled["close"].ewm(span=period, adjust=False).mean()
                trend_up = ema.iloc[-1] > ema.iloc[-3]

                tf_trend[f"EMA_{period}"] = "🢁" if trend_up else "🢃"

                if trend_up:
                    tf_bullish += 1
                else:
                    tf_bearish += 1

            dashboard[tf_name] = tf_trend

            if tf_bullish > tf_bearish:
                bullish_count += 1
            else:
                bearish_count += 1

        total_tfs = bullish_count + bearish_count
        bullish_ratio = bullish_count / total_tfs if total_tfs else 0.5

        # ---------- CURRENT TF EMA VALUES ----------
        current_emas = {}
        for period in self.EMA_PERIODS:
            ema_series = df["close"].ewm(span=period, adjust=False).mean()
            current_emas[f"ema_{period}"] = round(ema_series.iloc[-1], 2)

        indicators = {
            "trend_dashboard": dashboard,
            "bullish_timeframes": bullish_count,
            "bearish_timeframes": bearish_count,
            "bullish_ratio": round(bullish_ratio * 100, 2),
            "current_emas": current_emas,
            "price": round(df["close"].iloc[-1], 2)
        }

        # ---------- SIGNAL LOGIC ----------
        if bullish_ratio >= 0.65:
            strength = min(100, int(bullish_ratio * 100))
            return self.get_result(
                Signal.BUY,
                strength,
                "Strong multi-timeframe bullish EMA trend",
                indicators
            )

        elif bullish_ratio <= 0.35:
            strength = min(100, int((1 - bullish_ratio) * 100))
            return self.get_result(
                Signal.SELL,
                strength,
                "Strong multi-timeframe bearish EMA trend",
                indicators
            )

        return self.get_result(
            Signal.HOLD,
            50,
            "Mixed EMA trends across timeframes",
            indicators
        )