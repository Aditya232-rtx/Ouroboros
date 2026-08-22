"use client";

import { useState } from "react";

interface ScanInputProps {
  onScan: (url: string) => void;
  disabled?: boolean;
}

export function ScanInput({ onScan, disabled }: ScanInputProps) {
  const [url, setUrl] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) return;
    const normalized = trimmed.startsWith("http") ? trimmed : `https://${trimmed}`;
    onScan(normalized);
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
      <div
        className="flex items-center gap-0 rounded-lg overflow-hidden"
        style={{ border: "1px solid var(--border)", background: "var(--surface)" }}
      >
        <span className="pl-4 pr-2 text-sm" style={{ color: "var(--text-dim)" }}>
          target://
        </span>
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://target.example.com"
          disabled={disabled}
          className="flex-1 bg-transparent py-3 pr-3 text-sm outline-none placeholder:opacity-30"
          style={{ color: "var(--text)" }}
          autoFocus
        />
        <button
          type="submit"
          disabled={disabled || !url.trim()}
          className="px-6 py-3 text-sm font-bold uppercase tracking-widest transition-all disabled:opacity-30"
          style={{
            background: disabled ? "transparent" : "var(--green)",
            color: disabled ? "var(--text-dim)" : "#000",
            cursor: disabled ? "not-allowed" : "pointer",
          }}
        >
          {disabled ? "SCANNING..." : "SCAN"}
        </button>
      </div>
    </form>
  );
}
