"use client";

import { useRef, useState, DragEvent } from "react";
import { useRouter } from "next/navigation";
import { startSession } from "@/lib/api";

export default function StartPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [role, setRole] = useState("");
  const [company, setCompany] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped?.type === "application/pdf") setFile(dropped);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f?.type === "application/pdf") setFile(f);
  };

  const canSubmit = !!file && role.trim().length > 0 && !loading;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("resume", file!);
      formData.append("role", role.trim());
      if (company.trim()) formData.append("company", company.trim());

      const data = await startSession(formData);

      localStorage.setItem(
        `session-${data.session_id}`,
        JSON.stringify({
          intro_message: data.intro_message,
          interviewer_persona: data.interviewer_persona,
        })
      );

      router.push(`/interview/${data.session_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start session");
      setLoading(false);
    }
  };

  return (
    <main className="flex flex-1 items-center justify-center px-4 py-16">
      <div
        className="w-full max-w-lg"
        style={{ animation: "fade-in-up 300ms cubic-bezier(0.4,0,0.2,1) forwards" }}
      >
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight">
            Mock Interview
          </h1>
          <p className="text-slate-400 mt-2 text-sm">
            Upload your resume and start a real-time AI behavioral interview
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-neutral-800 border border-neutral-700 rounded-3xl p-8 flex flex-col gap-6"
        >
          {/* Drop zone */}
          <div
            role="button"
            tabIndex={0}
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            className={`relative rounded-2xl border-2 border-dashed px-6 py-10 flex flex-col items-center gap-3 cursor-pointer transition-colors ${
              dragging
                ? "border-indigo-400 bg-neutral-700"
                : file
                ? "border-emerald-500/50 bg-emerald-500/5"
                : "border-indigo-500/50 bg-neutral-800 hover:bg-neutral-700"
            }`}
          >
            <span
              className="text-3xl"
              style={{ animation: file ? "none" : "bounce-up 2s ease-in-out infinite" }}
            >
              {file ? "📄" : "⬆️"}
            </span>
            <div className="text-center">
              {file ? (
                <p className="text-sm text-emerald-400 font-medium">{file.name}</p>
              ) : (
                <>
                  <p className="text-sm text-slate-200 font-medium">
                    Drop your resume here
                  </p>
                  <p className="text-xs text-slate-400 mt-1">PDF only · click to browse</p>
                </>
              )}
            </div>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={handleFileInput}
          />

          {/* Fields */}
          <div className="flex flex-col gap-4">
            <div>
              <label className="text-[11px] uppercase tracking-widest text-slate-400 block mb-1.5">
                Target Role <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder="e.g. Product Manager"
                className="w-full bg-neutral-900 border border-neutral-700 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>
            <div>
              <label className="text-[11px] uppercase tracking-widest text-slate-400 block mb-1.5">
                Company (optional)
              </label>
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="e.g. Google"
                className="w-full bg-neutral-900 border border-neutral-700 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>
          </div>

          {error && (
            <p className="text-red-400 text-sm text-center">{error}</p>
          )}

          <button
            type="submit"
            disabled={!canSubmit}
            className="w-full bg-indigo-500 hover:bg-indigo-600 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold rounded-xl py-4 transition-all duration-150 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-indigo-500/20 active:translate-y-0"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span
                  className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full"
                  style={{ animation: "spin 1s linear infinite" }}
                />
                Starting interview…
              </span>
            ) : (
              "Begin Interview"
            )}
          </button>
        </form>
      </div>
    </main>
  );
}
