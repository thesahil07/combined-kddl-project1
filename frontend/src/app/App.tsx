import { FormEvent, useEffect, useState } from "react";

import { activeTenantBrand } from "./tenantBrand";
import "./signIn.css";
import { CurrentUser, Workspace } from "./workspace";

const apiUrl = "http://127.0.0.1:8000/api/v1";

export function App() {
  const [isOpen, setIsOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailReadOnly, setEmailReadOnly] = useState(true);
  const [passwordReadOnly, setPasswordReadOnly] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);

  async function loadCurrentUser(token: string) {
    const response = await fetch(`${apiUrl}/me`, { headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) throw new Error("Session is no longer valid.");
    setCurrentUser((await response.json()) as CurrentUser);
  }

  useEffect(() => {
    const token = sessionStorage.getItem("kddl_access_token");
    if (token) loadCurrentUser(token).catch(() => sessionStorage.removeItem("kddl_access_token"));
  }, []);

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setMessage("");
    try {
      const response = await fetch(`${apiUrl}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) {
        if (response.status === 503) {
          setMessage("Sign-in service is temporarily unavailable.");
        } else if (response.status === 429) {
          setMessage("Too many login attempts. Please wait a moment and try again.");
        } else {
          setMessage("Invalid email or password. Please try again.");
        }
        setIsLoading(false);
        return;
      }
      const result = (await response.json()) as { access_token: string };
      sessionStorage.setItem("kddl_access_token", result.access_token);
      await loadCurrentUser(result.access_token);
      setIsOpen(false);
      setPassword("");
    } catch {
      setMessage("Unable to reach the sign-in service.");
    } finally {
      setIsLoading(false);
    }
  }

  if (currentUser) {
    return (
      <Workspace
        user={currentUser}
        onSignOut={() => {
          sessionStorage.removeItem("kddl_access_token");
          setCurrentUser(null);
        }}
      />
    );
  }

  return (
    <main className="shell">
      <nav>
        <div className="brand">
          <img src={activeTenantBrand.logoUrl} alt={activeTenantBrand.tenantName} />
          <span>Talent Transformation</span>
        </div>
        <span className="nav-note">POWERED BY PLANET GANGES</span>
      </nav>
      <section className="hero">
        <p className="eyebrow">KDDL TALENT TRANSFORMATION PLATFORM</p>
        <h1>
          Make talent decisions
          <br />
          <em>clearer, together.</em>
        </h1>
        <p className="intro">
          A secure workspace for capability assessment, critical-role visibility, and succession
          planning across KDDL Dials.
        </p>
        <div className="actions">
          <button
            onClick={() => {
              setMessage("");
              setEmail("");
              setPassword("");
              setEmailReadOnly(true);
              setPasswordReadOnly(true);
              setIsOpen(true);
            }}
          >
            Sign in to platform
          </button>
          <a href="#foundation">Explore platform foundation</a>
        </div>
        <figure className="hero-visual">
          <img
            src="/manufacturing-talent-hero.png"
            alt="KDDL manufacturing professionals reviewing precision work"
          />
          <figcaption>Precision, people, and progress.</figcaption>
        </figure>
      </section>
      <section id="foundation" className="foundation">
        <div className="foundation-copy">
          <p className="eyebrow">FOUNDATION</p>
          <h2>Built for a trusted talent process.</h2>
          <p>
            Role-based access, tenant isolation, and auditable workflows provide the backbone for
            every capability decision.
          </p>
        </div>
        <div className="cards">
          <article>
            <b>01</b>
            <h3>Role clarity</h3>
            <p>Structured role descriptions and ASK framework alignment.</p>
          </article>
          <article>
            <b>02</b>
            <h3>Capability insight</h3>
            <p>Assessment signals made ready for meaningful conversations.</p>
          </article>
          <article>
            <b>03</b>
            <h3>Succession readiness</h3>
            <p>Critical-role visibility for deliberate workforce planning.</p>
          </article>
        </div>
      </section>
      <footer>
        <span>KDDL Dials Talent Transformation Platform</span>
        <span>Internal workspace / {new Date().getFullYear()}</span>
      </footer>

      {isOpen && (
        <div
          className="dialog-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setIsOpen(false);
              setEmail("");
              setPassword("");
            }
          }}
        >
          <section className="dialog" role="dialog" aria-modal="true" aria-labelledby="sign-in-title">
            <button
              className="close-btn"
              aria-label="Close sign in"
              onClick={() => {
                setIsOpen(false);
                setEmail("");
                setPassword("");
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
            <p className="eyebrow">SECURE ACCESS</p>
            <h2 id="sign-in-title">Sign in to the platform</h2>
            <p className="dialog-subtext">Use your KDDL corporate credentials to continue.</p>

            {message && (
              <div className="login-message login-error" role="alert">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="12" y1="8" x2="12" y2="12"></line>
                  <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
                <span>{message}</span>
              </div>
            )}

            <form onSubmit={signIn} className="login-form" autoComplete="off">
              {/* Trap Chrome/Edge autofill mechanisms */}
              <input type="text" style={{ display: "none" }} tabIndex={-1} autoComplete="off" />
              <input type="password" style={{ display: "none" }} tabIndex={-1} autoComplete="off" />

              <label>
                Email
                <input
                  type="email"
                  name="kddl_auth_email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  onFocus={() => setEmailReadOnly(false)}
                  readOnly={emailReadOnly}
                  placeholder="Enter your email"
                  autoComplete="off"
                  required
                  disabled={isLoading}
                />
              </label>

              <label>
                Password
                <div className="password-input-wrap">
                  <input
                    type={showPassword ? "text" : "password"}
                    name="kddl_auth_password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    onFocus={() => setPasswordReadOnly(false)}
                    readOnly={passwordReadOnly}
                    placeholder="Enter password"
                    autoComplete="new-password"
                    required
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    className="password-toggle-btn"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    tabIndex={-1}
                  >
                    {showPassword ? (
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                        <line x1="1" y1="1" x2="23" y2="23"></line>
                      </svg>
                    ) : (
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                        <circle cx="12" cy="12" r="3"></circle>
                      </svg>
                    )}
                  </button>
                </div>
              </label>

              <button type="submit" className="login-submit-btn" disabled={isLoading}>
                {isLoading ? (
                  <span className="btn-loading">
                    <span className="spinner"></span>
                    Signing in...
                  </span>
                ) : (
                  "Sign in"
                )}
              </button>
            </form>

            <div className="login-footer-security">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
              </svg>
              <span>Authorized KDDL Personnel · Protected Workspace</span>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
