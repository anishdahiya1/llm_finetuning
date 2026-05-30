import React, { useState, useEffect } from "react";
import axios from "axios";
import AuthInterface from "./AuthInterface";
import ChatInterface from "./ChatInterface";
import "./App.css";

export default function App() {
  const [userId, setUserId] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is already logged in
    const token = localStorage.getItem("auth_token");
    const storedUserId = localStorage.getItem("user_id");

    if (token && storedUserId) {
      axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
      setUserId(storedUserId);
    }

    setLoading(false);
  }, []);

  if (loading) {
    return (
      <div className="app loading">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="app">
      {userId ? (
        <ChatInterface userId={userId} />
      ) : (
        <AuthInterface onLogin={(id) => setUserId(id)} />
      )}
    </div>
  );
}

