"use client";

interface WaveformProps {
  label: string;
}

function Waveform({ label }: WaveformProps) {
  return (
    <div className="flex items-center gap-2 py-1">
      <div className="flex items-end gap-[3px] h-5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-[3px] rounded-full bg-indigo-400"
            style={{
              height: "4px",
              animation: `wave 600ms ease-in-out ${i * 200}ms infinite`,
            }}
          />
        ))}
      </div>
      <span className="text-xs text-slate-400">{label}</span>
    </div>
  );
}

function PulsingDot() {
  return (
    <div className="flex items-center gap-2 py-1">
      <span
        className="w-2 h-2 rounded-full bg-indigo-400"
        style={{ animation: "ring-pulse 1.2s ease-out infinite" }}
      />
      <span className="text-xs text-slate-400">Waiting for your response…</span>
    </div>
  );
}

export type BubbleState = "idle" | "speaking" | "waiting";

interface ChatBubbleProps {
  role: "ai" | "user";
  content: string;
  speakerName?: string;
  state?: BubbleState;
  animateIn?: boolean;
}

export default function ChatBubble({
  role,
  content,
  speakerName = "AI",
  state = "idle",
  animateIn = true,
}: ChatBubbleProps) {
  const isAI = role === "ai";

  return (
    <div
      className={`flex w-full mb-4 ${isAI ? "justify-start" : "justify-end"}`}
      style={animateIn ? { animation: "fade-in-up 300ms cubic-bezier(0.4,0,0.2,1) forwards" } : undefined}
    >
      <div
        className={`max-w-[90%] rounded-2xl px-4 py-3 ${
          isAI
            ? "bg-neutral-800 border border-neutral-700 rounded-tl-sm"
            : "bg-indigo-500/90 text-white rounded-tr-sm"
        }`}
      >
        {isAI && (
          <p className="text-[10px] uppercase tracking-widest text-slate-400 mb-1">
            {speakerName}
          </p>
        )}
        <p className="text-sm leading-relaxed text-slate-100">{content}</p>
        {isAI && state === "speaking" && (
          <Waveform label={`${speakerName} is speaking…`} />
        )}
        {isAI && state === "waiting" && <PulsingDot />}
      </div>
    </div>
  );
}
