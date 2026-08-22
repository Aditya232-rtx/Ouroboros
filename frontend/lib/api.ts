import type { AgentsState, Finding, Transcript, ResearchFinding } from "./types";

const BASE = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL ?? "http://localhost:7891";

export async function startScan(url: string, scanMode = "quick") {
  const res = await fetch(`${BASE}/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, scan_mode: scanMode }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ run_id: string; run_name: string }>;
}

export function openScanEventStream(runId: string) {
  return new EventSource(`${BASE}/scan/${runId}/events`);
}

/** Registers an already-running (or already-finished) strix run dir that wasn't
 * launched through startScan — e.g. started manually on the CLI — so the
 * dashboard can display it. Omit runName to adopt the most recent run dir. */
export async function adoptScan(runName?: string) {
  const qs = runName ? `?run_name=${encodeURIComponent(runName)}` : "";
  const res = await fetch(`${BASE}/scan/adopt${qs}`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ run_id: string; run_name: string; url: string; status: string }>;
}

export async function connectGateway(phoneNumber: string) {
  const res = await fetch(`${BASE}/gateway/connect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone_number: phoneNumber }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getGatewayQr() {
  const res = await fetch(`${BASE}/gateway/qr`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ state: string; qr_data: string | null; phone: string | null }>;
}

export async function getGatewayStatus() {
  const res = await fetch(`${BASE}/gateway/status`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ state: string; phone: string | null }>;
}

export async function getReport(runId: string) {
  const res = await fetch(`${BASE}/report/${runId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function seedDemo() {
  const res = await fetch(`${BASE}/demo/seed`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ run_id: string; findings_count: number }>;
}

export async function triggerFixAll(runId: string, targetUrl: string, phoneNumber: string) {
  const res = await fetch(`${BASE}/fix-all`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_id: runId, target_url: targetUrl, phone_number: phoneNumber }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getScanAgents(runId: string): Promise<AgentsState> {
  const res = await fetch(`${BASE}/scan/${runId}/agents`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getScanTranscript(runId: string): Promise<Transcript> {
  const res = await fetch(`${BASE}/scan/${runId}/transcript`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function triggerResearch(runId: string) {
  const res = await fetch(`${BASE}/scan/${runId}/research`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ status: string; run_id: string }>;
}

export async function getResearch(runId: string) {
  const res = await fetch(`${BASE}/scan/${runId}/research`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ ready: boolean; findings: ResearchFinding[] }>;
}

export async function getScanFindings(runId: string) {
  const res = await fetch(`${BASE}/scan/${runId}/findings`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ findings: Finding[]; status: string }>;
}
