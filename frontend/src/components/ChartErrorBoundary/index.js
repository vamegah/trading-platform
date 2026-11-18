import { Component } from 'react';

export default class ChartErrorBoundary extends Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error('ChartErrorBoundary caught an error:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <p className="chart-error" role="alert">
          {this.props.fallback ?? 'Chart unavailable'}
        </p>
      );
    }
    return this.props.children;
  }
}
