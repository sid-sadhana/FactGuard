"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { ProgressTimeline } from "@/components/analyze/ProgressTimeline";
import { Footer } from "@/components/site/Footer";
import { Header } from "@/components/site/Header";
import { fetchJob, jobEventStream } from "@/lib/api-client";
import type { Job } from "@/types/api";

import { ResultsView } from "@/components/results/ResultsView";

export default function JobPage() {
  const params = useParams<{ jobId: string }>();
  const jobId = params?.jobId as string;
  const [job, setJob] = useState<Job | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    fetchJob(jobId)
      .then((j) => !cancelled && setJob(j))
      .catch((e) => !cancelled && setErr(e instanceof Error ? e.message : "Failed to load"));
    const close = jobEventStream(jobId, (j) => {
      if (!cancelled) setJob(j);
    });
    return () => {
      cancelled = true;
      close();
    };
  }, [jobId]);

  return (
    <>
      <Header />
      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
        <div className="mb-6">
          <p className="text-xs uppercase tracking-[0.2em] text-brand">Job</p>
          <h1 className="mt-1 truncate text-2xl font-semibold tracking-tight sm:text-3xl">
            {job?.result?.title || job?.source_ref || jobId}
          </h1>
          <p className="mt-1 truncate text-sm text-fg-subtle">id: {jobId}</p>
        </div>

        {err && (
          <div className="rounded-lg border border-verdict-refuted/30 bg-verdict-refuted/10 px-4 py-3 text-sm text-verdict-refuted">
            {err}
          </div>
        )}

        {job && (
          <>
            <ProgressTimeline
              stage={job.progress.stage}
              percent={job.progress.percent}
              message={job.progress.message || job.error || ""}
            />

            {job.result && <ResultsView job={job} />}
          </>
        )}
      </main>
      <Footer />
    </>
  );
}
