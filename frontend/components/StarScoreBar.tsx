"use client";

import { useEffect, useRef, useState } from "react";

interface StarScoreBarProps {
  label: string;
  score: number; // 0–10
  index?: number; // stagger delay
}

function scoreColor(score: number): string {
  if (score >= 8) return "bg-emerald-500";
  if (score >= 6) return "bg-yellow-400";
  if (score >= 4) return "bg-amber-500";
  return "bg-red-500";
}

export default function StarScoreBar({
  label,
  score,
  index = 0,
}: StarScoreBarProps) {
  const [width, setWidth] = useState(0);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setTimeout(() => setWidth((score / 10) * 100), index * 100);
          observer.disconnect();
        }
      },
      { threshold: 0.5 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [score, index]);

  return (
    <div ref={ref} className="flex flex-col gap-1">
      <div className="flex justify-between items-center">
        <span className="text-[11px] uppercase tracking-widest text-slate-400">
          {label}
        </span>
        <span className="text-sm font-bold text-slate-200">
          {score.toFixed(1)}
        </span>
      </div>
      <div className="h-2 w-full bg-neutral-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-none ${scoreColor(score)}`}
          style={{
            width: `${width}%`,
            transition: "width 800ms cubic-bezier(0.4,0,0.2,1)",
          }}
        />
      </div>
    </div>
  );
}
