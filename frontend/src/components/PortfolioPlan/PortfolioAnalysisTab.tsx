import React, { useEffect, useState } from "react";
import {
	getAdvisorPortfolios,
	getPortfolioAnalysis,
	getPortfolioAdvisorConsent,
	requestPortfolioAnalysis,
	setPortfolioAdvisorConsent,
} from "../../services/api";
import AllocationCharts from "./AllocationCharts";
import ReportViewer from "./ReportViewer";
import RetirementProjection from "./RetirementProjection";
import ResearchEvidence from "./ResearchEvidence";

const initialRetirement = {
	years_until_retirement: "",
	annual_contribution: "",
	target_annual_income: "",
	years_in_retirement: "30",
	inflation_rate: "0.025",
	allocation: { equity: "", fixed_income: "", real_estate: "", commodities: "", cash: "" },
};

function PortfolioAnalysisTab() {
	const [portfolios, setPortfolios] = useState([]);
	const [portfolioId, setPortfolioId] = useState("");
	const [job, setJob] = useState(null);
	const [includeRetirement, setIncludeRetirement] = useState(false);
	const [assumptions, setAssumptions] = useState(initialRetirement);
	const [status, setStatus] = useState("loading");
	const [consent, setConsent] = useState(null);
	const [consentSaving, setConsentSaving] = useState(false);
	const [error, setError] = useState("");

	useEffect(() => {
		let active = true;
		Promise.all([getAdvisorPortfolios(), getPortfolioAdvisorConsent()])
			.then(([{ portfolios: rows }, consentState]) => {
				if (!active) return;
				setPortfolios(rows);
				setConsent(consentState);
				if (rows.length) setPortfolioId(String(rows[0].id));
				setStatus("ready");
			})
			.catch((requestError) => {
				if (!active) return;
				setError(requestError.message || "Could not load portfolios.");
				setStatus("error");
			});
		return () => {
			active = false;
		};
	}, []);

	useEffect(() => {
		if (!job?.job_id || ["completed", "failed"].includes(job.status)) return undefined;
		let active = true;
		const controller = new AbortController();
		const poll = async () => {
			try {
				const updated = await getPortfolioAnalysis(job.job_id);
				if (active) setJob(updated);
			} catch (requestError) {
				if (active) setError(requestError.message || "Could not refresh analysis status.");
			}
		};
		const interval = window.setInterval(poll, 1500);
		poll();
		return () => {
			active = false;
			controller.abort();
			window.clearInterval(interval);
		};
	}, [job?.job_id, job?.status]);

	const updateAssumption = (key, value) => {
		setAssumptions((current) => ({ ...current, [key]: value }));
	};

	const updateAllocation = (key, value) => {
		setAssumptions((current) => ({
			...current,
			allocation: { ...current.allocation, [key]: value },
		}));
	};

	const updateConsent = async (enabled) => {
		setConsentSaving(true);
		setError("");
		try {
			setConsent(await setPortfolioAdvisorConsent(enabled));
		} catch (requestError) {
			setError(requestError.message || "Could not update AI processing consent.");
		} finally {
			setConsentSaving(false);
		}
	};

	const submit = async (event) => {
		event.preventDefault();
		setError("");
		setJob(null);
		setStatus("submitting");
		try {
			const retirement = includeRetirement
				? {
						years_until_retirement: Number(assumptions.years_until_retirement),
						annual_contribution: Number(assumptions.annual_contribution),
						target_annual_income: Number(assumptions.target_annual_income),
						years_in_retirement: Number(assumptions.years_in_retirement),
						inflation_rate: Number(assumptions.inflation_rate),
						allocation: Object.fromEntries(
							Object.entries(assumptions.allocation).map(([key, value]) => [key, Number(value || 0)])
						),
						simulations: 1000,
						seed: 0,
					}
				: null;
			const created = await requestPortfolioAnalysis({
				portfolio_id: Number(portfolioId),
				idempotency_key: `advisor-${crypto.randomUUID()}`,
				max_market_data_age_days: 5,
				use_llm: Boolean(consent?.provider_enabled && consent.allow_bedrock_processing),
				retirement,
			});
			setJob(created);
			setStatus(created.status);
		} catch (requestError) {
			setError(requestError.message || "Analysis request failed.");
			setStatus("error");
		}
	};

	const retirementFieldsValid =
		Number.isFinite(Number(assumptions.years_until_retirement)) &&
		assumptions.years_until_retirement !== "" &&
		Number.isFinite(Number(assumptions.annual_contribution)) &&
		assumptions.annual_contribution !== "" &&
		Number(assumptions.target_annual_income) > 0 &&
		Object.values(assumptions.allocation).every((value) => value !== "") &&
		Math.abs(Object.values(assumptions.allocation).reduce((sum, value) => sum + Number(value || 0), 0) - 1) < 0.001;

	const result = job?.result;
	const busy = ["loading", "submitting", "pending", "running", "retrying"].includes(status);

	return (
		<section className="operating-stack portfolio-advisor">
			<form className="panel advisor-request" onSubmit={submit}>
				<header>
					<div>
						<span>Portfolio review</span>
						<h2>Analysis request</h2>
					</div>
					<span className={`badge ${status === "error" || job?.status === "failed" ? "review" : "healthy"}`}>
						{status}
					</span>
				</header>
				{portfolios.length ? (
					<div className="advisor-form-grid">
						<label>
							Portfolio
							<select value={portfolioId} onChange={(event) => setPortfolioId(event.target.value)}>
								{portfolios.map((portfolio) => (
									<option key={portfolio.id} value={portfolio.id}>
										{portfolio.name} · {portfolio.risk_profile}
									</option>
								))}
							</select>
						</label>
						<label className="advisor-check">
							<input
								checked={includeRetirement}
								type="checkbox"
								onChange={(event) => setIncludeRetirement(event.target.checked)}
							/>
							Include retirement scenarios
						</label>
					</div>
				) : (
					<p className="operating-note">No portfolios are available for this account.</p>
				)}
				{includeRetirement && (
					<fieldset className="advisor-assumptions">
						<legend>Retirement assumptions</legend>
						<div className="advisor-form-grid">
							{[
								["years_until_retirement", "Years until retirement", "0.1", "70"],
								["annual_contribution", "Annual contribution ($)", "0", "10000000"],
								["target_annual_income", "Target annual income ($)", "1", "10000000"],
								["years_in_retirement", "Years in retirement", "1", "70"],
								["inflation_rate", "Annual inflation rate", "0", "0.2"],
							].map(([key, label, min, max]) => (
								<label key={key}>
									{label}
									<input
										max={max}
										min={min}
										required
										step={key === "inflation_rate" ? "0.001" : "1"}
										type="number"
										value={assumptions[key]}
										onChange={(event) => updateAssumption(key, event.target.value)}
									/>
								</label>
							))}
						</div>
						<p className="operating-note">Allocation weights must sum to 1. Enter each asset-class weight as a decimal.</p>
						<div className="advisor-form-grid advisor-allocation-grid">
							{Object.entries(assumptions.allocation).map(([key, value]) => (
								<label key={key}>
									{key.replace("_", " ")}
									<input
										max="1"
										min="0"
										required
										step="0.01"
										type="number"
										value={value}
										onChange={(event) => updateAllocation(key, event.target.value)}
									/>
								</label>
							))}
						</div>
					</fieldset>
				)}
				{consent?.provider_enabled && (
					<div className="advisor-consent">
						<label className="advisor-check">
							<input
								checked={Boolean(consent.allow_bedrock_processing)}
								disabled={consentSaving || busy}
								type="checkbox"
								onChange={(event) => updateConsent(event.target.checked)}
							/>
							Allow this service to send the analysis snapshot to Amazon Bedrock for a written narrative
						</label>
						<p className="operating-note">{consent.disclosure}</p>
					</div>
				)}
				{!consent?.provider_enabled && (
					<p className="operating-note">Written AI narratives are disabled by deployment configuration. Deterministic analysis remains available.</p>
				)}
				{error && <p className="advisor-error" role="alert">{error}</p>}
				<button disabled={busy || !portfolioId || (includeRetirement && !retirementFieldsValid)} type="submit">
					{busy ? "Analysis in progress" : "Request analysis"}
				</button>
				<p className="advisor-disclosure">
					Research and educational analysis only. Outputs do not place or authorize trades.
				</p>
			</form>

			{job && (
				<>
					<section className="panel advisor-job-status" aria-live="polite">
						<span>Analysis job</span>
						<strong>{job.job_id}</strong>
						<span>Status: {job.status}</span>
						{job.error && <p className="advisor-error">{job.error}</p>}
					</section>
					{result && (
						<>
							<section className="metrics advisor-metrics">
								<article className="metric"><span>Known market value</span><strong>${result.portfolio.known_market_value.toLocaleString()}</strong></article>
								<article className="metric"><span>Positions priced</span><strong>{result.portfolio.priced_position_count}/{result.portfolio.position_count}</strong></article>
								<article className="metric"><span>Price coverage</span><strong>{Math.round(result.portfolio.price_coverage * 100)}%</strong></article>
								<article className="metric"><span>Largest holding</span><strong>{Math.round(result.portfolio.largest_position_weight * 100)}%</strong></article>
							</section>
							<ReportViewer report={result.report} />
							{result.llm_report && <ReportViewer llmReport={result.llm_report} />}
							<ResearchEvidence research={result.research} />
							<AllocationCharts charts={result.charts} />
							<RetirementProjection projection={result.retirement} narrative={result.llm_retirement} />
							{result.multi_agent && (
								<section className="panel advisor-agent-status">
									<header><div><span>Workflow</span><h2>Agent stages</h2></div></header>
									{Object.entries(result.multi_agent).map(([name, stage]) => (
										<div className="row" key={name}><span>{name.replaceAll("_", " ")}</span><strong>{stage}</strong></div>
									))}
								</section>
							)}
							<p className="advisor-source-meta">
								Snapshot {result.source_snapshot.snapshot_id} · Captured {new Date(result.source_snapshot.captured_at).toLocaleString()} ·
								Freshness window {result.source_snapshot.max_market_data_age_days} days
							</p>
							<p className="advisor-disclosure">{result.disclosure}</p>
						</>
					)}
				</>
			)}
		</section>
	);
}

export default PortfolioAnalysisTab;
