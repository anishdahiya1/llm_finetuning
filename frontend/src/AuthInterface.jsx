import React, { useState } from "react";
import axios from "axios";
import "./AuthInterface.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function setAuthHeaders(token, userId) {
  axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  axios.defaults.headers.common["X-User-Id"] = userId;
}

export default function AuthInterface({ onLogin }) {
  const [userId, setUserId] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!userId || !email) {
      setError("Please fill in all fields");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await axios.post(`${API_URL}/api/auth/login`, {
        user_id: userId,
        email: email,
      });

      const token = response.data.access_token;
      localStorage.setItem("auth_token", token);
      localStorage.setItem("user_id", userId);

      // Set default Auth header for future requests
      setAuthHeaders(token, userId);

      onLogin(userId);
    } catch (err) {
      setError("Login failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleGuest = async () => {
    const guestId = `guest_${Date.now()}`;
    const response = await axios.post(`${API_URL}/api/auth/login`, {
      user_id: guestId,
      email: `${guestId}@guest.local`,
    });

    const token = response.data.access_token;
    localStorage.setItem("auth_token", token);
    localStorage.setItem("user_id", guestId);
    setAuthHeaders(token, guestId);
    onLogin(guestId);
  };

  return (
    <div className="auth-container">
      <div className="auth-box">
        <h1>🚀 LLM Optimization Lab</h1>
        <p className="subtitle">ChatGPT-like interface with visible LLM optimization</p>

        <form onSubmit={handleLogin} className="auth-form">
          <div className="form-group">
            <label htmlFor="userId">User ID</label>
            <input
              id="userId"
              type="text"
              placeholder="your-username"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
            />
          </div>

          {error && <div className="auth-error">{error}</div>}

          <button type="submit" className="btn-login" disabled={loading}>
            {loading ? "Logging in..." : "Login"}
          </button>
        </form>

        <div className="auth-divider">or</div>

        <button onClick={handleGuest} className="btn-guest" disabled={loading}>
          Continue as Guest
        </button>

        <p className="auth-note">Multi-user isolation with JWT tokens. Each user gets their own chat sessions.</p>
      </div>
    </div>
  );
}
