import { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';
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
      },
      rightPriceScale: {
        borderColor: '#2d3748',
      },
      timeScale: {
        borderColor: '#2d3748',
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: (time) => {
          const date = new Date(time * 1000);
          const istDate = new Date(date.getTime() + (5.5 * 60 * 60 * 1000));
          return istDate.toLocaleString('en-IN', {
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
      // MA Crossover - overlay on price
      if (strategyName === 'MA_CROSSOVER' && indicators.short_ma_line && indicators.long_ma_line) {
        const timestamps = indicators.timestamps || [];

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

        const shortData = indicators.short_ma_line.map((value, idx) => ({
          time: timestamps[idx] ? new Date(timestamps[idx]).getTime() / 1000 : formattedData[idx]?.time || 0,
          value: value,
        })).filter(d => d.time > 0 && d.value !== null && !isNaN(d.value));

        const longData = indicators.long_ma_line.map((value, idx) => ({
          time: timestamps[idx] ? new Date(timestamps[idx]).getTime() / 1000 : formattedData[idx]?.time || 0,
          value: value,
        })).filter(d => d.time > 0 && d.value !== null && !isNaN(d.value));

        if (shortData.length > 0) shortMaSeries.setData(shortData);
        if (longData.length > 0) longMaSeries.setData(longData);
      }

      // Bollinger Bands - overlay on price
      if (strategyName === 'BOLLINGER' && indicators.upper_band_line && indicators.lower_band_line && indicators.middle_band_line) {
        const timestamps = indicators.timestamps || [];

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

        const upperData = indicators.upper_band_line.map((value, idx) => ({
          time: timestamps[idx] ? new Date(timestamps[idx]).getTime() / 1000 : formattedData[idx]?.time || 0,
          value: value,
        })).filter(d => d.time > 0 && d.value !== null && !isNaN(d.value));

        const middleData = indicators.middle_band_line.map((value, idx) => ({
          time: timestamps[idx] ? new Date(timestamps[idx]).getTime() / 1000 : formattedData[idx]?.time || 0,
          value: value,
        })).filter(d => d.time > 0 && d.value !== null && !isNaN(d.value));

        const lowerData = indicators.lower_band_line.map((value, idx) => ({
          time: timestamps[idx] ? new Date(timestamps[idx]).getTime() / 1000 : formattedData[idx]?.time || 0,
          value: value,
        })).filter(d => d.time > 0 && d.value !== null && !isNaN(d.value));

        if (upperData.length > 0) upperBandSeries.setData(upperData);
        if (middleData.length > 0) middleBandSeries.setData(middleData);
        if (lowerData.length > 0) lowerBandSeries.setData(lowerData);
      }
    }

    // Create indicator panel for MACD/RSI
    let indicatorChart = null;
    if (needsIndicatorPanel && indicatorChartContainerRef.current && indicators) {
      indicatorChart = createChart(indicatorChartContainerRef.current, {
        ...chartOptions,
        width: indicatorChartContainerRef.current.clientWidth,
        height: indicatorChartHeight,
      });

      indicatorChartRef.current = indicatorChart;

      const timestamps = indicators.timestamps || [];

      // MACD Indicator
      if (strategyName === 'MACD' && indicators.macd_line && indicators.signal_line && indicators.histogram_line) {
        // MACD histogram
        const histogramSeries = indicatorChart.addHistogramSeries({
          priceFormat: {
            type: 'price',
            precision: 4,
            minMove: 0.0001,
          },
        });

        const histogramData = indicators.histogram_line.map((value, idx) => ({
          time: timestamps[idx] ? new Date(timestamps[idx]).getTime() / 1000 : formattedData[idx]?.time || 0,
          value: value,
          color: value >= 0 ? '#26a69a' : '#ef5350',
        })).filter(d => d.time > 0 && d.value !== null && !isNaN(d.value));

        if (histogramData.length > 0) {
          histogramSeries.setData(histogramData);
        }

        // MACD line
        const macdLineSeries = indicatorChart.addLineSeries({
          color: '#2196F3',
          lineWidth: 2,
          title: 'MACD',
        });

        const macdData = indicators.macd_line.map((value, idx) => ({
          time: timestamps[idx] ? new Date(timestamps[idx]).getTime() / 1000 : formattedData[idx]?.time || 0,
          value: value,
        })).filter(d => d.time > 0 && d.value !== null && !isNaN(d.value));

        if (macdData.length > 0) {
          macdLineSeries.setData(macdData);
        }

        // Signal line
        const signalLineSeries = indicatorChart.addLineSeries({
          color: '#FF6D00',
          lineWidth: 2,
          title: 'Signal',
        });

        const signalData = indicators.signal_line.map((value, idx) => ({
          time: timestamps[idx] ? new Date(timestamps[idx]).getTime() / 1000 : formattedData[idx]?.time || 0,
          value: value,
        })).filter(d => d.time > 0 && d.value !== null && !isNaN(d.value));

        if (signalData.length > 0) {
          signalLineSeries.setData(signalData);
        }
      }

      // RSI Indicator
      if (strategyName === 'RSI' && indicators.rsi_line) {
        const rsiSeries = indicatorChart.addLineSeries({
          color: '#9C27B0',
          lineWidth: 2,
          title: 'RSI',
        });

        // Overbought line (70)
        const overboughtLine = indicatorChart.addLineSeries({
          color: '#ef4444',
          lineWidth: 1,
          lineStyle: 2,
          title: 'Overbought',
        });

        // Oversold line (30)
        const oversoldLine = indicatorChart.addLineSeries({
          color: '#10b981',
          lineWidth: 1,
          lineStyle: 2,
          title: 'Oversold',
        });

        const rsiData = indicators.rsi_line.map((value, idx) => ({
          time: timestamps[idx] ? new Date(timestamps[idx]).getTime() / 1000 : formattedData[idx]?.time || 0,
          value: value,
        })).filter(d => d.time > 0 && d.value !== null && !isNaN(d.value));

        if (rsiData.length > 0) {
          rsiSeries.setData(rsiData);

          const overboughtData = rsiData.map(d => ({ time: d.time, value: 70 }));
          const oversoldData = rsiData.map(d => ({ time: d.time, value: 30 }));

          overboughtLine.setData(overboughtData);
          oversoldLine.setData(oversoldData);
        }
      }

      // Sync time scales with better handling to prevent lag
      let isProgrammaticChange = false;

      priceChart.timeScale().subscribeVisibleTimeRangeChange((timeRange) => {
        if (!isProgrammaticChange && timeRange) {
          isProgrammaticChange = true;
          indicatorChart.timeScale().setVisibleRange(timeRange);
          isProgrammaticChange = false;
        }
      });

      indicatorChart.timeScale().subscribeVisibleTimeRangeChange((timeRange) => {
        if (!isProgrammaticChange && timeRange) {
          isProgrammaticChange = true;
          priceChart.timeScale().setVisibleRange(timeRange);
          isProgrammaticChange = false;
        }
      });

      // Also sync crosshair movement for better UX
      priceChart.subscribeCrosshairMove((param) => {
        if (param.time) {
          indicatorChart.setCrosshairPosition(param.point?.x || 0, param.time, indicatorChart.series()[0]);
        }
      });

      indicatorChart.subscribeCrosshairMove((param) => {
        if (param.time) {
          const candlestickSeries = priceChart.series()[0];
          priceChart.setCrosshairPosition(param.point?.x || 0, param.time, candlestickSeries);
        }
      });
    }

    // Auto-fit content
    priceChart.timeScale().fitContent();
    if (indicatorChart) {
      indicatorChart.timeScale().fitContent();
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

  return (
    <div className="trading-chart-container">
      <div ref={priceChartContainerRef} className="trading-chart" />
      {needsIndicatorPanel && (
        <div
          ref={indicatorChartContainerRef}
          className="indicator-chart"
          style={{ marginTop: '4px' }}
        />
      )}
    </div>
  );
};

export default TradingChartWithIndicators;
