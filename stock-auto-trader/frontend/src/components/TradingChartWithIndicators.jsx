import { createChart } from 'lightweight-charts';
import { useEffect, useRef } from 'react';
import './TradingChart.css';

const TradingChartWithIndicators = ({
  data,
  signals = [],
  height = 400,
  currentSignal = null,
  strategyName = '',
  indicators = null,
  trades = []
}) => {
  const priceChartContainerRef = useRef(null);
  const indicatorChartContainerRef = useRef(null);
  const priceChartRef = useRef(null);
  const indicatorChartRef = useRef(null);

  // Determine if we need a separate indicator panel
  const needsIndicatorPanel = strategyName === 'MACD' || strategyName === 'RSI';
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

    // Helper to calculate EMA from candle data
    const calculateEMA = (closes, period) => {
      if (closes.length < period) return [];

      const multiplier = 2 / (period + 1);
      const emaValues = [];

      // Calculate initial SMA for the first EMA value
      let sum = 0;
      for (let i = 0; i < period; i++) {
        sum += closes[i];
        emaValues.push(null); // No EMA for first period-1 values
      }

      // First EMA is the SMA
      let ema = sum / period;
      emaValues[period - 1] = ema;

      // Calculate subsequent EMAs
      for (let i = period; i < closes.length; i++) {
        ema = (closes[i] - ema) * multiplier + ema;
        emaValues.push(ema);
      }

      return emaValues;
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
        tickMarkFormatter: (time) => {
          const date = new Date(time * 1000);
          return date.toLocaleString('en-IN', {
            month: 'short',
            day: 'numeric',
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

      // MTF_EMA - 7 EMA lines calculated from current timeframe candle data
      if (strategyName === 'MTF_EMA') {
        const emaPeriods = [20, 30, 40, 50, 60, 200, 300];
        const bullishColor = '#10b981';  // lime/green
        const bearishColor = '#a855f7';  // purple

        // Extract close prices from candle data
        const closes = data.map(candle => candle.close);

        emaPeriods.forEach((period) => {
          // Calculate EMA from candle data for this timeframe
          const emaValues = calculateEMA(closes, period);

          if (emaValues.length > 0) {
            // Determine trend: EMA > EMA[2 bars ago] = bullish
            const lastIdx = emaValues.length - 1;
            const current = emaValues[lastIdx];
            const prev2 = lastIdx >= 2 ? emaValues[lastIdx - 2] : current;
            const isBullish = current !== null && prev2 !== null && current > prev2;

            const emaSeries = priceChart.addLineSeries({
              color: isBullish ? bullishColor : bearishColor,
              lineWidth: period >= 200 ? 2 : 1,
              title: `EMA ${period}`,
              priceLineVisible: false,
              lastValueVisible: period === 200 || period === 300,
            });

            // Build EMA data aligned with candle timestamps
            const emaData = [];
            for (let i = 0; i < emaValues.length; i++) {
              if (emaValues[i] !== null && formattedData[i]) {
                emaData.push({
                  time: formattedData[i].time,
                  value: emaValues[i],
                });
              }
            }

            if (emaData.length > 0) emaSeries.setData(emaData);
          }
        });

        // Add crossover markers (detect EMA crossing its 2-bar-ago value)
        const crossoverMarkers = [];
        emaPeriods.forEach((period) => {
          const emaValues = calculateEMA(closes, period);
          for (let i = 3; i < emaValues.length; i++) {
            if (emaValues[i] === null || emaValues[i - 2] === null) continue;
            if (emaValues[i - 1] === null || emaValues[i - 3] === null) continue;

            const prevCross = emaValues[i - 1] > emaValues[i - 3];
            const currCross = emaValues[i] > emaValues[i - 2];

            // Crossover up: was below, now above
            if (!prevCross && currCross && formattedData[i]) {
              crossoverMarkers.push({
                time: formattedData[i].time,
                position: 'belowBar',
                color: bullishColor,
                shape: 'arrowUp',
                text: `EMA${period}`,
                size: 1,
              });
            }
            // Crossover down: was above, now below
            else if (prevCross && !currCross && formattedData[i]) {
              crossoverMarkers.push({
                time: formattedData[i].time,
                position: 'aboveBar',
                color: bearishColor,
                shape: 'arrowDown',
                text: `EMA${period}`,
                size: 1,
              });
            }
          }
        });

        if (crossoverMarkers.length > 0) {
          const allMarkers = [...markers, ...crossoverMarkers];
          candlestickSeries.setMarkers(allMarkers.sort((a, b) => a.time - b.time));
        }
      }
    }

    // Create indicator panel for MACD/RSI (TradingView style - separate synced panel)
    let indicatorChart = null;
    let priceContainer = null;
    let indicatorContainer = null;
    let priceWheelHandler = null;
    let indicatorWheelHandler = null;
    let priceDragHandler = null;
    let indicatorDragHandler = null;
    let pendingSync = null;

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

      // RSI Indicator
      if (strategyName === 'RSI' && indicators.rsi_line) {
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
          title: 'RSI',
          priceScaleId: 'right',
        });

        // Use aligned data for proper sync with candles
        const rsiData = createAlignedIndicatorData(indicators.rsi_line);

        if (rsiData.length > 0) {
          rsiSeries.setData(rsiData);
        }

        // Reference lines spanning all candles
        const allTimes = formattedData.map(d => d.time);
        const overboughtData = allTimes.map(time => ({ time, value: 70 }));
        const oversoldData = allTimes.map(time => ({ time, value: 30 }));
        const middleData = allTimes.map(time => ({ time, value: 50 }));

        // Overbought line (70)
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

        // Oversold line (30)
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
      // Using a more immediate sync approach to eliminate lag
      let isSyncing = false;

      const syncTimeScaleImmediate = (sourceChart, targetChart) => {
        if (isSyncing) return;

        const sourceTimeScale = sourceChart.timeScale();
        const targetTimeScale = targetChart.timeScale();
        const logicalRange = sourceTimeScale.getVisibleLogicalRange();

        if (logicalRange) {
          isSyncing = true;
          targetTimeScale.setVisibleLogicalRange(logicalRange);
          isSyncing = false;
        }
      };

      // Use requestAnimationFrame for smoother batched updates
      const syncWithRAF = (sourceChart, targetChart) => {
        if (pendingSync) {
          cancelAnimationFrame(pendingSync);
        }
        pendingSync = requestAnimationFrame(() => {
          syncTimeScaleImmediate(sourceChart, targetChart);
          pendingSync = null;
        });
      };

      // Subscribe to visible range changes
      priceChart.timeScale().subscribeVisibleLogicalRangeChange(() => {
        if (!isSyncing) {
          syncWithRAF(priceChart, indicatorChart);
        }
      });

      indicatorChart.timeScale().subscribeVisibleLogicalRangeChange(() => {
        if (!isSyncing) {
          syncWithRAF(indicatorChart, priceChart);
        }
      });

      // Intercept wheel events to sync immediately on user interaction
      // This provides instant feedback before the chart's internal handler runs
      const handleWheel = (sourceChart, targetChart) => () => {
        // Let the default handler process first, then sync immediately
        requestAnimationFrame(() => {
          syncTimeScaleImmediate(sourceChart, targetChart);
        });
      };

      priceWheelHandler = handleWheel(priceChart, indicatorChart);
      indicatorWheelHandler = handleWheel(indicatorChart, priceChart);

      priceChartContainerRef.current?.addEventListener('wheel', priceWheelHandler, { passive: true });
      indicatorChartContainerRef.current?.addEventListener('wheel', indicatorWheelHandler, { passive: true });

      // Also sync on mouse drag (for panning)
      const handleMouseMove = (sourceChart, targetChart) => (e) => {
        if (e.buttons === 1) { // Left mouse button pressed (dragging)
          requestAnimationFrame(() => {
            syncTimeScaleImmediate(sourceChart, targetChart);
          });
        }
      };

      priceDragHandler = handleMouseMove(priceChart, indicatorChart);
      indicatorDragHandler = handleMouseMove(indicatorChart, priceChart);

      priceChartContainerRef.current?.addEventListener('mousemove', priceDragHandler);
      indicatorChartContainerRef.current?.addEventListener('mousemove', indicatorDragHandler);

      // Store container refs for cleanup
      priceContainer = priceChartContainerRef.current;
      indicatorContainer = indicatorChartContainerRef.current;

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

      // Remove wheel and mouse event listeners for chart sync
      if (indicatorChart) {
        if (priceContainer) {
          priceContainer.removeEventListener('wheel', priceWheelHandler);
          priceContainer.removeEventListener('mousemove', priceDragHandler);
        }
        if (indicatorContainer) {
          indicatorContainer.removeEventListener('wheel', indicatorWheelHandler);
          indicatorContainer.removeEventListener('mousemove', indicatorDragHandler);
        }
        // Cancel any pending sync
        if (pendingSync) {
          cancelAnimationFrame(pendingSync);
        }
        indicatorChart.remove();
      }

      priceChart.remove();
    };
  }, [data, signals, height, currentSignal, strategyName, indicators, trades, needsIndicatorPanel, priceChartHeight, indicatorChartHeight]);

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
};

export default TradingChartWithIndicators;
