"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import ChatBubble, { BubbleState } from "@/components/ChatBubble";
import VoiceButton from "@/components/VoiceButton";
import { respond, endSession, textToSpeech, transcribe } from "@/lib/api";

interface Message {
  id: string;
  role: "ai" | "user";
  content: string;
  state?: BubbleState;
}

function playBlob(blob: Blob): Promise<void> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.onended = () => {
      URL.revokeObjectURL(url);
      resolve();
    };
    audio.onerror = reject;
    audio.play().catch(reject);
  });
}

export default function InterviewPage() {
  const router = useRouter();
  const { sessionId } = useParams<{ sessionId: string }>();

  const [messages, setMessages] = useState<Message[]>([]);
  const [stage, setStage] = useState("intro");
  const [interviewComplete, setInterviewComplete] = useState(false);
  const [aiSpeaking, setAiSpeaking] = useState(false);
  const [waitingForUser, setWaitingForUser] = useState(false);
  const [voiceDisabled, setVoiceDisabled] = useState(true);
  const [elapsed, setElapsed] = useState(0);
  const [endingSession, setEndingSession] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const startTimeRef = useRef(Date.now());
  const lastMsgIdRef = useRef<string | null>(null);

  // Timer
  useEffect(() => {
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  const stageLabel = () => {
    if (stage === "intro") return "Intro";
    if (stage === "open_qa") return "Open Q&A";
    const match = stage.match(/question_(\d+)/);
    if (match) return `Q${match[1]}`;
    return stage;
  };

  const addMessage = useCallback((msg: Omit<Message, "id">): string => {
    const id = crypto.randomUUID();
    setMessages((prev) => [...prev, { ...msg, id }]);
    lastMsgIdRef.current = id;
    return id;
  }, []);

  const updateLastAiState = useCallback((state: BubbleState) => {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === lastMsgIdRef.current ? { ...m, state } : m
      )
    );
  }, []);

  const speakAndWait = useCallback(
    async (text: string, speakerName: string) => {
      const id = addMessage({ role: "ai", content: text, state: "speaking" });
      lastMsgIdRef.current = id;
      setAiSpeaking(true);
      setVoiceDisabled(true);

      try {
        const blob = await textToSpeech(text);
        await playBlob(blob);
      } catch {
        // If TTS fails, just continue
      }

      setAiSpeaking(false);
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, state: "waiting" } : m))
      );
      setWaitingForUser(true);
      setVoiceDisabled(false);
    },
    [addMessage]
  );

  // On mount: load intro from localStorage and play
  useEffect(() => {
    const stored = localStorage.getItem(`session-${sessionId}`);
    if (!stored) {
      router.push("/");
      return;
    }
    const { intro_message, interviewer_persona } = JSON.parse(stored);
    const speakerName = interviewer_persona?.split(" ")[0] ?? "AI";

    speakAndWait(intro_message, speakerName);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleTranscript = useCallback(
    async (text: string) => {
      if (voiceDisabled) return;
      setVoiceDisabled(true);
      setWaitingForUser(false);

      // Mark previous AI bubble as idle
      updateLastAiState("idle");

      addMessage({ role: "user", content: text });

      try {
        const data = await respond(sessionId, text, stage);
        setStage(data.stage);
        setInterviewComplete(data.interview_complete);

        const stored = localStorage.getItem(`session-${sessionId}`);
        const persona = stored ? JSON.parse(stored).interviewer_persona : "";
        const speakerName = persona?.split(" ")[0] ?? "AI";

        if (data.interview_complete) {
          // Show final message without waiting for response
          addMessage({ role: "ai", content: data.ai_message, state: "idle" });
          try {
            const blob = await textToSpeech(data.ai_message);
            await playBlob(blob);
          } catch {}
          setVoiceDisabled(true);
        } else {
          await speakAndWait(data.ai_message, speakerName);
        }
      } catch (err) {
        addMessage({
          role: "ai",
          content: "Something went wrong. Please try again.",
          state: "idle",
        });
        setVoiceDisabled(false);
      }
    },
    [voiceDisabled, sessionId, stage, addMessage, updateLastAiState, speakAndWait]
  );

  const handleGetFeedback = async () => {
    setEndingSession(true);
    try {
      const feedback = await endSession(sessionId);
      localStorage.setItem(`feedback-${sessionId}`, JSON.stringify(feedback));
      router.push(`/results/${sessionId}`);
    } catch {
      setEndingSession(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-neutral-950">
      {/* Header */}
      <header className="sticky top-0 z-30 bg-neutral-950/90 backdrop-blur border-b border-neutral-800 px-4 py-3 flex items-center justify-between">
        <button
          onClick={() => router.push("/")}
          className="text-slate-400 hover:text-slate-200 transition-colors text-sm"
        >
          ← Back
        </button>
        <div className="flex items-center gap-3">
          <span className="bg-indigo-500/10 text-indigo-300 text-[11px] uppercase tracking-widest px-3 py-1 rounded-full border border-indigo-500/20">
            {stageLabel()}
          </span>
          <span className="text-slate-400 text-sm tabular-nums">
            {formatTime(elapsed)}
          </span>
        </div>
      </header>

      {/* Chat */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-2xl mx-auto">
          {messages.map((msg) => {
            const stored = localStorage.getItem(`session-${sessionId}`);
            const persona = stored ? JSON.parse(stored).interviewer_persona : "";
            const speakerName = persona?.split(" ")[0] ?? "AI";
            return (
              <ChatBubble
                key={msg.id}
                role={msg.role}
                content={msg.content}
                speakerName={speakerName}
                state={msg.state}
              />
            );
          })}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Feedback CTA */}
      {interviewComplete && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-40">
          <button
            onClick={handleGetFeedback}
            disabled={endingSession}
            className="bg-indigo-500 hover:bg-indigo-600 disabled:opacity-60 text-white font-semibold rounded-2xl px-8 py-4 shadow-xl shadow-indigo-500/20 transition-all hover:-translate-y-0.5"
          >
            {endingSession ? "Generating feedback…" : "Get Feedback →"}
          </button>
        </div>
      )}

      {/* Voice button */}
      {!interviewComplete && (
        <VoiceButton
          onTranscript={handleTranscript}
          disabled={voiceDisabled}
          transcribeAudio={transcribe}
        />
      )}

      {/* Bottom padding for voice button */}
      <div className="h-40" />
    </div>
  );
}
