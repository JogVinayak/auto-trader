import { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';
import './TradingChart.css';

const TradingChart = ({ data, signals = [], height = 400, currentSignal = null, strategyName = '', indicators = null, trades = [] }) => {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candlestickSeriesRef = useRef(null);
  const indicatorSeriesRefs = useRef([]);

  useEffect(() => {
    if (!chartContainerRef.current || !data || data.length === 0) return;

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height,
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
        // Convert to IST (UTC+5:30)
        tickMarkFormatter: (time) => {
          const date = new Date(time * 1000);
          // Add 5 hours 30 minutes for IST
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
    });

    chartRef.current = chart;

    // Add candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderUpColor: '#10b981',
      borderDownColor: '#ef4444',
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    candlestickSeriesRef.current = candlestickSeries;

    // Convert data to lightweight-charts format
    const formattedData = data.map((candle) => ({
      time: new Date(candle.timestamp).getTime() / 1000,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    }));

    candlestickSeries.setData(formattedData);

    // Add signal markers
    const markers = [];

    // Add historical signals if provided
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

    // Add current signal marker on the most recent candle
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

    // Add executed trades markers (buy/sell indicators)
    if (trades && trades.length > 0) {
      trades.forEach((trade) => {
        // Only show trades for the current strategy if strategyName is specified
        if (strategyName && trade.strategy !== strategyName) {
          return;
        }

        const tradeTime = new Date(trade.timestamp || trade.entry_time).getTime() / 1000;

        // Add entry marker (BUY or SELL)
        markers.push({
          time: tradeTime,
          position: trade.type === 'BUY' ? 'belowBar' : 'aboveBar',
          color: trade.type === 'BUY' ? '#3b82f6' : '#f59e0b', // Different colors for actual trades
          shape: trade.type === 'BUY' ? 'circle' : 'circle', // Circles for executed trades
          text: `${trade.type} (${trade.strategy || ''})`,
          size: 2,
        });

        // Add exit marker if trade is closed
        if (trade.exit_time && trade.exit_price) {
          const exitTime = new Date(trade.exit_time).getTime() / 1000;
          markers.push({
            time: exitTime,
            position: trade.type === 'BUY' ? 'aboveBar' : 'belowBar', // Opposite position for exit
            color: trade.pnl >= 0 ? '#10b981' : '#ef4444', // Green for profit, red for loss
            shape: 'square',
            text: `EXIT ${trade.pnl >= 0 ? '↑' : '↓'} ${Math.abs(trade.pnl).toFixed(2)}`,
            size: 1.5,
          });
        }
      });
    }

    if (markers.length > 0) {
      candlestickSeries.setMarkers(markers);
    }

    // Add indicator lines based on strategy
    if (indicators && strategyName) {
      // MA_CROSSOVER Strategy - Add EMA/SMA lines
      if ((strategyName === 'MA_CROSSOVER' || strategyName === 'MA_CROSSOVER ') && 
          (indicators.short_ema_20 || indicators.short_sma_20)) {
        
        // Determine if using EMA or SMA
        const shortKey = indicators.short_ema_20 ? 'short_ema_20' : 'short_sma_20';
        const longKey = indicators.long_ema_50 ? 'long_ema_50' : 'long_sma_50';
        
        // Get historical data
        const shortMaLine = indicators.short_ma_line || [];
        const longMaLine = indicators.long_ma_line || [];
        const timestamps = indicators.timestamps || [];
        
        if (shortMaLine.length > 0 && longMaLine.length > 0) {
          const emaShortSeries = chart.addLineSeries({
            color: '#3b82f6',
            lineWidth: 2,
            title: 'Short MA',
          });
          const emaLongSeries = chart.addLineSeries({
            color: '#8b5cf6',
            lineWidth: 2,
            title: 'Long MA',
          });

          // Map historical data
          const shortData = shortMaLine.map((value, idx) => ({
            time: timestamps[idx] ? new Date(timestamps[idx]).getTime() / 1000 : formattedData[idx]?.time || 0,
            value: value,
          })).filter(d => d.time > 0);

          const longData = longMaLine.map((value, idx) => ({
            time: timestamps[idx] ? new Date(timestamps[idx]).getTime() / 1000 : formattedData[idx]?.time || 0,
            value: value,
          })).filter(d => d.time > 0);

          if (shortData.length > 0) emaShortSeries.setData(shortData);
          if (longData.length > 0) emaLongSeries.setData(longData);

          indicatorSeriesRefs.current.push(emaShortSeries, emaLongSeries);
        }
      }

      // BOLLINGER Strategy - Add Bollinger Bands
      if ((strategyName === 'BOLLINGER' || strategyName === 'BOLLINGER ') && 
          indicators.upper_band_line && indicators.lower_band_line && indicators.middle_band_line) {
        
        const upperBandSeries = chart.addLineSeries({
          color: '#ef4444',
          lineWidth: 1,
          lineStyle: 2, // dashed
          title: 'Upper Band',
        });
        const middleBandSeries = chart.addLineSeries({
          color: '#94a3b8',
          lineWidth: 1,
          title: 'Middle Band (SMA)',
        });
        const lowerBandSeries = chart.addLineSeries({
          color: '#10b981',
          lineWidth: 1,
          lineStyle: 2, // dashed
          title: 'Lower Band',
        });

        const timestamps = indicators.timestamps || [];
        const upperBandLine = indicators.upper_band_line || [];
        const middleBandLine = indicators.middle_band_line || [];
        const lowerBandLine = indicators.lower_band_line || [];

        const upperData = upperBandLine.map((value, idx) => ({
          time: timestamps[idx] ? new Date(timestamps[idx]).getTime() / 1000 : formattedData[idx]?.time || 0,
          value: value,
        })).filter(d => d.time > 0);

        const middleData = middleBandLine.map((value, idx) => ({
          time: timestamps[idx] ? new Date(timestamps[idx]).getTime() / 1000 : formattedData[idx]?.time || 0,
          value: value,
        })).filter(d => d.time > 0);

        const lowerData = lowerBandLine.map((value, idx) => ({
          time: timestamps[idx] ? new Date(timestamps[idx]).getTime() / 1000 : formattedData[idx]?.time || 0,
          value: value,
        })).filter(d => d.time > 0);

        if (upperData.length > 0) upperBandSeries.setData(upperData);
        if (middleData.length > 0) middleBandSeries.setData(middleData);
        if (lowerData.length > 0) lowerBandSeries.setData(lowerData);

        indicatorSeriesRefs.current.push(upperBandSeries, middleBandSeries, lowerBandSeries);
      }

      // MACD Strategy - Add MACD lines (using histogram as area series)
      if ((strategyName === 'MACD' || strategyName === 'MACD ') &&
          indicators.macd_line && indicators.signal_line && indicators.histogram_line) {

        // Create MACD line series with separate price scale
        const macdLineSeries = chart.addLineSeries({
          color: '#3b82f6',
          lineWidth: 2,
          title: 'MACD Line',
          priceScaleId: 'macd',
        });

        const signalLineSeries = chart.addLineSeries({
          color: '#f59e0b',
          lineWidth: 2,
          title: 'Signal Line',
          priceScaleId: 'macd',
        });

        // Add histogram as a histogram series
        const histogramSeries = chart.addHistogramSeries({
          color: '#26a69a',
          priceFormat: {
            type: 'volume',
          },
          priceScaleId: 'macd',
          title: 'Histogram',
        });

        // Configure separate price scale for MACD
        chart.priceScale('macd').applyOptions({
          scaleMargins: {
            top: 0.7,
            bottom: 0,
          },
          borderColor: '#2d3748',
        });

        const timestamps = indicators.timestamps || [];
        const macdLine = indicators.macd_line || [];
        const signalLine = indicators.signal_line || [];
        const histogramLine = indicators.histogram_line || [];

        const macdData = macdLine.map((value, idx) => ({
          time: timestamps[idx] ? new Date(timestamps[idx]).getTime() / 1000 : formattedData[idx]?.time || 0,
          value: value,
        })).filter(d => d.time > 0 && d.value !== null && !isNaN(d.value));

        const signalData = signalLine.map((value, idx) => ({
          time: timestamps[idx] ? new Date(timestamps[idx]).getTime() / 1000 : formattedData[idx]?.time || 0,
          value: value,
        })).filter(d => d.time > 0 && d.value !== null && !isNaN(d.value));

        const histogramData = histogramLine.map((value, idx) => ({
          time: timestamps[idx] ? new Date(timestamps[idx]).getTime() / 1000 : formattedData[idx]?.time || 0,
          value: value,
          color: value >= 0 ? '#26a69a' : '#ef5350',
        })).filter(d => d.time > 0 && d.value !== null && !isNaN(d.value));

        if (macdData.length > 0) macdLineSeries.setData(macdData);
        if (signalData.length > 0) signalLineSeries.setData(signalData);
        if (histogramData.length > 0) histogramSeries.setData(histogramData);

        indicatorSeriesRefs.current.push(macdLineSeries, signalLineSeries, histogramSeries);
      }

      // RSI Strategy - Add RSI line with separate price scale
      if ((strategyName === 'RSI' || strategyName === 'RSI ') && indicators.rsi_line) {

        const rsiSeries = chart.addLineSeries({
          color: '#ec4899',
          lineWidth: 2,
          title: 'RSI',
          priceScaleId: 'rsi',
        });

        // Configure separate price scale for RSI (0-100 range)
        chart.priceScale('rsi').applyOptions({
          scaleMargins: {
            top: 0.7,
            bottom: 0,
          },
          borderColor: '#2d3748',
          // RSI specific range
          autoScale: false,
          mode: 0,
        });

        // Add RSI overbought (70) and oversold (30) reference lines
        const overboughtLine = chart.addLineSeries({
          color: '#ef4444',
          lineWidth: 1,
          lineStyle: 2, // dashed
          title: 'Overbought (70)',
          priceScaleId: 'rsi',
        });

        const oversoldLine = chart.addLineSeries({
          color: '#10b981',
          lineWidth: 1,
          lineStyle: 2, // dashed
          title: 'Oversold (30)',
          priceScaleId: 'rsi',
        });

        const timestamps = indicators.timestamps || [];
        const rsiLine = indicators.rsi_line || [];

        const rsiData = rsiLine.map((value, idx) => ({
          time: timestamps[idx] ? new Date(timestamps[idx]).getTime() / 1000 : formattedData[idx]?.time || 0,
          value: value,
        })).filter(d => d.time > 0 && d.value !== null && !isNaN(d.value));

        // Create reference lines data
        const overboughtData = rsiData.map(d => ({ time: d.time, value: 70 }));
        const oversoldData = rsiData.map(d => ({ time: d.time, value: 30 }));

        if (rsiData.length > 0) {
          rsiSeries.setData(rsiData);
          overboughtLine.setData(overboughtData);
          oversoldLine.setData(oversoldData);
        }

        indicatorSeriesRefs.current.push(rsiSeries, overboughtLine, oversoldLine);
      }
    }

    // Auto-fit content
    chart.timeScale().fitContent();

    // Handle window resize
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, signals, height, currentSignal, strategyName, indicators, trades]);

  return (
    <div className="trading-chart-container">
      <div ref={chartContainerRef} className="trading-chart" />
    </div>
  );
};

export default TradingChart;
