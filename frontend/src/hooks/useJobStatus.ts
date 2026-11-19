import { useEffect, useState } from "react";
import { getPortfolioAnalysis } from "../services/api";

type JobStatus = "pending" | "running" | "retrying" | "completed" | "failed";

interface Job {
  job_id: string;
  status: JobStatus;
  result?: any;
  error?: string;
}

const TERMINAL: JobStatus[] = ["completed", "failed"];
const POLL_MS = 1500;

export function useJobStatus(jobId: string | null) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    if (!jobId) return;
    let active = true;

    const poll = async () => {
      try {
        const data = await getPortfolioAnalysis(jobId);
        if (active) setJob(data);
      } catch (err: any) {
        if (active) setError(err.message ?? "Failed to fetch job status.");
      }
    };

    poll();
    const interval = window.setInterval(() => {
      if (job && TERMINAL.includes(job.status)) {
        window.clearInterval(interval);
        return;
      }
      poll();
    }, POLL_MS);

    return () => {
      active = false;
      window.clearInterval(interval);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  return { job, error };
}
