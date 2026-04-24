"use client";

import { useRef, useState, useCallback } from "react";

export type VoiceState = "idle" | "listening" | "processing" | "error";

interface VoiceButtonProps {
  onTranscript: (text: string) => void;
  disabled?: boolean;
  transcribeAudio: (blob: Blob) => Promise<{ text: string }>;
  onVoiceStateChange?: (state: VoiceState) => void;
}

export default function VoiceButton({
  onTranscript,
  disabled = false,
  transcribeAudio,
  onVoiceStateChange,
}: VoiceButtonProps) {
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");

  const setVS = useCallback((s: VoiceState) => {
    setVoiceState(s);
    onVoiceStateChange?.(s);
  }, [onVoiceStateChange]);
  const [errorMsg, setErrorMsg] = useState<string>("");
  const [fallbackText, setFallbackText] = useState("");
  const [showFallback, setShowFallback] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    if (disabled || voiceState !== "idle") return;
    setErrorMsg("");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm", audioBitsPerSecond: 16000 });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        setVS("processing");
        try {
          const result = await transcribeAudio(blob);
          if (result.text.trim()) {
            onTranscript(result.text.trim());
          } else {
            setVS("error");
            setErrorMsg("No speech detected");
            setTimeout(() => setVS("idle"), 2000);
            return;
          }
        } catch {
          setVS("error");
          setErrorMsg("Transcription failed");
          setTimeout(() => setVS("idle"), 2000);
          return;
        }
        setVS("idle");
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setVS("listening");
    } catch {
      setShowFallback(true);
    }
  }, [disabled, voiceState, onTranscript, transcribeAudio, setVS]);

  const stopRecording = useCallback(() => {
    if (voiceState !== "listening") return;
    mediaRecorderRef.current?.stop();
  }, [voiceState]);

  const submitFallback = () => {
    if (fallbackText.trim()) {
      onTranscript(fallbackText.trim());
      setFallbackText("");
    }
  };

  const buttonConfig = {
    idle: {
      bg: "bg-indigo-500 hover:bg-indigo-600",
      icon: "🎤",
      label: "HOLD TO TALK",
      pulse: false,
    },
    listening: {
      bg: "bg-indigo-600",
      icon: "🎤",
      label: "LISTENING…",
      pulse: true,
    },
    processing: {
      bg: "bg-amber-500",
      icon: "⏳",
      label: "PROCESSING…",
      pulse: false,
    },
    error: {
      bg: "bg-red-500",
      icon: "❌",
      label: errorMsg || "ERROR",
      pulse: false,
    },
  }[voiceState];

  if (showFallback) {
    return (
      <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-40 flex flex-col items-center gap-2 w-80">
        <textarea
          className="w-full bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-3 text-slate-100 text-sm resize-none focus:outline-none focus:border-indigo-500"
          rows={3}
          placeholder="Type your response here…"
          value={fallbackText}
          onChange={(e) => setFallbackText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submitFallback();
            }
          }}
          disabled={disabled}
        />
        <button
          onClick={submitFallback}
          disabled={disabled || !fallbackText.trim()}
          className="w-full bg-indigo-500 hover:bg-indigo-600 disabled:opacity-40 text-white rounded-xl py-3 text-sm font-semibold transition-colors"
        >
          Send
        </button>
      </div>
    );
  }

  return (
    <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-40 flex flex-col items-center gap-3">
      <div className="relative flex items-center justify-center">
        {buttonConfig.pulse && (
          <>
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="absolute w-[120px] h-[120px] rounded-full bg-indigo-500/30"
                style={{
                  animation: `ring-pulse 1.2s ease-out ${i * 200}ms infinite`,
                }}
              />
            ))}
          </>
        )}
        <button
          className={`relative w-[120px] h-[120px] rounded-full ${buttonConfig.bg} text-white flex flex-col items-center justify-center gap-1 shadow-lg transition-all duration-150 active:scale-95 disabled:opacity-40 select-none`}
          style={{
            transition: "transform 150ms, box-shadow 150ms",
          }}
          onMouseDown={startRecording}
          onMouseUp={stopRecording}
          onTouchStart={(e) => {
            e.preventDefault();
            startRecording();
          }}
          onTouchEnd={(e) => {
            e.preventDefault();
            stopRecording();
          }}
          disabled={disabled || voiceState === "processing"}
        >
          <span className="text-2xl">{buttonConfig.icon}</span>
          <span className="text-[9px] font-bold tracking-widest">
            {buttonConfig.label}
          </span>
        </button>
      </div>
    </div>
  );
}
