import { useState } from "react";
import { useAuth } from "../context/AuthContext";

/**
 * AuthPage — Combined Login/Signup form with animated toggle.
 *
 * Features:
 *   - Toggle between login and signup modes
 *   - Client-side validation
 *   - Error display with animation
 *   - Premium glassmorphism design
 */
export default function AuthPage() {
  const { login, signup } = useAuth();
  const [isSignup, setIsSignup] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Client-side validation
    if (isSignup && name.trim().length < 2) {
      setError("Name must be at least 2 characters");
      return;
    }
    if (!email.includes("@")) {
      setError("Please enter a valid email address");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }

    setIsLoading(true);

    try {
      if (isSignup) {
        await signup(name.trim(), email.trim(), password);
      } else {
        await login(email.trim(), password);
      }
    } catch (err) {
      const message =
        err.response?.data?.error || "Something went wrong. Please try again.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleMode = () => {
    setIsSignup(!isSignup);
    setError(null);
  };

  return (
    <div className="auth-page">
      {/* Background decorative elements */}
      <div className="auth-bg-orb auth-bg-orb-1"></div>
      <div className="auth-bg-orb auth-bg-orb-2"></div>
      <div className="auth-bg-orb auth-bg-orb-3"></div>

      <div className="auth-container">
        {/* Logo */}
        <div className="auth-logo">
          <div className="auth-logo-icon">
            <svg
              width="32"
              height="32"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14,2 14,8 20,8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10,9 9,9 8,9" />
            </svg>
          </div>
          <h1>PDF ChatBot</h1>
          <p className="auth-subtitle">AI-Powered Document Q&A</p>
        </div>

        {/* Form Card */}
        <div className="auth-card">
          <h2>{isSignup ? "Create Account" : "Welcome Back"}</h2>
          <p className="auth-card-subtitle">
            {isSignup
              ? "Sign up to start chatting with your documents"
              : "Sign in to continue your conversations"}
          </p>

          <form onSubmit={handleSubmit} className="auth-form" id="auth-form">
            {isSignup && (
              <div className="auth-field">
                <label htmlFor="auth-name">Name</label>
                <input
                  id="auth-name"
                  type="text"
                  placeholder="Your name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  autoComplete="name"
                />
              </div>
            )}

            <div className="auth-field">
              <label htmlFor="auth-email">Email</label>
              <input
                id="auth-email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />
            </div>

            <div className="auth-field">
              <label htmlFor="auth-password">Password</label>
              <input
                id="auth-password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={isSignup ? "new-password" : "current-password"}
              />
            </div>

            {error && (
              <div className="auth-error" id="auth-error">
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <circle cx="12" cy="12" r="10" />
                  <line x1="15" y1="9" x2="9" y2="15" />
                  <line x1="9" y1="9" x2="15" y2="15" />
                </svg>
                {error}
              </div>
            )}

            <button
              type="submit"
              className="auth-submit"
              disabled={isLoading}
              id="auth-submit"
            >
              {isLoading ? (
                <span className="auth-spinner"></span>
              ) : isSignup ? (
                "Create Account"
              ) : (
                "Sign In"
              )}
            </button>
          </form>

          <div className="auth-toggle">
            <span>
              {isSignup
                ? "Already have an account?"
                : "Don't have an account?"}
            </span>
            <button
              type="button"
              onClick={toggleMode}
              className="auth-toggle-btn"
              id="auth-toggle-btn"
            >
              {isSignup ? "Sign In" : "Sign Up"}
            </button>
          </div>
        </div>

        <p className="auth-footer">
          Powered by <strong>Gemini</strong> + <strong>LangChain</strong>
        </p>
      </div>
    </div>
  );
}
