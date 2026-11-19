import React from "react";

function AllocationCharts({ charts }) {
	if (!charts) return null;
	const holdings = charts.top_holdings || [];
	const factors = charts.factor_exposures || [];
	const allocations = charts.allocation || {};
	const allocationPanels = [
		["asset_class", "Asset class"],
		["region", "Region"],
		["sector", "Sector"],
	];
	return (
		<section className="analysis-grid advisor-charts">
			<div className="panel">
				<header><div><span>Market value</span><h2>Largest holdings</h2></div></header>
				{holdings.length ? holdings.map((holding) => (
					<div className="advisor-bar-row" key={holding.symbol}>
						<div className="advisor-bar-label"><strong>{holding.symbol}</strong><span>{(holding.weight * 100).toFixed(1)}%</span></div>
						<div className="bar" role="img" aria-label={`${holding.symbol}, ${(holding.weight * 100).toFixed(1)} percent`}>
							<i style={{ width: `${Math.max(0, Math.min(100, holding.weight * 100))}%` }} />
						</div>
						<span>${holding.value.toLocaleString()}</span>
					</div>
				)) : <p className="operating-note">No fresh prices are available to chart.</p>}
			</div>
			<div className="panel">
				<header><div><span>Position metadata</span><h2>Factor exposure</h2></div></header>
				{factors.length ? factors.map((item) => (
					<div className="row" key={item.factor}><strong>{item.factor}</strong><span>{item.weight.toFixed(2)}</span></div>
				)) : <p className="operating-note">No factor-exposure metadata is available.</p>}
			</div>
			{allocationPanels.map(([key, title]) => (
				<div className="panel" key={key}>
					<header><div><span>Instrument classification</span><h2>{title}</h2></div></header>
					{(allocations[key] || []).length ? allocations[key].map((item) => (
						<div className="advisor-bar-row" key={item.category}>
							<div className="advisor-bar-label"><strong>{item.category.replaceAll("_", " ")}</strong><span>{(item.weight * 100).toFixed(1)}%</span></div>
							<div className="bar" role="img" aria-label={`${item.category}, ${(item.weight * 100).toFixed(1)} percent`}>
								<i style={{ width: `${Math.max(0, Math.min(100, item.weight * 100))}%` }} />
							</div>
							<span>${item.value.toLocaleString()}</span>
						</div>
					)) : <p className="operating-note">No validated {title.toLowerCase()} allocation metadata is available.</p>}
				</div>
			))}
		</section>
	);
}

export default AllocationCharts;
