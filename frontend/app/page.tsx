"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import type { User } from "@supabase/supabase-js";
import Auth from "@/components/ouro-ui/Auth";
import Dashboard from "@/components/ouro-ui/Dashboard";
import "@/components/ouro-ui/App.css";
import { GatewayModal } from "@/components/GatewayModal";
import { supabase } from "@/lib/supabaseClient";
import { startScan, openScanEventStream, triggerFixAll, adoptScan, getScanFindings } from "@/lib/api";
import type { Finding, ScanStatus, GatewayState } from "@/lib/types";

const heroBackground = "/assets/BackGroundImg.png";
const logo = "/assets/OuroLogo.png";

function PixelWord({ children }: { children: string }) {
  return (
    <span className="pixel-word">
      <span className="pixel-cap">{children.charAt(0)}</span>
      <span className="pixel-rest">{children.slice(1)}</span>
    </span>
  );
}

type View = "home" | "login" | "signup" | "dashboard";

export default function App() {
  const [loaded, setLoaded] = useState(false);
  const [linkText, setLinkText] = useState("");
  const [currentView, setCurrentView] = useState<View>("home");
  const [user, setUser] = useState<User | null>(null);
  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false);

  // Scan state (backend integration) — owned here, handed down to Dashboard.
  const [scanStatus, setScanStatus] = useState<ScanStatus>("idle");
  const [scannedUrl, setScannedUrl] = useState("");
  const [runId, setRunId] = useState<string | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [findingsHistory, setFindingsHistory] = useState<{ t: number; count: number }[]>([]);
  const scanStartRef = useRef(0);
  const [showGateway, setShowGateway] = useState(false);
  const [gatewayState, setGatewayState] = useState<GatewayState>("disconnected");

  const navigateTo = (view: string) => {
    setCurrentView(view as View);
    setProfileDropdownOpen(false);
    window.location.hash = view === "home" ? "" : `#${view}`;
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // Track findings-count-over-time for the Vulnerability Timeline chart.
  useEffect(() => {
    if (scanStatus === "idle" || !scanStartRef.current) return;
    setFindingsHistory((prev) => [...prev, { t: (Date.now() - scanStartRef.current) / 1000, count: findings.length }]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [findings.length]);

  useEffect(() => {
    setLoaded(true);

    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user || null);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user || null);
    });

    const handleHash = () => {
      const hash = window.location.hash;
      if (hash === "#login") setCurrentView("login");
      else if (hash === "#signup") setCurrentView("signup");
      else if (hash === "#dashboard") setCurrentView("dashboard");
      else setCurrentView("home");
    };

    handleHash();
    window.addEventListener("hashchange", handleHash);

    const handleClickOutside = (e: MouseEvent) => {
      if (!(e.target as HTMLElement).closest(".navbar__profile-wrap")) {
        setProfileDropdownOpen(false);
      }
    };
    window.addEventListener("click", handleClickOutside);

    return () => {
      subscription?.unsubscribe();
      window.removeEventListener("hashchange", handleHash);
      window.removeEventListener("click", handleClickOutside);
    };
  }, []);

  // ?run=<run_name> (or bare ?adopt) picks up an already-running strix
  // process that wasn't launched through the Scan form — e.g. started
  // manually on the CLI — and shows it live on the dashboard.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (!params.has("run") && !params.has("adopt")) return;
    const runName = params.get("run") ?? undefined;

    // React Strict Mode double-invokes effects in dev, which would fire two
    // /scan/adopt calls and race two different run_ids into state. Bail out
    // of the stale invocation's callback instead of applying it.
    let cancelled = false;

    adoptScan(runName)
      .then(async ({ run_id, url, status }) => {
        if (cancelled) return;
        setRunId(run_id);
        setScannedUrl(url);
        setScanStatus(status === "completed" ? "completed" : "running");
        scanStartRef.current = Date.now();
        setFindingsHistory([{ t: 0, count: 0 }]);
        navigateTo("dashboard");

        // The periodic poll below only runs for running/starting scans, so
        // an adopted *completed* run needs its findings fetched once here —
        // otherwise the dashboard shows zero findings for an already-done scan.
        try {
          const { findings: existing } = await getScanFindings(run_id);
          if (!cancelled && existing.length) setFindings(existing);
        } catch {
          // no findings file yet — leave empty
        }
      })
      .catch(() => {
        // no matching run — stay on the current view
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fallback findings poll — the SSE stream above is the fast path, but a
  // long-lived EventSource can fail to establish on the very first attempt
  // (unlike a mid-stream drop, the browser won't retry that case) and then
  // silently deliver nothing for the rest of the scan. Poll the same data
  // the stream would have pushed so findings always catch up regardless of
  // whether SSE is behaving.
  useEffect(() => {
    if (!runId || (scanStatus !== "running" && scanStatus !== "starting")) return;
    const interval = setInterval(async () => {
      try {
        const { findings: latest } = await getScanFindings(runId);
        if (latest.length === 0) return;
        setFindings((prev) => {
          const known = new Set(prev.map((f) => f.id));
          const additions = latest.filter((f) => !known.has(f.id));
          return additions.length ? [...prev, ...additions] : prev;
        });
      } catch {
        // keep polling
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [runId, scanStatus]);

  const handleSignOut = async () => {
    setProfileDropdownOpen(false);
    await supabase.auth.signOut();
    setUser(null);
    navigateTo("home");
  };

  const handleScan = useCallback(async (url: string) => {
    setScannedUrl(url);
    setScanStatus("starting");
    setFindings([]);
    scanStartRef.current = Date.now();
    setFindingsHistory([{ t: 0, count: 0 }]);

    try {
      const { run_id } = await startScan(url);
      setRunId(run_id);
      setScanStatus("running");
      navigateTo("dashboard");

      const es = openScanEventStream(run_id);

      es.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === "finding") {
            setFindings((prev) => {
              const exists = prev.some((f) => f.id === msg.finding.id);
              return exists ? prev : [...prev, msg.finding];
            });
          } else if (msg.type === "status") {
            if (msg.status === "running" || msg.status === "starting") {
              setScanStatus(msg.status);
            }
          } else if (msg.type === "done") {
            setScanStatus(msg.status === "completed" ? "completed" : "failed");
            if (msg.findings?.length) setFindings(msg.findings);
            es.close();
          }
        } catch {
          // ignore parse errors
        }
      };

      // The browser's EventSource already retries transient connection
      // drops on its own (readyState cycles back to CONNECTING) — treating
      // every error event as fatal here was closing healthy scans and
      // marking them "failed" over a single network blip, with no way to
      // recover findings that arrived after. Leave reconnection to the
      // browser; the findings fallback poll below is the resilience layer
      // that keeps the dashboard correct even if this stream misbehaves.
      es.onerror = () => {};
    } catch {
      setScanStatus("failed");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleLinkSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!linkText.trim()) return;
    handleScan(linkText.trim());
  };

  if (currentView === "login" || currentView === "signup") {
    return (
      <Auth
        initialMode={currentView}
        onBackToHome={() => navigateTo("home")}
        logoSrc={logo}
        bgSrc={heroBackground}
        onAuthSuccess={(authUser) => {
          setUser(authUser ?? null);
          navigateTo("dashboard");
        }}
      />
    );
  }

  if (currentView === "dashboard") {
    return (
      <>
        <Dashboard
          user={user}
          onNavigate={navigateTo}
          onSignOut={handleSignOut}
          logoSrc={logo}
          bgSrc={heroBackground}
          runId={runId}
          targetUrl={scannedUrl}
          scanStatus={scanStatus}
          findings={findings}
          findingsHistory={findingsHistory}
          gatewayState={gatewayState}
          onDeployAgent={() => setShowGateway(true)}
        />
        {showGateway && (
          <GatewayModal
            onConnected={async (phone) => {
              setGatewayState("connected");
              setShowGateway(false);
              if (runId && scannedUrl) {
                try {
                  await triggerFixAll(runId, scannedUrl, phone);
                } catch {
                  // non-fatal — Ouro will start when gateway is ready
                }
              }
            }}
            onClose={() => setShowGateway(false)}
          />
        )}
      </>
    );
  }

  return (
    <div className={`app ${loaded ? "app--loaded" : ""}`}>
      {/* ═══════════════ HERO SECTION ═══════════════ */}
      <section className="hero">
        <div className="hero__bg">
          <img src={heroBackground} alt="" className="hero__bg-img" />
          <div className="hero__bg-overlay" />
        </div>

        <div className="hero__lines">
          <span className="hero__line hero__line--1" />
          <span className="hero__line hero__line--2" />
          <span className="hero__line hero__line--3" />
        </div>

        <div className="hero__frame">
          <nav className="navbar">
            <a
              href="#home"
              onClick={(e) => {
                e.preventDefault();
                navigateTo("home");
              }}
              className="navbar__brand"
              id="nav-logo"
            >
              <img src={logo} alt="Ouroborous" className="navbar__logo" />
            </a>

            <div className="navbar__right">
              {user ? (
                <div className="navbar__user-group">
                  <button
                    type="button"
                    onClick={() => navigateTo("dashboard")}
                    className="navbar__link navbar__link--dashboard"
                    id="nav-dashboard"
                  >
                    Dashboard
                  </button>

                  <div className="navbar__profile-wrap">
                    <button
                      type="button"
                      onClick={() => setProfileDropdownOpen(!profileDropdownOpen)}
                      className="navbar__profile-btn"
                      id="nav-profile-btn"
                      aria-label="User Profile"
                    >
                      <span className="navbar__profile-avatar">
                        {user.user_metadata?.full_name
                          ? user.user_metadata.full_name.charAt(0).toUpperCase()
                          : user.email?.charAt(0).toUpperCase() || "O"}
                      </span>
                    </button>

                    {profileDropdownOpen && (
                      <div className="navbar__dropdown">
                        <div className="navbar__dropdown-header">
                          <span className="navbar__dropdown-name">{user.user_metadata?.full_name || "Cyber Operator"}</span>
                          <span className="navbar__dropdown-email">{user.email}</span>
                        </div>
                        <div className="navbar__dropdown-divider" />
                        <button type="button" className="navbar__dropdown-item" onClick={() => navigateTo("dashboard")}>
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <rect x="3" y="3" width="7" height="7" />
                            <rect x="14" y="3" width="7" height="7" />
                            <rect x="14" y="14" width="7" height="7" />
                            <rect x="3" y="14" width="7" height="7" />
                          </svg>
                          <span>System Dashboard</span>
                        </button>
                        <button
                          type="button"
                          className="navbar__dropdown-item navbar__dropdown-item--danger"
                          onClick={handleSignOut}
                        >
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                            <polyline points="16 17 21 12 16 7" />
                            <line x1="21" y1="12" x2="9" y2="12" />
                          </svg>
                          <span>Sign Out</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <>
                  <button type="button" onClick={() => navigateTo("login")} className="navbar__link" id="nav-login">
                    Login
                  </button>
                  <button type="button" onClick={() => navigateTo("signup")} className="navbar__btn" id="nav-signup">
                    Sign up
                  </button>
                </>
              )}
            </div>
          </nav>

          <div className="hero__content">
            <h1 className="hero-title" id="hero-heading">
              <span className="line">
                <PixelWord>Enter</PixelWord> <PixelWord>Your</PixelWord>
                <PixelWord>Link</PixelWord> <PixelWord>Here</PixelWord>
              </span>
            </h1>

            <form className="hero__input-form" onSubmit={handleLinkSubmit}>
              <div className="hero__input-box">
                <textarea
                  className="hero__textarea"
                  placeholder="Paste your target URL here..."
                  rows={2}
                  value={linkText}
                  onChange={(e) => setLinkText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleLinkSubmit();
                    }
                  }}
                  id="hero-link-input"
                  disabled={scanStatus === "starting" || scanStatus === "running"}
                />
                {linkText.trim().length > 0 && (
                  <button type="submit" className="hero__arrow-btn" aria-label="Submit link" id="submit-link-btn">
                    <svg width="20" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="5" y1="12" x2="19" y2="12" />
                      <polyline points="12 5 19 12 12 19" />
                    </svg>
                  </button>
                )}
              </div>
            </form>
          </div>

          <div className="hero__scroll">
            <span className="hero__scroll-text">SCROLL</span>
            <span className="hero__scroll-arrows">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M4 6L8 10L12 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ marginTop: "-6px" }}>
                <path d="M4 6L8 10L12 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
          </div>
        </div>
      </section>

      {/* ═══════════════ ABOUT SECTION ═══════════════ */}
      <section className="section section--about" id="about">
        <div className="section__inner">
          <div className="section__label">What is Ouroborous?</div>
          <h2 className="section__title">
            Security that <em>evolves</em> by attacking itself.
          </h2>
          <div className="section__grid">
            <div className="card" id="card-purple-teaming">
              <div className="card__icon">∞</div>
              <h3 className="card__title">Autonomous Purple Teaming</h3>
              <p className="card__desc">
                Continuous, orchestrated combat between offensive and defensive AI agents, uncovering vulnerabilities before human adversaries do.
              </p>
            </div>
            <div className="card" id="card-agent-swapping">
              <div className="card__icon">◈</div>
              <h3 className="card__title">Dynamic Agent Swapping</h3>
              <p className="card__desc">
                An architecture that adapts in real-time. Specialized agents swap seamlessly to counter emerging threat contexts and optimize defense strategies.
              </p>
            </div>
            <div className="card" id="card-local-infrastructure">
              <div className="card__icon">⬡</div>
              <h3 className="card__title">Local &amp; Secure Infrastructure</h3>
              <p className="card__desc">
                Built for absolute privacy. Deploy fine-tuned QLoRA adapters and local LLMs within sandboxed environments—keeping your security data strictly on-premise.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════ VISION SECTION ═══════════════ */}
      <section className="section section--vision" id="vision">
        <div className="section__inner">
          <div className="section__label">Our Vision</div>
          <h2 className="section__title">
            The serpent eats its tail.
            <br />
            The cycle never ends.
          </h2>
          <p className="section__text">
            In cybersecurity, this is the ultimate defense. Ouroboros represents the continuous loop of attack, detection, and remediation. We are
            building a multi-agent platform that doesn&apos;t just respond to threats, but autonomously learns from its own offensive
            simulations—creating an ascending spiral of system resilience that knows no ceiling.
          </p>
          <div className="vision__stats">
            <div className="stat" id="stat-exfiltration">
              <span className="stat__number">Zero</span>
              <span className="stat__label">Data Exfiltration (Local Execution)</span>
            </div>
            <div className="stat" id="stat-cycles">
              <span className="stat__number">∞</span>
              <span className="stat__label">Attack-Defense Cycles</span>
            </div>
            <div className="stat" id="stat-reallocation">
              <span className="stat__number">Sub-Second</span>
              <span className="stat__label">Agent Reallocation</span>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════ FOOTER ═══════════════ */}
      <footer className="footer" id="footer">
        <div className="footer__inner">
          <div className="footer__brand">
            <img src={logo} alt="Ouroborous" className="footer__logo" />
            <span className="footer__name">Ouroborous</span>
          </div>
          <p className="footer__copy">© {new Date().getFullYear()} Ouroborous. The cycle continues.</p>
        </div>
      </footer>
    </div>
  );
}
