export type JobStage =
  | "pending"
  | "ingesting"
  | "transcribing"
  | "extracting_claims"
  | "retrieving_evidence"
  | "verifying"
  | "evaluating"
  | "completed"
  | "failed";

export type Verdict = "supported" | "refuted" | "unverifiable";

export interface TranscriptSegment {
  start: number;
  duration: number;
  text: string;
}

export interface Claim {
  id: number;
  text: string;
  source: "transcript";
  needs_search: boolean;
  prelim_answer: string | null;
}

export interface Evidence {
  url: string;
  title: string;
  snippet: string;
  score: number;
}

export interface ClaimVerification {
  claim: Claim;
  verdict: Verdict;
  confidence: number;
  reasoning: string;
  citations: Evidence[];
}

export interface RagasScores {
  faithfulness: number | null;
  answer_relevancy: number | null;
  context_precision: number | null;
  context_recall: number | null;
}

export interface JobResult {
  job_id: string;
  source: "youtube" | "upload";
  source_ref: string;
  title: string | null;
  duration_seconds: number | null;
  transcript: string;
  claims: Claim[];
  verifications: ClaimVerification[];
  ragas: RagasScores | null;
  overall_score: number;
  summary: string;
  summary_citations: Evidence[];
}

export interface JobProgress {
  stage: JobStage;
  message: string;
  percent: number;
}

export interface Job {
  job_id: string;
  source: "youtube" | "upload";
  source_ref: string;
  created_at: string;
  updated_at: string;
  progress: JobProgress;
  result: JobResult | null;
  error: string | null;
}

export const STAGE_LABEL: Record<JobStage, string> = {
  pending: "Queued",
  ingesting: "Fetching video",
  transcribing: "Transcribing audio",
  extracting_claims: "Picking checkworthy points",
  retrieving_evidence: "Searching web sources",
  verifying: "Fact-checking each point against the web",
  evaluating: "Finalizing",
  completed: "Complete",
  failed: "Failed",
};

export const STAGE_ORDER: JobStage[] = [
  "ingesting",
  "transcribing",
  "extracting_claims",
  "verifying",
  "evaluating",
  "completed",
];
