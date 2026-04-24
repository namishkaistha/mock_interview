"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import InterviewBlob, { BlobState } from "@/components/InterviewBlob";
import VoiceButton from "@/components/VoiceButton";
import { respondStream, endSession, textToSpeech, transcribe } from "@/lib/api";

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

/** Strip stage directions like *nods thoughtfully* and collapse extra spaces. */
function stripActions(text: string): string {
  return text.replace(/\*[^*]+\*/g, " ").replace(/\s+/g, " ").trim();
}

export default function InterviewPage() {
  const router = useRouter();
  const { sessionId } = useParams<{ sessionId: string }>();

  const [blobState, setBlobState] = useState<BlobState>("idle");
  const [caption, setCaption] = useState<string>("");
  const [captionVisible, setCaptionVisible] = useState(false);

  const [stage, setStage] = useState("intro");
  const [interviewComplete, setInterviewComplete] = useState(false);
  const [voiceDisabled, setVoiceDisabled] = useState(true);
  const [elapsed, setElapsed] = useState(0);
  const [endingSession, setEndingSession] = useState(false);

  const startTimeRef = useRef(Date.now());
  const introPlayedRef = useRef(false);

  // Ordered TTS promise queue — preserves sentence playback order even when
  // shorter sentences resolve faster than earlier longer ones.
  const ttsQueueRef = useRef<Promise<Blob>[]>([]);
  const isPlayingRef = useRef(false);

  const drainQueue = useCallback(async () => {
    if (isPlayingRef.current) return;
    isPlayingRef.current = true;
    while (ttsQueueRef.current.length > 0) {
      const blobPromise = ttsQueueRef.current.shift()!;
      await blobPromise.then((blob) => playBlob(blob)).catch(() => {});
    }
    isPlayingRef.current = false;
  }, []);

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

  const showCaption = useCallback((text: string) => {
    setCaption(text);
    setCaptionVisible(true);
  }, []);

  const hideCaption = useCallback(() => {
    setCaptionVisible(false);
    setTimeout(() => setCaption(""), 400);
  }, []);

  const speakAndWait = useCallback(
    async (text: string) => {
      const cleaned = stripActions(text);
      showCaption(cleaned);
      setBlobState("speaking");
      setVoiceDisabled(true);

      try {
        const audioBlob = await textToSpeech(cleaned);
        await playBlob(audioBlob);
      } catch {
        // TTS failed — wait a moment so the caption is readable
        await new Promise((r) => setTimeout(r, Math.min(cleaned.length * 50, 4000)));
      }

      setBlobState("idle");
      setVoiceDisabled(false);
    },
    [showCaption]
  );

  // On mount: play intro
  useEffect(() => {
    if (introPlayedRef.current) return;
    introPlayedRef.current = true;

    const stored = localStorage.getItem(`session-${sessionId}`);
    if (!stored) {
      router.push("/");
      return;
    }
    const { intro_message } = JSON.parse(stored);
    speakAndWait(intro_message);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const handleTranscript = useCallback(
    async (text: string) => {
      if (voiceDisabled) return;
      setVoiceDisabled(true);
      hideCaption();
      setBlobState("processing");

      // Reset TTS queue
      ttsQueueRef.current = [];
      isPlayingRef.current = false;

      try {
        let fullText = "";
        let sentenceBuffer = "";
        let streamDone = false;
        let finalStage = stage;
        let finalComplete = false;

        // Regex for sentence boundaries
        const SENTENCE_END = /([.!?])\s/;

        const flushSentence = (sentence: string) => {
          // Strip action descriptions like *nods thoughtfully* before TTS
          const cleaned = stripActions(sentence);
          if (!cleaned) return;
          if (fullText === "") showCaption(cleaned);
          setBlobState("speaking");
          // Push TTS promise in order — drainQueue awaits them sequentially,
          // so playback is always in sentence order regardless of network timing.
          ttsQueueRef.current.push(
            textToSpeech(cleaned).catch(() => new Blob([], { type: "audio/mpeg" }))
          );
          drainQueue();
        };

        for await (const event of respondStream(sessionId, text, stage)) {
          if (event.type === "token") {
            fullText += event.text;
            sentenceBuffer += event.text;

            // Flush complete sentences as they arrive
            let match: RegExpExecArray | null;
            while ((match = SENTENCE_END.exec(sentenceBuffer)) !== null) {
              const end = match.index + 1;
              flushSentence(sentenceBuffer.slice(0, end));
              sentenceBuffer = sentenceBuffer.slice(end + 1);
            }
          } else if (event.type === "done") {
            finalStage = event.stage;
            finalComplete = event.interview_complete;
            streamDone = true;
          }
        }

        // Flush any remaining text after stream ends
        if (sentenceBuffer.trim()) {
          flushSentence(sentenceBuffer.trim());
        }

        // Update caption with full text once stream is done (strip action descriptions)
        if (fullText.trim()) showCaption(stripActions(fullText));

        // Wait for all queued audio to finish playing
        await new Promise<void>((resolve) => {
          const check = () => {
            if (!isPlayingRef.current && ttsQueueRef.current.length === 0) {
              resolve();
            } else {
              setTimeout(check, 100);
            }
          };
          check();
        });

        setStage(finalStage);
        setInterviewComplete(finalComplete);

        if (finalComplete) {
          setBlobState("idle");
          setVoiceDisabled(true);
        } else {
          setBlobState("idle");
          setVoiceDisabled(false);
        }
      } catch {
        showCaption("Something went wrong. Please try again.");
        setBlobState("idle");
        setVoiceDisabled(false);
      }
    },
    [voiceDisabled, sessionId, stage, showCaption, hideCaption, drainQueue]
  );

  const handleGetFeedback = useCallback(async () => {
    setEndingSession(true);
    try {
      const feedback = await endSession(sessionId);
      localStorage.setItem(`feedback-${sessionId}`, JSON.stringify(feedback));
      router.push(`/results/${sessionId}`);
    } catch {
      setEndingSession(false);
    }
  }, [sessionId, router]);

  const handleSkip = () => {
    if (window.confirm("End the interview now and get your feedback?")) {
      handleGetFeedback();
    }
  };

  // Sync blobState with voice button state from VoiceButton
  const handleVoiceStateChange = useCallback((vs: "idle" | "listening" | "processing" | "error") => {
    if (vs === "listening") setBlobState("listening");
    else if (vs === "processing") setBlobState("processing");
    // idle/error handled by speakAndWait flow
  }, []);

  return (
    <div className="flex flex-col h-screen bg-neutral-950 overflow-hidden">
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
          <span className="text-slate-400 text-sm tabular-nums">{formatTime(elapsed)}</span>
        </div>
        <button
          onClick={handleSkip}
          disabled={endingSession}
          className="text-slate-400 hover:text-slate-200 disabled:opacity-40 transition-colors text-sm"
        >
          {endingSession ? "Loading…" : "Skip →"}
        </button>
      </header>

      {/* Main area — blob + caption */}
      <div className="flex-1 flex flex-col items-center justify-center gap-8 px-6">
        <InterviewBlob state={blobState} />

        {/* Caption */}
        <div
          className="max-w-sm text-center transition-all duration-400"
          style={{
            opacity: captionVisible ? 1 : 0,
            transform: captionVisible ? "translateY(0)" : "translateY(8px)",
            transition: "opacity 400ms ease, transform 400ms ease",
          }}
        >
          <p className="text-slate-300 text-sm leading-relaxed">{caption}</p>
        </div>

        {/* State label */}
        <p className="text-[11px] uppercase tracking-widest text-slate-500">
          {blobState === "speaking" && "Speaking…"}
          {blobState === "listening" && "Listening…"}
          {blobState === "processing" && "Thinking…"}
          {blobState === "idle" && !voiceDisabled && "Hold to respond"}
          {blobState === "idle" && voiceDisabled && " "}
        </p>
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
          onVoiceStateChange={handleVoiceStateChange}
        />
      )}

      <div className="h-40" />
    </div>
  );
}
