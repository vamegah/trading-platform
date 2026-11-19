import PropTypes from 'prop-types';
import { CHART_THEME } from '../../styles/chart-theme';

export function confidenceColor(confidence) {
  if (confidence >= 0.68) return CHART_THEME.green;
  if (confidence >= 0.55) return CHART_THEME.amber;
  return CHART_THEME.red;
}

function ConfidenceBar({ confidence = 0 }) {
  const value = Number.isFinite(confidence) ? confidence : 0;
  const percentage = Math.max(0, Math.min(100, Math.round(value * 100)));
  const label = `Confidence ${percentage}%`;

  return (
    <div className="confidence-cell">
      <svg
        aria-label={label}
        className="confidence-bar"
        data-confidence-bar="true"
        role="img"
        viewBox="0 0 100 8"
      >
        <title>{label}</title>
        <rect fill={CHART_THEME.border} height="8" rx="4" width="100" x="0" y="0" />
        <rect fill={confidenceColor(value)} height="8" rx="4" width={percentage} x="0" y="0" />
      </svg>
      <span className="confidence-cell__value">{percentage}%</span>
    </div>
  );
}

ConfidenceBar.propTypes = {
  confidence: PropTypes.number,
};

export default ConfidenceBar;
