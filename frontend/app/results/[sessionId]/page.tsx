"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import FeedbackCard from "@/components/FeedbackCard";
import type { SessionEndResponse } from "@/lib/api";

function scoreColor(score: number): string {
  if (score >= 8) return "text-emerald-400";
  if (score >= 6) return "text-yellow-400";
  if (score >= 4) return "text-amber-400";
  return "text-red-400";
}

export default function ResultsPage() {
  const router = useRouter();
  const { sessionId } = useParams<{ sessionId: string }>();
  const [feedback, setFeedback] = useState<SessionEndResponse | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem(`feedback-${sessionId}`);
    if (!stored) {
      router.push("/");
      return;
    }
    setFeedback(JSON.parse(stored));
  }, [sessionId, router]);

  if (!feedback) return null;

  return (
    <main className="min-h-screen bg-neutral-950 px-4 py-12">
      <div
        className="max-w-2xl mx-auto flex flex-col gap-8"
        style={{ animation: "fade-in-up 300ms cubic-bezier(0.4,0,0.2,1) forwards" }}
      >
        {/* Hero */}
        <div className="text-center flex flex-col items-center gap-4">
          <span className="text-5xl">🎉</span>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
            Interview Complete
          </h1>
          <div
            className={`text-8xl font-black tracking-tighter ${scoreColor(
              feedback.overall_score
            )}`}
          >
            {feedback.overall_score.toFixed(1)}
          </div>
          <p className="text-[11px] uppercase tracking-widest text-slate-400">
            Overall Score / 10
          </p>
        </div>

        {/* Summary */}
        <div className="bg-neutral-800 border border-neutral-700 rounded-2xl px-6 py-5">
          <p className="text-[11px] uppercase tracking-widest text-slate-400 mb-3">
            Summary
          </p>
          <p className="text-sm text-slate-300 leading-relaxed">{feedback.summary}</p>
        </div>

        {/* Strengths + Improvements */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-neutral-800 border border-l-4 border-l-emerald-500 border-neutral-700 rounded-2xl px-5 py-4">
            <p className="text-[11px] uppercase tracking-widest text-emerald-400 mb-3">
              Top Strengths
            </p>
            <ul className="flex flex-col gap-2">
              {feedback.top_strengths?.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                  <span className="text-emerald-400 mt-0.5">✓</span>
                  {s}
                </li>
              ))}
            </ul>
          </div>
          <div className="bg-neutral-800 border border-l-4 border-l-amber-500 border-neutral-700 rounded-2xl px-5 py-4">
            <p className="text-[11px] uppercase tracking-widest text-amber-400 mb-3">
              Top Improvements
            </p>
            <ul className="flex flex-col gap-2">
              {feedback.top_improvements?.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                  <span className="text-amber-400 mt-0.5">→</span>
                  {s}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Question feedback */}
        {feedback.question_feedback?.length > 0 && (
          <div className="flex flex-col gap-3">
            <p className="text-[11px] uppercase tracking-widest text-slate-400">
              Question Breakdown
            </p>
            {feedback.question_feedback.map((q, i) => (
              <FeedbackCard
                key={i}
                feedback={q}
                index={i}
                defaultOpen={i === 0}
              />
            ))}
          </div>
        )}

        {/* Footer CTAs */}
        <div className="flex gap-3 pb-8">
          <button
            onClick={() => router.push("/")}
            className="flex-1 bg-neutral-800 hover:bg-neutral-700 border border-neutral-700 text-slate-200 font-semibold rounded-xl py-4 transition-colors"
          >
            Try Again
          </button>
          <button
            onClick={() => window.print()}
            className="flex-1 bg-indigo-500 hover:bg-indigo-600 text-white font-semibold rounded-xl py-4 transition-all hover:-translate-y-0.5 hover:shadow-lg hover:shadow-indigo-500/20"
          >
            Download PDF Report
          </button>
        </div>
      </div>
    </main>
  );
}
