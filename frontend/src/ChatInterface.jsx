import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import "./ChatInterface.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";

function authConfig() {
  const token = localStorage.getItem("auth_token");
  const userId = localStorage.getItem("user_id");
  return {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(userId ? { "X-User-Id": userId } : {}),
    },
  };
}

function makeAssistantMessage(content, metadata = null) {
  return { role: "assistant", content, metadata };
}

function formatTime(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);
  const diffMinutes = Math.floor((Date.now() - date.getTime()) / 60000);
  if (diffMinutes < 1) return "just now";
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

export default function ChatInterface({ userId }) {
  const [messages, setMessages] = useState([
    makeAssistantMessage("Hi. Ask me anything and I’ll show the generated answer here."),
  ]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [contextWindow, setContextWindow] = useState("");
  const [useRAG, setUseRAG] = useState(true);
  const [useQuantization, setUseQuantization] = useState(false);
  const [modelName, setModelName] = useState("sshleifer/tiny-gpt2");
  const [useWebSocket, setUseWebSocket] = useState(false);
  const [models, setModels] = useState([]);
  const [previousChats, setPreviousChats] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeAnswerDetails, setActiveAnswerDetails] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const loadModels = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/models`, authConfig());
        setModels(Array.isArray(response.data?.models) ? response.data.models : []);
      } catch (error) {
        console.error("Failed to load models:", error);
      }
    };

    const loadPreviousChats = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/chat`, authConfig());
        const sessions = Array.isArray(response.data?.sessions) ? response.data.sessions : [];
        setPreviousChats(sessions.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at)));
      } catch (error) {
        console.error("Failed to load previous chats:", error);
      }
    };

    loadModels();
    loadPreviousChats();
  }, []);

  const refreshPreviousChats = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/chat`, authConfig());
      const sessions = Array.isArray(response.data?.sessions) ? response.data.sessions : [];
      setPreviousChats(sessions.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at)));
    } catch (error) {
      console.error("Failed to refresh chats:", error);
    }
  };

  const loadChat = async (chatSessionId) => {
    try {
      const response = await axios.get(`${API_URL}/api/chat/${chatSessionId}`, authConfig());
      setMessages(Array.isArray(response.data?.messages) && response.data.messages.length > 0 ? response.data.messages : [makeAssistantMessage("This chat is empty.")]);
      setSessionId(chatSessionId);
      setContextWindow("");
    } catch (error) {
      console.error("Failed to load chat:", error);
    }
  };

  const handleNewChat = () => {
    setMessages([makeAssistantMessage("New chat started. Send a prompt and I’ll show the answer here.")]);
    setSessionId(null);
    setContextWindow("");
    setActiveAnswerDetails(false);
  };

  const handleDeleteChat = async (chatSessionId) => {
    try {
      await axios.delete(`${API_URL}/api/chat/${chatSessionId}`, authConfig());
      setPreviousChats((current) => current.filter((chat) => chat.session_id !== chatSessionId));
      if (sessionId === chatSessionId) {
        handleNewChat();
      }
    } catch (error) {
      console.error("Failed to delete chat:", error);
    }
  };

  const postChat = async (messageText) => {
    const response = await axios.post(
      `${API_URL}/api/chat`,
      {
        message: messageText,
        session_id: sessionId,
        use_rag: useRAG,
        use_quantization: useQuantization,
        model_name: modelName,
      },
      authConfig()
    );

    if (!sessionId && response.data?.session_id) {
      setSessionId(response.data.session_id);
    }

    setContextWindow(response.data?.context_window || "");
    setMessages((current) => [...current, response.data?.message || makeAssistantMessage("No response returned.")]);
    await refreshPreviousChats();
  };

  const handleSendMessageREST = async () => {
    if (!inputValue.trim()) return;
    const messageText = inputValue.trim();
    setMessages((current) => [...current, { role: "user", content: messageText, metadata: null }]);
    setInputValue("");
    setLoading(true);

    try {
      await postChat(messageText);
    } catch (error) {
      console.error("Error:", error);
      setMessages((current) => [...current, makeAssistantMessage("Sorry, I encountered an error. Please try again.")]);
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessageWebSocket = async () => {
    if (!inputValue.trim()) return;
    const messageText = inputValue.trim();
    setMessages((current) => [...current, { role: "user", content: messageText, metadata: null }]);
    setInputValue("");
    setLoading(true);

    try {
      const ws = new WebSocket(`${WS_URL.replace(/^http/, "ws")}/ws/chat/${sessionId || "new"}`);
      let fullResponse = "";
      let metadata = null;

      ws.onopen = () => {
        ws.send(JSON.stringify({
          message: messageText,
          session_id: sessionId,
          use_rag: useRAG,
          use_quantization: useQuantization,
          model_name: modelName,
        }));
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === "token") {
          fullResponse += data.data;
          setMessages((current) => {
            const updated = [...current];
            const last = updated[updated.length - 1];
            if (last?.role === "assistant") {
              last.content = fullResponse;
            } else {
              updated.push(makeAssistantMessage(fullResponse));
            }
            return updated;
          });
        }

        if (data.type === "metadata") {
          metadata = data.data;
        }

        if (data.type === "complete") {
          if (!sessionId && data.data?.session_id) {
            setSessionId(data.data.session_id);
          }
          setContextWindow(data.data?.context_window || "");
          setMessages((current) => {
            const updated = [...current];
            const last = updated[updated.length - 1];
            if (last?.role === "assistant") {
              last.metadata = metadata;
            }
            return updated;
          });
          setLoading(false);
          refreshPreviousChats();
        }

        if (data.type === "error") {
          setMessages((current) => [...current, makeAssistantMessage(`Error: ${data.data}`)]);
          setLoading(false);
        }
      };

      ws.onerror = () => setLoading(false);
      ws.onclose = () => setLoading(false);
    } catch (error) {
      console.error("WebSocket Error:", error);
      setMessages((current) => [...current, makeAssistantMessage("Sorry, I encountered an error. Please try again.")]);
      setLoading(false);
    }
  };

  const handleSendMessage = useWebSocket ? handleSendMessageWebSocket : handleSendMessageREST;

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="chat-shell">
      <aside className={`chat-sidebar ${sidebarOpen ? "open" : "closed"}`}>
        <div className="sidebar-top">
          <div>
            <div className="eyebrow">LLM Lab</div>
            <h1 className="sidebar-heading">Conversations</h1>
          </div>
          <button className="icon-button" onClick={() => setSidebarOpen((v) => !v)}>
            {sidebarOpen ? "◀" : "▶"}
          </button>
        </div>

        <button className="new-chat-button" onClick={handleNewChat}>
          + New Chat
        </button>

        <div className="history-list">
          {previousChats.length > 0 ? previousChats.map((chat) => (
            <div key={chat.session_id} className={`history-card ${sessionId === chat.session_id ? "active" : ""}`}>
              <button className="history-main" onClick={() => loadChat(chat.session_id)}>
                <div className="history-title">{chat.title || "Untitled chat"}</div>
                <div className="history-subtitle">{chat.message_count} messages • {formatTime(chat.updated_at)}</div>
              </button>
              <button className="history-delete" onClick={() => handleDeleteChat(chat.session_id)}>×</button>
            </div>
          )) : <div className="history-empty">No previous chats yet.</div>}
        </div>

        <div className="sidebar-panel">
          <div className="panel-label">Model</div>
          <select className="select-field" value={modelName} onChange={(e) => setModelName(e.target.value)}>
            {models.length > 0 ? models.map((model) => <option key={model.name} value={model.name}>{model.name}</option>) : <option value="sshleifer/tiny-gpt2">sshleifer/tiny-gpt2</option>}
          </select>

          <label className="toggle-row"><input type="checkbox" checked={useRAG} onChange={(e) => setUseRAG(e.target.checked)} /> Hybrid RAG</label>
          <label className="toggle-row"><input type="checkbox" checked={useQuantization} onChange={(e) => setUseQuantization(e.target.checked)} /> 4-bit Quantization</label>
          <label className="toggle-row"><input type="checkbox" checked={useWebSocket} onChange={(e) => setUseWebSocket(e.target.checked)} /> WebSocket Streaming</label>

          <div className="user-pill">{userId}</div>
        </div>
      </aside>

      <main className="chat-main">
        <header className="chat-header">
          <div>
            <div className="eyebrow">Assistant Answer</div>
            <h2>Generated response, context, and history</h2>
          </div>
          <div className="status-chip">{loading ? "Generating..." : "Ready"}</div>
        </header>

        <section className="answer-summary">
          <div className="answer-summary-title">Latest context</div>
          <div className="answer-summary-body">{contextWindow || "No context yet. Send a message to populate the generated answer and context window."}</div>
        </section>

        <section className="messages-list">
          {messages.map((message, index) => (
            <article key={index} className={`message-card ${message.role}`}>
              <div className="message-avatar">{message.role === "user" ? "You" : "AI"}</div>
              <div className="message-body">
                <div className="message-role">{message.role === "user" ? "Your prompt" : "Chatbot answer"}</div>
                <div className="message-content">{message.content}</div>
                {message.metadata && (
                  <div className="message-details">
                    <button className="details-button" onClick={() => setActiveAnswerDetails((v) => !v)}>
                      {activeAnswerDetails ? "Hide details" : "Show details"}
                    </button>
                    {activeAnswerDetails && (
                      <div className="details-grid">
                        <div><span>Tokens</span><strong>{message.metadata.tokens_generated}</strong></div>
                        <div><span>Latency</span><strong>{message.metadata.latency_ms} ms</strong></div>
                        <div><span>Model</span><strong>{message.metadata.model_name}</strong></div>
                        <div><span>Retrieved docs</span><strong>{message.metadata.retrieved_docs?.length || 0}</strong></div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </article>
          ))}

          {loading && (
            <article className="message-card assistant loading">
              <div className="message-avatar">AI</div>
              <div className="message-body">
                <div className="message-role">Generating answer</div>
                <div className="typing-dots"><span></span><span></span><span></span></div>
              </div>
            </article>
          )}

          <div ref={messagesEndRef} />
        </section>

        <footer className="composer">
          <textarea
            className="composer-input"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question, then the chatbot answer will appear above."
            rows={3}
          />
          <button className="composer-send" onClick={handleSendMessage} disabled={loading || !inputValue.trim()}>
            {loading ? "Sending..." : "Send"}
          </button>
        </footer>
      </main>
    </div>
  );
}