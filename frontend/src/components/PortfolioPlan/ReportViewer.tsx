import React from "react";

function ReportViewer({ report, llmReport }) {
	if (llmReport) {
		if (llmReport.status !== "complete" || !llmReport.content) {
			return (
				<section className="panel advisor-report">
					<header><div><span>AI narrative</span><h2>Written analysis</h2></div><span className="badge review">{llmReport.status}</span></header>
					<p className="operating-note">The deterministic findings remain available; no generated narrative was returned.</p>
				</section>
			);
		}
		return (
			<section className="panel advisor-report">
				<header><div><span>Amazon Bedrock · {llmReport.model_id}</span><h2>Written analysis</h2></div></header>
				<pre className="advisor-llm-report">{llmReport.content}</pre>
				<p className="advisor-disclosure">Generated research is educational content only. Verify its figures and sources.</p>
			</section>
		);
	}
	if (!report) return null;
	return (
		<section className="panel advisor-report">
			<header>
				<div>
					<span>Portfolio report</span>
					<h2>Findings</h2>
				</div>
				<span className={`badge ${report.status === "complete" ? "healthy" : "review"}`}>
					{report.status}
				</span>
			</header>
			<ul className="advisor-observations">
				{report.observations.map((observation) => <li key={observation}>{observation}</li>)}
			</ul>
			{report.data_warnings.length > 0 && (
				<div className="advisor-warnings">
					<h3>Market-data warnings</h3>
					{report.data_warnings.map((warning) => (
						<div className="row" key={`${warning.symbol}-${warning.reason}`}>
							<strong>{warning.symbol}</strong>
							<span>{warning.reason.replaceAll("_", " ")} · {warning.price_as_of || "no date"}</span>
						</div>
					))}
				</div>
			)}
			<p className="operating-note">{report.methodology}</p>
		</section>
	);
}

export default ReportViewer;
