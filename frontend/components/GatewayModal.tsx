"use client";

import { useEffect, useState, useRef } from "react";
import { QRCodeSVG } from "qrcode.react";
import { connectGateway, getGatewayQr } from "@/lib/api";
import "./GatewayModal.css";

interface GatewayModalProps {
  onConnected: (phone: string) => void;
  onClose: () => void;
}

type Step = "phone" | "qr" | "connected";

export function GatewayModal({ onConnected, onClose }: GatewayModalProps) {
  const [step, setStep] = useState<Step>("phone");
  const [phone, setPhone] = useState("");
  const [qrText, setQrText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [slackConnected, setSlackConnected] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  async function handleConnect() {
    if (!phone.trim()) return;
    setError(null);
    try {
      const result = await connectGateway(phone.trim());
      if (result.status === "already_paired") {
        setStep("connected");
        setTimeout(() => onConnected(phone.trim()), 1200);
        return;
      }
      setStep("qr");
      startQrPolling();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Connection failed");
    }
  }

  function startQrPolling() {
    pollRef.current = setInterval(async () => {
      try {
        const data = await getGatewayQr();
        if (data.qr_data) setQrText(data.qr_data);
        if (data.state === "connected") {
          if (pollRef.current) clearInterval(pollRef.current);
          setStep("connected");
          setTimeout(() => onConnected(phone), 1500);
        }
      } catch {
        // transient — keep polling
      }
    }, 1500);
  }

  return (
    <div className="gwm__overlay">
      <div className="gwm__card glass animate-fade-in">
        <button onClick={onClose} className="gwm__close" aria-label="Close">
          ✕
        </button>

        {step === "phone" && (
          <div>
            <h2 className="gwm__title">Connect WhatsApp</h2>
            <p className="gwm__subtitle">
              This links your WhatsApp as a companion device — like WhatsApp Web.
              Ouro will message you in your own <strong>&quot;Message yourself&quot;</strong>{" "}
              thread. You can unlink it anytime from{" "}
              <strong>Settings → Linked Devices</strong>.
            </p>

            <label className="gwm__label">Your WhatsApp number (with country code)</label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+91 98765 43210"
              className="gwm__input"
              onKeyDown={(e) => e.key === "Enter" && handleConnect()}
              autoFocus
            />

            {error && <p className="gwm__error">{error}</p>}

            <button
              onClick={handleConnect}
              disabled={!phone.trim()}
              className="gwm__btn-primary"
            >
              Pair WhatsApp
            </button>

            <div className="gwm__divider">
              <p className="gwm__divider-label">Optional — connect Slack for escalation alerts</p>
              <button
                onClick={() => setSlackConnected(!slackConnected)}
                className={`gwm__btn-secondary ${slackConnected ? "gwm__btn-secondary--active" : ""}`}
              >
                {slackConnected ? "✓ Slack Connected" : "Connect Slack"}
              </button>
            </div>
          </div>
        )}

        {step === "qr" && (
          <div className="text-center">
            <h2 className="gwm__title">Scan QR Code</h2>
            <p className="gwm__subtitle">
              Open WhatsApp → Settings → Linked Devices → Link a Device
            </p>

            {qrText ? (
              <div className="gwm__qr-box">
                <div className="gwm__qr-frame">
                  <QRCodeSVG value={qrText} size={220} level="M" includeMargin={false} />
                </div>
              </div>
            ) : (
              <div className="gwm__qr-loading">
                <div className="gwm__spinner" />
                <p className="gwm__hint">Waiting for QR code from gateway...</p>
              </div>
            )}

            <p className="gwm__hint">
              Waiting for pairing confirmation
              <span className="animate-blink">_</span>
            </p>
          </div>
        )}

        {step === "connected" && (
          <div className="text-center" style={{ padding: "24px 0" }}>
            <div className="gwm__success-icon">✓</div>
            <h2 className="gwm__title" style={{ marginBottom: 6 }}>
              WhatsApp Connected
            </h2>
            <p className="gwm__hint">Ouro will message you in your self-chat thread</p>
          </div>
        )}
      </div>
    </div>
  );
}
