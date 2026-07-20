import { useState } from "react";
import "./AuthPage.css";
import { API_BASE_URL } from "../config";

function AuthPage({ onLoginSuccess }) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    // Basic Validation
    if (!username.trim() || !password) {
      setError("Username and Password are required.");
      setLoading(false);
      return;
    }

    if (!isLogin && !email.trim()) {
      setError("Email is required for registration.");
      setLoading(false);
      return;
    }

    try {
      const endpoint = isLogin ? "/auth/login" : "/auth/register";
      const payload = isLogin 
        ? { username: username.trim(), password }
        : { username: username.trim(), email: email.trim(), password };

      const res = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Authentication failed.");
      }

      // Store token
      localStorage.setItem("auth-token", data.access_token);
      localStorage.setItem("auth-user", JSON.stringify(data.user));

      // Trigger success callback in App.jsx
      onLoginSuccess(data.user, data.access_token);
    } catch (err) {
      setError(err.message || "An unexpected error occurred. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const toggleAuthMode = () => {
    setIsLogin(!isLogin);
    setError("");
    setUsername("");
    setEmail("");
    setPassword("");
  };

  return (
    <div className="auth-container">
      <div className="auth-background-shapes">
        <div className="shape circle-1"></div>
        <div className="shape circle-2"></div>
      </div>
      
      <div className="auth-card">
        <div className="auth-card-header">
          <div className="logo-glow">⚡</div>
          <h1>AI Database Assistant</h1>
          <p className="subtitle">
            {isLogin ? "Sign in to access your databases" : "Create an account to get started"}
          </p>
        </div>

        {error && (
          <div className="auth-error-alert animate-shake">
            <span>⚠️</span>
            <span className="error-message">{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="input-group">
            <label htmlFor="username">{isLogin ? "Username or Email" : "Username"}</label>
            <input
              type="text"
              id="username"
              placeholder={isLogin ? "Enter username or email" : "Choose username"}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              disabled={loading}
              autoComplete="username"
            />
          </div>

          {!isLogin && (
            <div className="input-group animate-fade-in">
              <label htmlFor="email">Email Address</label>
              <input
                type="email"
                id="email"
                placeholder="Enter email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={loading}
                autoComplete="email"
              />
            </div>
          )}

          <div className="input-group">
            <label htmlFor="password">Password</label>
            <div className="password-input-wrapper">
              <input
                type={showPassword ? "text" : "password"}
                id="password"
                placeholder="Enter password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
                autoComplete="current-password"
              />
              <button
                type="button"
                className="password-toggle-btn"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex="-1"
              >
                {showPassword ? "👁️" : "👁️‍🗨️"}
              </button>
            </div>
          </div>

          <button type="submit" className="auth-submit-btn" disabled={loading}>
            {loading ? (
              <span className="spinner">⌛ Processing...</span>
            ) : isLogin ? (
              "Log In"
            ) : (
              "Register"
            )}
          </button>
        </form>

        <div className="auth-card-footer">
          <span>
            {isLogin ? "Don't have an account?" : "Already have an account?"}
          </span>
          <button type="button" className="auth-mode-toggle-btn" onClick={toggleAuthMode}>
            {isLogin ? "Register Now" : "Log In"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default AuthPage;
