import { AnalyzeForm } from "@/components/analyze/AnalyzeForm";
import { Footer } from "@/components/site/Footer";
import { Header } from "@/components/site/Header";

export default function AnalyzePage() {
  return (
    <>
      <Header />
      <main className="bg-glow">
        <div className="mx-auto grid min-h-[calc(100vh-3.5rem)] max-w-6xl place-items-center px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
          <div className="w-full max-w-xl">
            <p className="text-xs uppercase tracking-[0.2em] text-brand">Start</p>
            <h1 className="mt-2 text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
              Run a fact check.
            </h1>
            <p className="mt-3 text-fg-muted">
              Paste a YouTube URL or upload a clip. We&apos;ll extract claims,
              search the web for evidence, and score factual accuracy.
            </p>
            <div className="mt-8">
              <AnalyzeForm />
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
