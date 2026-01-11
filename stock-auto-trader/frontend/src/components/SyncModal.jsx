import { X, CheckCircle, AlertCircle, Loader } from 'lucide-react';
import './SyncModal.css';

const SyncModal = ({ symbol, isOpen, onClose, syncStatus }) => {
  if (!isOpen) return null;

  const { stage, message, progress, error, success, details, exchange, marketState, isMarketOpen, syncType } = syncStatus;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="sync-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="sync-modal-header">
          <h3>Syncing {symbol}</h3>
          <button className="close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="sync-modal-body">
          {/* Market Info */}
          {(exchange || marketState || syncType) && (
            <div className="market-info-card">
              {exchange && (
                <div className="info-row">
                  <span className="info-label">Exchange:</span>
                  <span className="info-value">{exchange}</span>
                </div>
              )}
              {marketState && (
                <div className="info-row">
                  <span className="info-label">Market Status:</span>
                  <span className={`market-status ${isMarketOpen ? 'open' : 'closed'}`}>
                    {marketState === 'REGULAR' && '🟢 Open'}
                    {marketState === 'PRE' && '🟡 Pre-Market'}
                    {marketState === 'POST' && '🟡 After-Hours'}
                    {marketState === 'CLOSED' && '🔴 Closed'}
                    {!['REGULAR', 'PRE', 'POST', 'CLOSED'].includes(marketState) && marketState}
                  </span>
                </div>
              )}
              {syncType && (
                <div className="info-row">
                  <span className="info-label">Sync Type:</span>
                  <span className="info-value sync-type">{syncType === 'delta' ? '📊 Delta (New Data Only)' : '📥 Full Sync'}</span>
                </div>
              )}
            </div>
          )}

          {/* Progress Stages */}
          <div className="sync-stages">
            <div className={`sync-stage ${stage === 'fetching' ? 'active' : stage === 'calculating' || stage === 'done' ? 'completed' : ''}`}>
              <div className="stage-icon">
                {stage === 'fetching' ? (
                  <Loader size={20} className="spinning" />
                ) : (stage === 'calculating' || stage === 'done') ? (
                  <CheckCircle size={20} />
                ) : (
                  <div className="stage-number">1</div>
                )}
              </div>
              <div className="stage-info">
                <div className="stage-title">Fetching Data</div>
                <div className="stage-desc">Downloading candles from data source</div>
              </div>
            </div>

            <div className={`sync-stage ${stage === 'calculating' ? 'active' : stage === 'done' ? 'completed' : ''}`}>
              <div className="stage-icon">
                {stage === 'calculating' ? (
                  <Loader size={20} className="spinning" />
                ) : stage === 'done' ? (
                  <CheckCircle size={20} />
                ) : (
                  <div className="stage-number">2</div>
                )}
              </div>
              <div className="stage-info">
                <div className="stage-title">Calculating Indicators</div>
                <div className="stage-desc">Processing technical indicators</div>
              </div>
            </div>

            <div className={`sync-stage ${stage === 'done' ? 'completed' : ''}`}>
              <div className="stage-icon">
                {stage === 'done' ? (
                  <CheckCircle size={20} />
                ) : (
                  <div className="stage-number">3</div>
                )}
              </div>
              <div className="stage-info">
                <div className="stage-title">Complete</div>
                <div className="stage-desc">Data synced successfully</div>
              </div>
            </div>
          </div>

          {/* Current Message */}
          <div className="sync-message">
            {error ? (
              <div className="message-error">
                <AlertCircle size={16} />
                <span>{message || 'Sync failed'}</span>
              </div>
            ) : success ? (
              <div className="message-success">
                <CheckCircle size={16} />
                <span>{message || 'Sync completed successfully'}</span>
              </div>
            ) : (
              <div className="message-info">
                <Loader size={16} className="spinning" />
                <span>{message || 'Syncing...'}</span>
              </div>
            )}
          </div>

          {/* Details */}
          {details && details.length > 0 && (
            <div className="sync-details">
              <h4>Details</h4>
              <div className="details-list">
                {details.map((detail, idx) => (
                  <div key={idx} className="detail-item">
                    <span className="detail-label">{detail.timeframe}:</span>
                    <span className="detail-value">
                      {detail.new_candles > 0 ? (
                        <span className="positive">+{detail.new_candles} new candles</span>
                      ) : (
                        <span className="neutral">Up to date</span>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Progress Bar */}
          {!error && !success && (
            <div className="sync-progress">
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${progress || 0}%` }}
                />
              </div>
              <div className="progress-text">{progress || 0}%</div>
            </div>
          )}
        </div>

        <div className="sync-modal-footer">
          {(error || success) && (
            <button className="btn btn-primary" onClick={onClose}>
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default SyncModal;
