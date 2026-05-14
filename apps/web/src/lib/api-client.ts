import type { Job } from "@/types/api";

const BASE = "/api/proxy";

export async function createYouTubeJob(url: string): Promise<Job> {
  const r = await fetch(`${BASE}/analyze/youtube`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!r.ok) throw new Error((await r.json()).detail || "Failed to start job");
  return r.json();
}

export async function createUploadJob(file: File): Promise<Job> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("filename", file.name);
  const r = await fetch(`${BASE}/analyze/upload`, { method: "POST", body: fd });
  if (!r.ok) throw new Error((await r.json()).detail || "Failed to start job");
  return r.json();
}

export async function fetchJob(jobId: string): Promise<Job> {
  const r = await fetch(`${BASE}/jobs/${jobId}`, { cache: "no-store" });
  if (!r.ok) throw new Error("Job not found");
  return r.json();
}

export function jobEventStream(jobId: string, onJob: (j: Job) => void): () => void {
  const es = new EventSource(`${BASE}/jobs/${jobId}/events`);
  es.addEventListener("job", (e) => {
    try {
      onJob(JSON.parse((e as MessageEvent).data) as Job);
    } catch {
      /* noop */
    }
  });
  return () => es.close();
}
