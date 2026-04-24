"use client";

import { useState } from "react";
import StarScoreBar from "./StarScoreBar";
import type { QuestionFeedback } from "@/lib/api";

interface FeedbackCardProps {
  feedback: QuestionFeedback;
  index: number;
  defaultOpen?: boolean;
}

export default function FeedbackCard({
  feedback,
  index,
  defaultOpen = false,
}: FeedbackCardProps) {
  const [open, setOpen] = useState(defaultOpen);

  const starEntries = [
    ["Situation", feedback.star_scores.situation],
    ["Task", feedback.star_scores.task],
    ["Action", feedback.star_scores.action],
    ["Result", feedback.star_scores.result],
  ] as const;

  const avgScore =
    (feedback.star_scores.situation +
      feedback.star_scores.task +
      feedback.star_scores.action +
      feedback.star_scores.result) /
    4;

  return (
    <div className="bg-neutral-800 border border-neutral-700 rounded-2xl overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-neutral-700/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-[11px] uppercase tracking-widest text-slate-400">
            Q{index + 1}
          </span>
          <span className="text-sm font-medium text-slate-200 line-clamp-1">
            {feedback.question}
          </span>
        </div>
        <div className="flex items-center gap-3 ml-4 shrink-0">
          <span className="text-sm font-bold text-slate-200">
            {avgScore.toFixed(1)}
          </span>
          <span className="text-slate-400 text-sm">{open ? "▲" : "▼"}</span>
        </div>
      </button>

      {open && (
        <div
          className="px-5 pb-5 flex flex-col gap-4"
          style={{ animation: "fade-in-up 300ms cubic-bezier(0.4,0,0.2,1) forwards" }}
        >
          <div className="flex flex-col gap-3">
            {starEntries.map(([label, score], i) => (
              <StarScoreBar key={label} label={label} score={score} index={i} />
            ))}
          </div>

          {feedback.user_answer && (
            <div className="bg-neutral-700/30 rounded-xl px-4 py-3">
              <p className="text-[11px] uppercase tracking-widest text-slate-400 mb-1">
                Your Answer
              </p>
              <p className="text-sm text-slate-300 italic leading-relaxed">
                {feedback.user_answer}
              </p>
            </div>
          )}

          {feedback.strengths?.length > 0 && (
            <div>
              <p className="text-[11px] uppercase tracking-widest text-emerald-400 mb-2">
                Strengths
              </p>
              <ul className="flex flex-col gap-1">
                {feedback.strengths.map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                    <span className="text-emerald-400 mt-0.5">✓</span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {feedback.improvements?.length > 0 && (
            <div>
              <p className="text-[11px] uppercase tracking-widest text-amber-400 mb-2">
                Improvements
              </p>
              <ul className="flex flex-col gap-1">
                {feedback.improvements.map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                    <span className="text-amber-400 mt-0.5">→</span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
