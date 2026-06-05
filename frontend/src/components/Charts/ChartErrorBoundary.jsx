import React from 'react';
import PropTypes from 'prop-types';
import { recordChartError } from '../../utils/charts/monitoring';

/**
 * ChartErrorBoundary - Error boundary for chart rendering errors.
 *
 * Keeps a chart failure inside its panel and leaves the numeric rows visible.
 */
class ChartErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    recordChartError({
      component: this.props.componentName,
      message: error?.message,
      stack: error?.stack,
      errorInfo: errorInfo?.componentStack,
    });
    console.error('Chart Error:', error);
    console.error('Chart Error Info:', errorInfo);

    this.setState({
      error,
      errorInfo,
    });
  }

  render() {
    const { hasError, error } = this.state;
    const { children, fallbackHeight = 250 } = this.props;

    if (hasError) {
      return (
        <div className="chart-fallback" data-fallback-height={fallbackHeight} role="alert">
          <div className="chart-fallback__title">Chart failed to load</div>
          <div className="chart-fallback__detail">
            {error?.message || 'An error occurred while rendering this chart.'}
          </div>
          <div className="chart-fallback__hint">
            Please refresh the page or check the numeric values displayed below.
          </div>
        </div>
      );
    }

    return children;
  }
}

ChartErrorBoundary.propTypes = {
  children: PropTypes.node.isRequired,
  componentName: PropTypes.string,
  fallbackHeight: PropTypes.number,
};

ChartErrorBoundary.defaultProps = {
  componentName: 'ChartErrorBoundary',
  fallbackHeight: 250,
};

export default ChartErrorBoundary;
