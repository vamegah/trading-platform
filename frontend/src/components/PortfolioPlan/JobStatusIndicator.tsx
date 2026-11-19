import React from "react";

interface Job {
  job_id: string;
  status: string;
  error?: string;
}

interface Props {
  job: Job;
}

function JobStatusIndicator({ job }: Props) {
  const isError = job.status === "failed";
  return (
    <section className="panel advisor-job-status" aria-live="polite">
      <span>Analysis job</span>
      <strong>{job.job_id}</strong>
      <span className={`badge ${isError ? "review" : "healthy"}`}>{job.status}</span>
      {job.error && <p className="advisor-error">{job.error}</p>}
    </section>
  );
}

export default JobStatusIndicator;
