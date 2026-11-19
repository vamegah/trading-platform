import React from "react";

function ResearchEvidence({ research }) {
  if (!research || research.status === "not_requested") return null;
  return (
    <section className="panel advisor-research-evidence">
      <header>
        <div><span>Alex Researcher</span><h2>Cited research</h2></div>
        <span className={`badge ${research.status === "ingested" ? "healthy" : "review"}`}>{research.status}</span>
      </header>
      {research.reason && <p className="operating-note">{research.reason.replaceAll("_", " ")}</p>}
      {(research.snapshots || []).map((snapshot) => (
        <article className="research-snapshot" key={snapshot.snapshot_id}>
          <header><strong>{snapshot.symbol}</strong><span>{snapshot.snapshot_id}</span></header>
          <p>{snapshot.summary}</p>
          <ul>
            {(snapshot.source_refs || []).map((source) => (
              <li key={`${snapshot.snapshot_id}-${source.url}`}>
                <a href={source.url} rel="noreferrer" target="_blank">
                  {source.name}{source.published_at ? ` · ${source.published_at}` : ""}
                </a>
              </li>
            ))}
          </ul>
        </article>
      ))}
      {research.run_id && <p className="advisor-source-meta">Research run {research.run_id}</p>}
    </section>
  );
}

export default ResearchEvidence;