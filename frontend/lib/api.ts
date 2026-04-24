const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface SessionStartResponse {
  session_id: string;
  intro_message: string;
  interviewer_persona: string;
}

export interface RespondResponse {
  ai_message: string;
  stage: string;
  interview_complete: boolean;
}

export interface SessionEndResponse {
  session_id: string;
  overall_score: number;
  summary: string;
  top_strengths: string[];
  top_improvements: string[];
  question_feedback: QuestionFeedback[];
}

export interface QuestionFeedback {
  question: string;
  user_answer: string;
  star_scores: StarScores;
  strengths: string[];
  improvements: string[];
}

export interface StarScores {
  situation: number;
  task: number;
  action: number;
  result: number;
}

export async function startSession(
  formData: FormData
): Promise<SessionStartResponse> {
  const res = await fetch(`${BASE}/session/start`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Session start failed (${res.status})`);
  }
  return res.json();
}

export async function respond(
  sessionId: string,
  userInput: string,
  stage: string
): Promise<RespondResponse> {
  const res = await fetch(`${BASE}/session/${sessionId}/respond`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_input: userInput, stage }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Respond failed (${res.status})`);
  }
  return res.json();
}

export async function endSession(
  sessionId: string
): Promise<SessionEndResponse> {
  const res = await fetch(`${BASE}/session/${sessionId}/end`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `End session failed (${res.status})`);
  }
  return res.json();
}

export async function textToSpeech(text: string): Promise<Blob> {
  const res = await fetch(`${BASE}/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    throw new Error(`TTS failed (${res.status})`);
  }
  return res.blob();
}

export type StreamEvent =
  | { type: "token"; text: string }
  | { type: "done"; stage: string; interview_complete: boolean };

export async function* respondStream(
  sessionId: string,
  userInput: string,
  stage: string
): AsyncGenerator<StreamEvent> {
  const res = await fetch(`${BASE}/session/${sessionId}/respond/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_input: userInput, stage }),
  });
  if (!res.ok || !res.body) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Respond failed (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          yield JSON.parse(line.slice(6)) as StreamEvent;
        } catch {
          // malformed line — skip
        }
      }
    }
  }
}

export async function transcribe(audioBlob: Blob): Promise<{ text: string }> {
  const formData = new FormData();
  formData.append("audio", audioBlob, "recording.webm");
  const res = await fetch(`${BASE}/transcribe`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Transcription failed (${res.status})`);
  }
  return res.json();
}
