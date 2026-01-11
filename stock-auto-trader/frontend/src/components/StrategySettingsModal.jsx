import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { X, Settings, Info, Loader2 } from 'lucide-react';
import { strategySettingsAPI } from '../services/api';
import './StrategySettingsModal.css';

const StrategySettingsModal = ({ isOpen, onClose, strategy, onSave }) => {
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // Default settings for each strategy (UI configuration)
  const strategyDefaults = {
    MACD: {
      fast_period: { value: 12, label: 'Fast Period', min: 5, max: 30, description: 'Fast EMA period' },
      slow_period: { value: 26, label: 'Slow Period', min: 10, max: 50, description: 'Slow EMA period' },
      signal_period: { value: 9, label: 'Signal Period', min: 5, max: 20, description: 'Signal line period' },
    },
    RSI: {
      period: { value: 14, label: 'Period', min: 5, max: 30, description: 'RSI calculation period' },
      overbought: { value: 70, label: 'Overbought Level', min: 60, max: 90, description: 'Overbought threshold' },
      oversold: { value: 30, label: 'Oversold Level', min: 10, max: 40, description: 'Oversold threshold' },
    },
    MA_CROSSOVER: {
      short_period: { value: 20, label: 'Short MA Period', min: 5, max: 50, description: 'Short moving average period' },
      long_period: { value: 50, label: 'Long MA Period', min: 20, max: 200, description: 'Long moving average period' },
      ma_type: {
        value: 'EMA',
        label: 'MA Type',
        type: 'select',
        options: ['SMA', 'EMA'],
        description: 'Moving average type'
      },
    },
    BOLLINGER: {
      period: { value: 20, label: 'Period', min: 10, max: 50, description: 'Bollinger Bands period' },
      std_dev: { value: 2, label: 'Standard Deviation', min: 1, max: 4, step: 0.5, description: 'Number of standard deviations' },
    },
    RSI_W_PATTERN: {
      rsi_period: { value: 14, label: 'RSI Period', min: 5, max: 30, description: 'RSI calculation period' },
      oversold_threshold: { value: 30, label: 'Oversold Threshold', min: 20, max: 40, description: 'RSI level for W-pattern detection' },
      overbought_threshold: { value: 70, label: 'Overbought Threshold', min: 60, max: 80, description: 'RSI level for M-pattern detection' },
      min_distance: { value: 3, label: 'Min Distance', min: 2, max: 10, description: 'Minimum candles between pattern points' },
      max_distance: { value: 10, label: 'Max Distance', min: 5, max: 30, description: 'Maximum candles between pattern points' },
      tolerance: { value: 3, label: 'Pattern Tolerance', min: 1, max: 10, step: 0.5, description: 'RSI point tolerance for pattern validation' },
    },
  };

  // Fetch settings from database when modal opens
  useEffect(() => {
    if (isOpen && strategy) {
      fetchSettings();
    }
  }, [isOpen, strategy]);

  const fetchSettings = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await strategySettingsAPI.get(strategy.name);
      setSettings(response.data);
    } catch (err) {
      console.error('Error fetching settings:', err);
      // Fall back to defaults
      const defaults = strategyDefaults[strategy.name] || {};
      const initialSettings = {};
      Object.keys(defaults).forEach(key => {
        initialSettings[key] = defaults[key].value;
      });
      setSettings(initialSettings);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen || !strategy) return null;

  const strategyConfig = strategyDefaults[strategy.name] || {};

  const handleChange = (key, value) => {
    setSettings(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await strategySettingsAPI.save(strategy.name, settings);
      // Call the parent onSave to refresh signals
      onSave(strategy.name, settings);
      onClose();
    } catch (err) {
      console.error('Error saving settings:', err);
      setError('Failed to save settings. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    const defaults = strategyDefaults[strategy.name] || {};
    const resetSettings = {};
    Object.keys(defaults).forEach(key => {
      resetSettings[key] = defaults[key].value;
    });
    setSettings(resetSettings);
  };

  const handleOverlayClick = (e) => {
    if (e.target.classList.contains('strategy-settings-overlay')) {
      onClose();
    }
  };

  // Use portal to render modal at document body level (above all other elements)
  return createPortal(
    <div className="strategy-settings-overlay" onClick={handleOverlayClick}>
      <div className="strategy-settings-modal">
        <div className="strategy-settings-header">
          <div className="settings-title">
            <Settings size={24} />
            <h2>{strategy.name.replace('_', ' ')} Settings</h2>
          </div>
          <button className="settings-close-btn" onClick={onClose}>
            <X size={24} />
          </button>
        </div>

        <div className="strategy-settings-body">
          <div className="settings-description">
            <Info size={16} />
            <p>{strategy.description}</p>
          </div>

          {loading ? (
            <div className="settings-loading">
              <Loader2 size={24} className="spin" />
              <span>Loading settings...</span>
            </div>
          ) : (
            <div className="settings-form">
              {Object.entries(strategyConfig).map(([key, config]) => (
                <div key={key} className="setting-item">
                  <div className="setting-label-row">
                    <label htmlFor={key}>{config.label}</label>
                    <span className="setting-value-display">{settings[key]}</span>
                  </div>

                  {config.type === 'select' ? (
                    <select
                      id={key}
                      value={settings[key] || config.value}
                      onChange={(e) => handleChange(key, e.target.value)}
                      className="setting-select"
                    >
                      {config.options.map(option => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="range"
                      id={key}
                      min={config.min}
                      max={config.max}
                      step={config.step || 1}
                      value={settings[key] || config.value}
                      onChange={(e) => handleChange(key, Number(e.target.value))}
                      className="setting-slider"
                    />
                  )}

                  <span className="setting-description">{config.description}</span>
                </div>
              ))}
            </div>
          )}

          {error && (
            <div className="settings-error">
              {error}
            </div>
          )}
        </div>

        <div className="strategy-settings-footer">
          <button className="btn btn-secondary" onClick={handleReset} disabled={loading || saving}>
            Reset to Defaults
          </button>
          <div className="footer-actions">
            <button className="btn btn-secondary" onClick={onClose} disabled={saving}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={handleSave} disabled={loading || saving}>
              {saving ? (
                <>
                  <Loader2 size={16} className="spin" />
                  Saving...
                </>
              ) : (
                'Save Settings'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default StrategySettingsModal;
