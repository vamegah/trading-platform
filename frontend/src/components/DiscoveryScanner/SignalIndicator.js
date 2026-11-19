import PropTypes from 'prop-types';
import { CHART_THEME } from '../../styles/chart-theme';

const SIGNALS = {
  BUY: { symbol: '▲', color: CHART_THEME.green },
  SELL: { symbol: '▼', color: CHART_THEME.red },
  HOLD: { symbol: '—', color: CHART_THEME.grey },
};

function SignalIndicator({ signal }) {
  const normalized = String(signal || 'HOLD').toUpperCase();
  const config = SIGNALS[normalized] || SIGNALS.HOLD;

  return (
    <svg
      aria-label={normalized}
      className="signal-indicator"
      data-signal-indicator={normalized}
      role="img"
      viewBox="0 0 16 16"
      width="16"
      height="16"
    >
      <title>{normalized}</title>
      <text fill={config.color} fontSize="14" textAnchor="middle" x="8" y="13">
        {config.symbol}
      </text>
    </svg>
  );
}

SignalIndicator.propTypes = {
  signal: PropTypes.string,
};

export default SignalIndicator;
