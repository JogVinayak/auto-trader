import { useEffect, useRef, forwardRef, useImperativeHandle } from 'react';
import { createChart } from 'lightweight-charts';
import './TradingChart.css';

const TradingChartWithIndicators = forwardRef(({
  data,
  signals = [],
  height = 400,
  currentSignal = null,
  strategyName = '',
  indicators = null,
  trades = [],
  scrollToTimestamp = null
}, ref) => {
  const priceChartContainerRef = useRef(null);
  const indicatorChartContainerRef = useRef(null);
  const priceChartRef = useRef(null);
  const indicatorChartRef = useRef(null);

  // Expose scroll method to parent
  useImperativeHandle(ref, () => ({
    scrollToTime: (timestamp) => {
      if (priceChartRef.current) {
        const timeScale = priceChartRef.current.timeScale();
        timeScale.scrollToPosition(0, true);
        setTimeout(() => {
          timeScale.scrollToPosition(-50, true); // Center the timestamp
        }, 100);
      }
    }
  }));

  // Determine if we need a separate indicator panel
  const needsIndicatorPanel = strategyName === 'MACD' || strategyName === 'RSI' || strategyName === 'RSI_W_PATTERN';
  const priceChartHeight = needsIndicatorPanel ? height * 0.65 : height;
  const indicatorChartHeight = height * 0.35;

  useEffect(() => {
    if (!priceChartContainerRef.current || !data || data.length === 0) return;

    // Helper to convert timestamp to unix seconds
    const toUnixTime = (timestamp) => {
      if (!timestamp) return 0;
      return Math.floor(new Date(timestamp).getTime() / 1000);
    };

    // Build a map of candle timestamps for proper alignment
    const candleTimeMap = new Map();
    data.forEach((candle) => {
      const time = toUnixTime(candle.timestamp);
      candleTimeMap.set(time, candle);
    });

    // Helper to align indicator data with candle timestamps
    const alignIndicatorData = (indicatorValues, timestamps) => {
      if (!indicatorValues || !timestamps || indicatorValues.length === 0) return [];

      const aligned = [];
      for (let i = 0; i < indicatorValues.length; i++) {
        const time = toUnixTime(timestamps[i]);
        const value = indicatorValues[i];
        if (time > 0 && value !== null && value !== undefined && !isNaN(value)) {
          aligned.push({ time, value });
        }
      }
      // Sort by time to ensure proper ordering
      return aligned.sort((a, b) => a.time - b.time);
    };

    const chartOptions = {
      layout: {
        background: { color: '#1a2234' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: '#2d3748' },
        horzLines: { color: '#2d3748' },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          labelVisible: true,
        },
        horzLine: {
          labelVisible: true,
        },
      },
      rightPriceScale: {
        borderColor: '#2d3748',
        scaleMargins: {
          top: 0.1,
          bottom: 0.1,
        },
      },
      timeScale: {
        borderColor: '#2d3748',
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 5,
        barSpacing: 6,
        minBarSpacing: 2,
        tickMarkFormatter: (time, tickMarkType, locale) => {
          const date = new Date(time * 1000);

          // For day boundaries or first tick, show only the date
          if (tickMarkType === 0) {
            return date.toLocaleDateString('en-IN', {
              month: 'short',
              day: 'numeric',
              timeZone: 'Asia/Kolkata'
            });
          }

          // For other ticks, show only the time
          return date.toLocaleTimeString('en-IN', {
            hour: '2-digit',
            minute: '2-digit',
            timeZone: 'Asia/Kolkata'
          });
        },
      },
    };

    // Create main price chart
    const priceChart = createChart(priceChartContainerRef.current, {
      ...chartOptions,
      width: priceChartContainerRef.current.clientWidth,
      height: priceChartHeight,
    });

    priceChartRef.current = priceChart;

    // Add candlestick series
    const candlestickSeries = priceChart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderUpColor: '#10b981',
      borderDownColor: '#ef4444',
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    // Format candle data
    const formattedData = data.map((candle) => ({
      time: new Date(candle.timestamp).getTime() / 1000,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    }));

    candlestickSeries.setData(formattedData);

    // Add markers (signals and trades)
    const markers = [];

    // Historical signals
    if (signals && signals.length > 0) {
      signals.forEach((signal) => {
        markers.push({
          time: new Date(signal.timestamp).getTime() / 1000,
          position: signal.signal === 'BUY' ? 'belowBar' : 'aboveBar',
          color: signal.signal === 'BUY' ? '#10b981' : '#ef4444',
          shape: signal.signal === 'BUY' ? 'arrowUp' : 'arrowDown',
          text: signal.strategy,
        });
      });
    }

    // Current signal marker
    if (currentSignal && currentSignal !== 'HOLD' && formattedData.length > 0) {
      const lastCandle = formattedData[formattedData.length - 1];
      markers.push({
        time: lastCandle.time,
        position: currentSignal === 'BUY' ? 'belowBar' : 'aboveBar',
        color: currentSignal === 'BUY' ? '#10b981' : '#ef4444',
        shape: currentSignal === 'BUY' ? 'arrowUp' : 'arrowDown',
        text: strategyName || currentSignal,
      });
    }

    // Trade markers
    if (trades && trades.length > 0) {
      trades.forEach((trade) => {
        if (strategyName && trade.strategy !== strategyName) return;

        const tradeTime = new Date(trade.timestamp || trade.entry_time).getTime() / 1000;
        markers.push({
          time: tradeTime,
          position: trade.type === 'BUY' ? 'belowBar' : 'aboveBar',
          color: trade.type === 'BUY' ? '#3b82f6' : '#f59e0b',
          shape: 'circle',
          text: `${trade.type}`,
          size: 2,
        });

        if (trade.exit_time && trade.exit_price) {
          const exitTime = new Date(trade.exit_time).getTime() / 1000;
          markers.push({
            time: exitTime,
            position: trade.type === 'BUY' ? 'aboveBar' : 'belowBar',
            color: trade.pnl >= 0 ? '#10b981' : '#ef4444',
            shape: 'square',
            text: `EXIT ${trade.pnl >= 0 ? '↑' : '↓'}`,
            size: 1.5,
          });
        }
      });
    }

    if (markers.length > 0) {
      candlestickSeries.setMarkers(markers);
    }

    // Add overlay indicators (MA, Bollinger Bands)
    if (indicators && strategyName) {
      const timestamps = indicators.timestamps || [];

      // MA Crossover - overlay on price
      if (strategyName === 'MA_CROSSOVER' && indicators.short_ma_line && indicators.long_ma_line) {
        const shortMaSeries = priceChart.addLineSeries({
          color: '#3b82f6',
          lineWidth: 2,
          title: 'Short MA',
        });

        const longMaSeries = priceChart.addLineSeries({
          color: '#8b5cf6',
          lineWidth: 2,
          title: 'Long MA',
        });

        const shortData = alignIndicatorData(indicators.short_ma_line, timestamps);
        const longData = alignIndicatorData(indicators.long_ma_line, timestamps);

        if (shortData.length > 0) shortMaSeries.setData(shortData);
        if (longData.length > 0) longMaSeries.setData(longData);
      }

      // Bollinger Bands - overlay on price
      if (strategyName === 'BOLLINGER' && indicators.upper_band_line && indicators.lower_band_line && indicators.middle_band_line) {
        const upperBandSeries = priceChart.addLineSeries({
          color: '#ef4444',
          lineWidth: 1,
          lineStyle: 2,
          title: 'Upper Band',
        });

        const middleBandSeries = priceChart.addLineSeries({
          color: '#94a3b8',
          lineWidth: 1,
          title: 'Middle Band',
        });

        const lowerBandSeries = priceChart.addLineSeries({
          color: '#10b981',
          lineWidth: 1,
          lineStyle: 2,
          title: 'Lower Band',
        });

        const upperData = alignIndicatorData(indicators.upper_band_line, timestamps);
        const middleData = alignIndicatorData(indicators.middle_band_line, timestamps);
        const lowerData = alignIndicatorData(indicators.lower_band_line, timestamps);

        if (upperData.length > 0) upperBandSeries.setData(upperData);
        if (middleData.length > 0) middleBandSeries.setData(middleData);
        if (lowerData.length > 0) lowerBandSeries.setData(lowerData);
      }
    }

    // Create indicator panel for MACD/RSI (TradingView style - separate synced panel)
    let indicatorChart = null;
    if (needsIndicatorPanel && indicatorChartContainerRef.current && indicators) {
      const timestamps = indicators.timestamps || [];

      // Create a map of indicator timestamps to values for proper alignment
      const indicatorTimeMap = new Map();
      timestamps.forEach((ts, idx) => {
        indicatorTimeMap.set(toUnixTime(ts), idx);
      });

      // Helper to create indicator data aligned with ALL candle timestamps
      // This ensures both charts have the same number of data points for proper sync
      const createAlignedIndicatorData = (indicatorValues) => {
        if (!indicatorValues || indicatorValues.length === 0) return [];

        return formattedData.map(candle => {
          const idx = indicatorTimeMap.get(candle.time);
          if (idx !== undefined && indicatorValues[idx] !== null && !isNaN(indicatorValues[idx])) {
            return { time: candle.time, value: indicatorValues[idx] };
          }
          // Return data point with same time but no value (creates gap in chart)
          return { time: candle.time, value: undefined };
        }).filter(d => d.value !== undefined);
      };

      // Create indicator chart with matching time scale settings
      indicatorChart = createChart(indicatorChartContainerRef.current, {
        ...chartOptions,
        width: indicatorChartContainerRef.current.clientWidth,
        height: indicatorChartHeight,
        timeScale: {
          ...chartOptions.timeScale,
          visible: false, // Hide time axis on indicator panel (TradingView style)
        },
        rightPriceScale: {
          borderColor: '#2d3748',
          scaleMargins: {
            top: 0.1,
            bottom: 0.1,
          },
        },
      });

      indicatorChartRef.current = indicatorChart;

      // MACD Indicator
      if (strategyName === 'MACD' && indicators.macd_line && indicators.signal_line && indicators.histogram_line) {
        // MACD histogram - use aligned data for proper sync with candles
        const histogramSeries = indicatorChart.addHistogramSeries({
          priceFormat: {
            type: 'price',
            precision: 4,
            minMove: 0.0001,
          },
          priceScaleId: 'right',
        });

        const histogramData = createAlignedIndicatorData(indicators.histogram_line).map(d => ({
          ...d,
          color: d.value >= 0 ? '#26a69a' : '#ef5350',
        }));

        if (histogramData.length > 0) {
          histogramSeries.setData(histogramData);
        }

        // MACD line
        const macdLineSeries = indicatorChart.addLineSeries({
          color: '#2196F3',
          lineWidth: 2,
          title: 'MACD',
          priceScaleId: 'right',
        });

        const macdData = createAlignedIndicatorData(indicators.macd_line);
        if (macdData.length > 0) {
          macdLineSeries.setData(macdData);
        }

        // Signal line
        const signalLineSeries = indicatorChart.addLineSeries({
          color: '#FF6D00',
          lineWidth: 2,
          title: 'Signal',
          priceScaleId: 'right',
        });

        const signalData = createAlignedIndicatorData(indicators.signal_line);
        if (signalData.length > 0) {
          signalLineSeries.setData(signalData);
        }

        // Zero line spanning all candles for reference
        const zeroLine = indicatorChart.addLineSeries({
          color: '#4a5568',
          lineWidth: 1,
          lineStyle: 2,
          priceScaleId: 'right',
          crosshairMarkerVisible: false,
        });
        const zeroData = formattedData.map(d => ({ time: d.time, value: 0 }));
        zeroLine.setData(zeroData);
      }

      // RSI Indicator (for both RSI and RSI_W_PATTERN strategies)
      if ((strategyName === 'RSI' || strategyName === 'RSI_W_PATTERN') && indicators.rsi_line) {
        // Configure RSI scale (0-100)
        indicatorChart.applyOptions({
          rightPriceScale: {
            autoScale: false,
            scaleMargins: {
              top: 0.05,
              bottom: 0.05,
            },
          },
        });

        const rsiSeries = indicatorChart.addLineSeries({
          color: '#9C27B0',
          lineWidth: 2,
          title: strategyName === 'RSI_W_PATTERN' ? 'RSI W/M-Pattern' : 'RSI',
          priceScaleId: 'right',
        });

        // Use aligned data for proper sync with candles
        const rsiData = createAlignedIndicatorData(indicators.rsi_line);

        if (rsiData.length > 0) {
          rsiSeries.setData(rsiData);
        }

        // Reference lines spanning all candles
        const allTimes = formattedData.map(d => d.time);

        // Use thresholds from indicators if available (for RSI_W_PATTERN), otherwise use defaults
        const overboughtLevel = indicators.overbought_threshold || 70;
        const oversoldLevel = indicators.oversold_threshold || 30;

        const overboughtData = allTimes.map(time => ({ time, value: overboughtLevel }));
        const oversoldData = allTimes.map(time => ({ time, value: oversoldLevel }));
        const middleData = allTimes.map(time => ({ time, value: 50 }));

        // Overbought line
        const overboughtLine = indicatorChart.addLineSeries({
          color: '#ef4444',
          lineWidth: 1,
          lineStyle: 2,
          priceScaleId: 'right',
          crosshairMarkerVisible: false,
        });
        overboughtLine.setData(overboughtData);

        // Middle line (50)
        const middleLine = indicatorChart.addLineSeries({
          color: '#4a5568',
          lineWidth: 1,
          lineStyle: 2,
          priceScaleId: 'right',
          crosshairMarkerVisible: false,
        });
        middleLine.setData(middleData);

        // Oversold line
        const oversoldLine = indicatorChart.addLineSeries({
          color: '#10b981',
          lineWidth: 1,
          lineStyle: 2,
          priceScaleId: 'right',
          crosshairMarkerVisible: false,
        });
        oversoldLine.setData(oversoldData);
      }

      // TradingView-style synchronized scrolling and zooming
      let isSyncing = false;

      const syncTimeScale = (sourceChart, targetChart) => {
        if (isSyncing) return;
        isSyncing = true;

        const sourceTimeScale = sourceChart.timeScale();
        const targetTimeScale = targetChart.timeScale();

        const logicalRange = sourceTimeScale.getVisibleLogicalRange();
        if (logicalRange) {
          targetTimeScale.setVisibleLogicalRange(logicalRange);
        }

        isSyncing = false;
      };

      // Sync on visible range change (zoom/scroll)
      priceChart.timeScale().subscribeVisibleLogicalRangeChange(() => {
        syncTimeScale(priceChart, indicatorChart);
      });

      indicatorChart.timeScale().subscribeVisibleLogicalRangeChange(() => {
        syncTimeScale(indicatorChart, priceChart);
      });

      // Sync crosshair movement
      priceChart.subscribeCrosshairMove((param) => {
        if (param.time && indicatorChart.series().length > 0) {
          indicatorChart.setCrosshairPosition(0, param.time, indicatorChart.series()[0]);
        } else {
          indicatorChart.clearCrosshairPosition();
        }
      });

      indicatorChart.subscribeCrosshairMove((param) => {
        if (param.time && priceChart.series().length > 0) {
          priceChart.setCrosshairPosition(0, param.time, priceChart.series()[0]);
        } else {
          priceChart.clearCrosshairPosition();
        }
      });
    }

    // Set initial view to show latest candles (TradingView style)
    // Show approximately the last 50-80 candles to match indicator data coverage
    const totalBars = formattedData.length;
    const visibleBars = Math.min(80, totalBars); // Show last 80 candles or all if less
    const initialLogicalRange = {
      from: totalBars - visibleBars,
      to: totalBars + 5, // Add some padding on the right
    };

    priceChart.timeScale().setVisibleLogicalRange(initialLogicalRange);

    if (indicatorChart) {
      // Sync indicator chart to the same logical range
      indicatorChart.timeScale().setVisibleLogicalRange(initialLogicalRange);
    }

    // Handle window resize
    const handleResize = () => {
      if (priceChartContainerRef.current) {
        priceChart.applyOptions({
          width: priceChartContainerRef.current.clientWidth,
        });
      }
      if (indicatorChart && indicatorChartContainerRef.current) {
        indicatorChart.applyOptions({
          width: indicatorChartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      priceChart.remove();
      if (indicatorChart) {
        indicatorChart.remove();
      }
    };
  }, [data, signals, height, currentSignal, strategyName, indicators, trades, needsIndicatorPanel, priceChartHeight, indicatorChartHeight]);

  // Effect to scroll to timestamp when it changes
  useEffect(() => {
    if (scrollToTimestamp && priceChartRef.current) {
      const timeScale = priceChartRef.current.timeScale();

      // Scroll to the specific timestamp
      setTimeout(() => {
        const range = 100; // Show 100 bars on each side
        timeScale.setVisibleLogicalRange({
          from: Math.max(0, scrollToTimestamp - range),
          to: scrollToTimestamp + range
        });
      }, 100);
    }
  }, [scrollToTimestamp]);

  return (
    <div className="trading-chart-container" style={{ height: `${height}px` }}>
      <div
        ref={priceChartContainerRef}
        className="trading-chart"
        style={{ height: `${priceChartHeight}px` }}
      />
      {needsIndicatorPanel && (
        <div
          ref={indicatorChartContainerRef}
          className="indicator-chart"
          style={{ height: `${indicatorChartHeight}px`, marginTop: '4px' }}
        />
      )}
    </div>
  );
});

TradingChartWithIndicators.displayName = 'TradingChartWithIndicators';

export default TradingChartWithIndicators;
