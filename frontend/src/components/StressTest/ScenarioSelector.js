import PropTypes from 'prop-types';

/**
 * Dropdown of stress-test scenarios (from /stress-test/scenarios).
 * Disabled while loading to prevent concurrent requests.
 */
export default function ScenarioSelector({ scenarios, value, onChange, loading }) {
  return (
    <div className="scenario-control">
      <label htmlFor="stress-scenario">Scenario</label>
      <select
        id="stress-scenario"
        disabled={loading || scenarios.length === 0}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {scenarios.map((scenario) => (
          <option key={scenario.id} value={scenario.id}>
            {scenario.name}
          </option>
        ))}
      </select>
    </div>
  );
}

ScenarioSelector.propTypes = {
  scenarios: PropTypes.arrayOf(
    PropTypes.shape({ id: PropTypes.string.isRequired, name: PropTypes.string.isRequired })
  ),
  value: PropTypes.string,
  onChange: PropTypes.func.isRequired,
  loading: PropTypes.bool,
};

ScenarioSelector.defaultProps = {
  scenarios: [],
  value: '',
  loading: false,
};
