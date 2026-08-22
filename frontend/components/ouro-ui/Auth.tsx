"use client";

import { useState, useEffect, type FormEvent, type ChangeEvent } from "react";
import { supabase, isSupabaseConfigured } from "@/lib/supabaseClient";
import type { User } from "@supabase/supabase-js";
import "./Auth.css";

type AuthMode = "login" | "signup" | "forgot";

interface AuthProps {
  initialMode?: AuthMode;
  onBackToHome: () => void;
  logoSrc: string;
  bgSrc: string;
  onAuthSuccess: (user: User | null | undefined) => void;
}

interface AuthFormData {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
  agreeTerms: boolean;
  rememberMe: boolean;
}

function PixelWord({ children }: { children: string }) {
  return (
    <span className="pixel-word">
      <span className="pixel-cap">{children.charAt(0)}</span>
      <span className="pixel-rest">{children.slice(1)}</span>
    </span>
  );
}

export default function Auth({ initialMode = "login", onBackToHome, logoSrc, bgSrc, onAuthSuccess }: AuthProps) {
  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [formData, setFormData] = useState<AuthFormData>({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
    agreeTerms: false,
    rememberMe: false,
  });
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const isConfigured = isSupabaseConfigured();

  useEffect(() => {
    setMode(initialMode);
    setErrorMessage("");
    setSuccessMessage("");
  }, [initialMode]);

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErrorMessage("");
    setSuccessMessage("");

    if (!isConfigured) {
      setErrorMessage(
        "Supabase is not configured yet. Please add your NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY to your .env.local file."
      );
      return;
    }

    setLoading(true);

    try {
      if (mode === "signup") {
        if (formData.password !== formData.confirmPassword) {
          setErrorMessage("Passwords do not match.");
          setLoading(false);
          return;
        }

        if (formData.password.length < 6) {
          setErrorMessage("Password must be at least 6 characters.");
          setLoading(false);
          return;
        }

        const { data, error } = await supabase.auth.signUp({
          email: formData.email,
          password: formData.password,
          options: {
            data: {
              full_name: formData.name,
            },
          },
        });

        if (error) throw error;

        if (data?.user && !data?.session) {
          setSuccessMessage("Account created! Please check your email to verify your address before signing in.");
        } else {
          setSuccessMessage("Account created and logged in successfully!");
          onAuthSuccess(data?.user);
        }
      } else if (mode === "login") {
        const { data, error } = await supabase.auth.signInWithPassword({
          email: formData.email,
          password: formData.password,
        });

        if (error) throw error;

        setSuccessMessage("Session initialized! Welcome back.");
        onAuthSuccess(data?.user);
      } else if (mode === "forgot") {
        const { error } = await supabase.auth.resetPasswordForEmail(formData.email, {
          redirectTo: `${window.location.origin}/#reset-password`,
        });

        if (error) throw error;

        setSuccessMessage("Password reset link sent to your email.");
      }
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Authentication error occurred.");
    } finally {
      setLoading(false);
    }
  };

  const handleOAuth = async (provider: "github" | "google") => {
    setErrorMessage("");
    setSuccessMessage("");

    if (!isConfigured) {
      setErrorMessage(
        "Supabase is not configured yet. Please add your NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY to your .env.local file."
      );
      return;
    }

    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: window.location.origin,
        },
      });
      if (error) throw error;
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : `Failed to sign in with ${provider}.`);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth__bg">
        <img src={bgSrc} alt="" className="auth__bg-img" />
      </div>

      <div className="auth__lines">
        <span className="auth__line auth__line--top" />
        <span className="auth__line auth__line--left" />
        <span className="auth__line auth__line--right" />
      </div>

      <header className="auth__nav">
        <button type="button" onClick={onBackToHome} className="auth__brand-btn" title="Return to Home" id="auth-nav-logo">
          <img src={logoSrc} alt="Ouroborous" className="auth__logo" />
        </button>

        <button type="button" onClick={onBackToHome} className="auth__back-btn" id="auth-back-btn">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="19" y1="12" x2="5" y2="12"></line>
            <polyline points="12 19 5 12 12 5"></polyline>
          </svg>
          <span>Back to Home</span>
        </button>
      </header>

      <main className="auth__main">
        <div className="auth__card">
          {!isConfigured && (
            <div className="auth__env-notice">
              <span className="auth__env-icon">⚡</span>
              <div>
                <strong>Supabase Config Required:</strong> Add your <code>NEXT_PUBLIC_SUPABASE_URL</code> and{" "}
                <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code> to <code>.env.local</code> to connect real authentication.
              </div>
            </div>
          )}

          {mode !== "forgot" && (
            <div className="auth__tabs">
              <button
                type="button"
                className={`auth__tab ${mode === "login" ? "auth__tab--active" : ""}`}
                onClick={() => {
                  setMode("login");
                  setErrorMessage("");
                  setSuccessMessage("");
                }}
                id="tab-login"
              >
                Sign In
              </button>
              <button
                type="button"
                className={`auth__tab ${mode === "signup" ? "auth__tab--active" : ""}`}
                onClick={() => {
                  setMode("signup");
                  setErrorMessage("");
                  setSuccessMessage("");
                }}
                id="tab-signup"
              >
                Create Account
              </button>
            </div>
          )}

          <div className="auth__header">
            <h1 className="auth__title">
              {mode === "login" && (
                <>
                  <PixelWord>Sign</PixelWord> <PixelWord>In</PixelWord>
                </>
              )}
              {mode === "signup" && (
                <>
                  <PixelWord>Create</PixelWord> <PixelWord>Account</PixelWord>
                </>
              )}
              {mode === "forgot" && (
                <>
                  <PixelWord>Reset</PixelWord> <PixelWord>Access</PixelWord>
                </>
              )}
            </h1>
            <p className="auth__subtitle">
              {mode === "login" && "Enter the eternal cycle of autonomous cyber resilience."}
              {mode === "signup" && "Join the next generation of offensive-defensive AI intelligence."}
              {mode === "forgot" && "Provide your security email to receive a recovery token."}
            </p>
          </div>

          {errorMessage && (
            <div className="auth__alert auth__alert--error">
              <span className="auth__alert-icon">!</span>
              <span>{errorMessage}</span>
            </div>
          )}

          {successMessage && (
            <div className="auth__alert auth__alert--success">
              <span className="auth__alert-icon">✓</span>
              <span>{successMessage}</span>
            </div>
          )}

          <form className="auth__form" onSubmit={handleSubmit}>
            {mode === "signup" && (
              <div className="auth__field">
                <label className="auth__label" htmlFor="name">
                  Full Name / Organization
                </label>
                <div className="auth__input-wrap">
                  <input
                    type="text"
                    id="name"
                    name="name"
                    required
                    placeholder="e.g. Satoshi Nakamoto"
                    className="auth__input"
                    value={formData.name}
                    onChange={handleChange}
                  />
                </div>
              </div>
            )}

            <div className="auth__field">
              <label className="auth__label" htmlFor="email">
                Email Address
              </label>
              <div className="auth__input-wrap">
                <input
                  type="email"
                  id="email"
                  name="email"
                  required
                  placeholder="name@organization.com"
                  className="auth__input"
                  value={formData.email}
                  onChange={handleChange}
                />
              </div>
            </div>

            {mode !== "forgot" && (
              <div className="auth__field">
                <div className="auth__label-row">
                  <label className="auth__label" htmlFor="password">
                    Password
                  </label>
                  {mode === "login" && (
                    <button
                      type="button"
                      className="auth__forgot-link"
                      onClick={() => {
                        setMode("forgot");
                        setErrorMessage("");
                        setSuccessMessage("");
                      }}
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
                <div className="auth__input-wrap">
                  <input
                    type="password"
                    id="password"
                    name="password"
                    required
                    placeholder="••••••••••••"
                    className="auth__input"
                    value={formData.password}
                    onChange={handleChange}
                  />
                </div>
              </div>
            )}

            {mode === "signup" && (
              <div className="auth__field">
                <label className="auth__label" htmlFor="confirmPassword">
                  Confirm Password
                </label>
                <div className="auth__input-wrap">
                  <input
                    type="password"
                    id="confirmPassword"
                    name="confirmPassword"
                    required
                    placeholder="••••••••••••"
                    className="auth__input"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                  />
                </div>
              </div>
            )}

            {mode !== "forgot" && (
              <div className="auth__options">
                {mode === "login" ? (
                  <label className="auth__checkbox-label">
                    <input
                      type="checkbox"
                      name="rememberMe"
                      checked={formData.rememberMe}
                      onChange={handleChange}
                      className="auth__checkbox"
                    />
                    <span>Remember this node session</span>
                  </label>
                ) : (
                  <label className="auth__checkbox-label">
                    <input
                      type="checkbox"
                      name="agreeTerms"
                      required
                      checked={formData.agreeTerms}
                      onChange={handleChange}
                      className="auth__checkbox"
                    />
                    <span>I accept the Terms of Service &amp; Privacy Shield</span>
                  </label>
                )}
              </div>
            )}

            <button type="submit" className="auth__submit-btn" disabled={loading} id="auth-submit-btn">
              {loading ? (
                <span className="auth__spinner-text">Processing...</span>
              ) : (
                <>
                  <span>
                    {mode === "login" && "Initialize Session"}
                    {mode === "signup" && "Deploy Account"}
                    {mode === "forgot" && "Send Recovery Token"}
                  </span>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="5" y1="12" x2="19" y2="12"></line>
                    <polyline points="12 5 19 12 12 19"></polyline>
                  </svg>
                </>
              )}
            </button>
          </form>

          {mode !== "forgot" && (
            <>
              <div className="auth__divider">
                <span>or authenticate via</span>
              </div>

              <div className="auth__social-grid">
                <button type="button" className="auth__social-btn" onClick={() => handleOAuth("github")} id="auth-oauth-github">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                  </svg>
                  <span>GitHub</span>
                </button>
                <button type="button" className="auth__social-btn" onClick={() => handleOAuth("google")} id="auth-oauth-google">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12.24 10.285V13.8h6.887C18.2 16.64 15.64 19.2 12.24 19.2c-3.98 0-7.2-3.22-7.2-7.2s3.22-7.2 7.2-7.2c1.78 0 3.39.66 4.64 1.74l2.67-2.67C17.9 2.37 15.22 1.4 12.24 1.4 6.36 1.4 1.6 6.16 1.6 12.04s4.76 10.64 10.64 10.64c6.33 0 10.43-4.45 10.43-10.62 0-.74-.08-1.3-.2-1.775H12.24z" />
                  </svg>
                  <span>Google</span>
                </button>
              </div>
            </>
          )}

          <div className="auth__footer">
            {mode === "login" && (
              <p>
                Don&apos;t have an enterprise key?{" "}
                <button
                  type="button"
                  className="auth__switch-btn"
                  onClick={() => {
                    setMode("signup");
                    setErrorMessage("");
                    setSuccessMessage("");
                  }}
                >
                  Create an account
                </button>
              </p>
            )}
            {mode === "signup" && (
              <p>
                Already have an account?{" "}
                <button
                  type="button"
                  className="auth__switch-btn"
                  onClick={() => {
                    setMode("login");
                    setErrorMessage("");
                    setSuccessMessage("");
                  }}
                >
                  Sign in here
                </button>
              </p>
            )}
            {mode === "forgot" && (
              <p>
                Remembered your password?{" "}
                <button
                  type="button"
                  className="auth__switch-btn"
                  onClick={() => {
                    setMode("login");
                    setErrorMessage("");
                    setSuccessMessage("");
                  }}
                >
                  Back to Sign In
                </button>
              </p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
