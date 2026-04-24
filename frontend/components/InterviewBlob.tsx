"use client";

export type BlobState = "idle" | "speaking" | "listening" | "processing";

interface InterviewBlobProps {
  state: BlobState;
}

export default function InterviewBlob({ state }: InterviewBlobProps) {
  return (
    <div className="relative flex items-center justify-center" style={{ width: 280, height: 280 }}>
      {/* Idle & speaking: morphing blob layers */}
      {(state === "idle" || state === "speaking") && (
        <>
          {/* Back layer — slowest morph */}
          <div
            className="absolute rounded-full"
            style={{
              width: 220,
              height: 220,
              background:
                state === "speaking"
                  ? "radial-gradient(ellipse at 40% 40%, #818cf8 0%, #6366f1 40%, #4338ca 100%)"
                  : "radial-gradient(ellipse at 40% 40%, #6366f1 0%, #4338ca 50%, #312e81 100%)",
              filter: "blur(24px)",
              animation:
                state === "speaking"
                  ? "morph 2.5s ease-in-out infinite, breathe 1.2s ease-in-out infinite"
                  : "morph 6s ease-in-out infinite, breathe 3s ease-in-out infinite",
              opacity: 0.7,
            }}
          />
          {/* Mid layer */}
          <div
            className="absolute rounded-full"
            style={{
              width: 170,
              height: 170,
              background:
                state === "speaking"
                  ? "radial-gradient(ellipse at 60% 30%, #a5b4fc 0%, #818cf8 50%, #6366f1 100%)"
                  : "radial-gradient(ellipse at 60% 30%, #818cf8 0%, #6366f1 60%, #4f46e5 100%)",
              filter: "blur(12px)",
              animation:
                state === "speaking"
                  ? "morph-alt 1.8s ease-in-out infinite, breathe 0.9s ease-in-out 150ms infinite"
                  : "morph-alt 4s ease-in-out infinite, breathe 3s ease-in-out 500ms infinite",
              opacity: 0.85,
            }}
          />
          {/* Front layer — brightest, fastest */}
          <div
            className="absolute rounded-full"
            style={{
              width: 110,
              height: 110,
              background:
                state === "speaking"
                  ? "radial-gradient(ellipse at 50% 40%, #e0e7ff 0%, #c7d2fe 40%, #a5b4fc 100%)"
                  : "radial-gradient(ellipse at 50% 40%, #c7d2fe 0%, #a5b4fc 50%, #818cf8 100%)",
              filter: "blur(6px)",
              animation:
                state === "speaking"
                  ? "morph 1.2s ease-in-out 100ms infinite, breathe 0.7s ease-in-out 300ms infinite"
                  : "morph 3s ease-in-out 200ms infinite, breathe 3s ease-in-out 1s infinite",
              opacity: 0.95,
            }}
          />
        </>
      )}

      {/* Listening: expanding rings */}
      {state === "listening" && (
        <>
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="absolute rounded-full border-2 border-indigo-400"
              style={{
                width: 140,
                height: 140,
                animation: `blob-ring 0.9s ease-out ${i * 280}ms infinite`,
              }}
            />
          ))}
          {/* Center dot */}
          <div
            className="absolute rounded-full"
            style={{
              width: 80,
              height: 80,
              background: "radial-gradient(ellipse, #818cf8 0%, #6366f1 100%)",
              filter: "blur(4px)",
              animation: "breathe 0.9s ease-in-out infinite",
            }}
          />
        </>
      )}

      {/* Processing: spinning gradient */}
      {state === "processing" && (
        <>
          <div
            className="absolute rounded-full"
            style={{
              width: 180,
              height: 180,
              background: "conic-gradient(from 0deg, #6366f1, #a5b4fc, #4338ca, #6366f1)",
              filter: "blur(18px)",
              animation: "blob-spin 1.5s linear infinite, breathe 1.5s ease-in-out infinite",
              opacity: 0.75,
            }}
          />
          <div
            className="absolute rounded-full"
            style={{
              width: 100,
              height: 100,
              background: "radial-gradient(ellipse, #c7d2fe 0%, #818cf8 100%)",
              filter: "blur(8px)",
              animation: "breathe 1.5s ease-in-out 200ms infinite",
            }}
          />
        </>
      )}
    </div>
  );
}
