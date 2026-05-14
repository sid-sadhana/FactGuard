"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { gsap } from "gsap";
import { Loader2, Link as LinkIcon, Upload } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import { createUploadJob, createYouTubeJob } from "@/lib/api-client";

type Tab = "youtube" | "upload";

export function AnalyzeForm() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("youtube");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const formRef = useRef<HTMLDivElement | null>(null);

  const shake = () => {
    if (!formRef.current) return;
    gsap.fromTo(
      formRef.current,
      { x: 0 },
      { x: -8, duration: 0.06, yoyo: true, repeat: 5, ease: "power2.inOut" },
    );
  };

  const submit = async () => {
    setError(null);
    setSubmitting(true);
    try {
      if (tab === "youtube") {
        if (!url.trim()) throw new Error("Paste a YouTube URL first.");
        const job = await createYouTubeJob(url.trim());
        router.push(`/analyze/${job.job_id}`);
      } else {
        if (!file) throw new Error("Choose a video file first.");
        const job = await createUploadJob(file);
        router.push(`/analyze/${job.job_id}`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
      shake();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div ref={formRef} className="w-full rounded-2xl border border-border bg-bg-raised/70 p-4 shadow-glow backdrop-blur sm:p-6">
      <div role="tablist" className="grid grid-cols-2 gap-1 rounded-xl bg-bg-overlay p-1 text-sm">
        <TabButton active={tab === "youtube"} onClick={() => setTab("youtube")}>
          <LinkIcon className="h-4 w-4" />
          YouTube link
        </TabButton>
        <TabButton active={tab === "upload"} onClick={() => setTab("upload")}>
          <Upload className="h-4 w-4" />
          Upload video
        </TabButton>
      </div>

      <div className="mt-5">
        {tab === "youtube" ? (
          <label className="block">
            <span className="text-xs uppercase tracking-wide text-fg-subtle">YouTube URL</span>
            <input
              type="url"
              inputMode="url"
              autoComplete="off"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=…"
              className="mt-2 w-full rounded-lg border border-border bg-bg px-3 py-2.5 text-sm outline-none transition-colors placeholder:text-fg-subtle focus:border-brand focus:ring-2 focus:ring-brand/30"
            />
          </label>
        ) : (
          <FileDrop file={file} onFile={setFile} />
        )}

        {error && (
          <p className="mt-3 rounded-lg border border-verdict-refuted/30 bg-verdict-refuted/10 px-3 py-2 text-sm text-verdict-refuted">
            {error}
          </p>
        )}

        <Button
          size="lg"
          className="mt-5 w-full"
          onClick={submit}
          disabled={submitting}
        >
          {submitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Starting analysis…
            </>
          ) : (
            <>Run fact check</>
          )}
        </Button>
      </div>
    </div>
  );
}

function TabButton({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg px-3 py-2 transition-all",
        active ? "bg-bg-raised text-fg shadow-sm" : "text-fg-muted hover:text-fg",
      )}
    >
      {children}
    </button>
  );
}

function FileDrop({ file, onFile }: { file: File | null; onFile: (f: File | null) => void }) {
  const [drag, setDrag] = useState(false);
  return (
    <label
      onDragOver={(e) => {
        e.preventDefault();
        setDrag(true);
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDrag(false);
        const f = e.dataTransfer.files?.[0];
        if (f) onFile(f);
      }}
      className={cn(
        "block cursor-pointer rounded-xl border-2 border-dashed border-border px-4 py-8 text-center transition-colors",
        drag ? "border-brand bg-brand/5" : "hover:border-fg-subtle",
      )}
    >
      <Upload className="mx-auto h-6 w-6 text-fg-subtle" />
      <p className="mt-2 text-sm">
        {file ? (
          <span className="text-fg">{file.name}</span>
        ) : (
          <>
            <span className="text-fg">Drop video here</span>{" "}
            <span className="text-fg-subtle">or click to browse</span>
          </>
        )}
      </p>
      <p className="mt-1 text-xs text-fg-subtle">MP4 · MOV · MKV · WEBM, up to 500 MB</p>
      <input
        type="file"
        accept="video/mp4,video/quicktime,video/x-matroska,video/webm,video/avi,video/x-m4v"
        className="hidden"
        onChange={(e) => onFile(e.target.files?.[0] ?? null)}
      />
    </label>
  );
}
