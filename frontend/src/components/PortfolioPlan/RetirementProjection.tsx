import React from "react";

function RetirementProjection({ projection, narrative }) {
	if (!projection || projection.status === "not_requested") return null;
	return (
		<section className="panel advisor-retirement">
			<header><div><span>Scenario analysis</span><h2>Retirement projection</h2></div></header>
			{projection.status === "not_calculated" ? (
				<p className="operating-note">Projection unavailable: {projection.reason.replaceAll("_", " ")}.
					{projection.unpriced_symbols?.length ? ` Unpriced: ${projection.unpriced_symbols.join(", ")}.` : ""}
				</p>
			) : (
				<>
					<div className="advisor-success-rate">
						<span>Scenarios ending above zero</span>
						<strong>{Math.round(projection.success_rate * 100)}%</strong>
					</div>
					<div className="advisor-form-grid advisor-percentiles">
						{Object.entries(projection.ending_balance_percentiles).map(([key, value]) => (
							<div key={key}><span>{key.toUpperCase()} ending balance</span><strong>${value.toLocaleString()}</strong></div>
						))}
					</div>
					<p className="operating-note">{projection.methodology.interpretation} Correlations are not modeled.</p>
					<details>
						<summary>Assumptions and method</summary>
						<pre>{JSON.stringify(projection.methodology, null, 2)}</pre>
						<pre>{JSON.stringify(projection.assumptions, null, 2)}</pre>
					</details>
				</>
			)}
			{narrative?.content && narrative.status === "complete" && (
				<div className="advisor-retirement-narrative">
					<h3>Retirement specialist</h3>
					<pre>{narrative.content}</pre>
				</div>
			)}
		</section>
	);
}

export default RetirementProjection;
