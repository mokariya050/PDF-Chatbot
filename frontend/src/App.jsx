import { useState, useRef, useEffect } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import AuthPage from "./components/AuthPage";
import Sidebar from "./components/Sidebar";
import FileUpload from "./components/FileUpload";
import ChatMessage from "./components/ChatMessage";
import ChatInput from "./components/ChatInput";
import { askQuestion, resetChat, getStatus } from "./api/client";
import "./App.css";

let messageIdCounter = 0;
const nextId = () => ++messageIdCounter;

function ChatApp() {
  const { user, logout } = useAuth();
  const [messages, setMessages] = useState([]);
  const [pdfInfo, setPdfInfo] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const chatEndRef = useRef(null);

  // Check backend status on mount
  useEffect(() => {
    getStatus()
      .then((data) => {
        if (data.pdf_loaded && data.pdf_name) {
          setPdfInfo({
            filename: data.pdf_name,
            num_pages: data.num_pages,
            num_chunks: data.num_chunks,
          });
        }
      })
      .catch(() => {
        // Backend not running yet — that's ok
      });
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleUploadSuccess = (result) => {
    setPdfInfo(result);
    setMessages([
      {
        id: nextId(),
        role: "bot",
        content: `✅ "${result.filename}" has been uploaded and processed successfully!\n\n📄 ${result.num_pages} pages extracted → ${result.num_chunks} searchable chunks created.\n\nI'm ready to answer questions about your document. Go ahead and ask!`,
      },
    ]);
  };

  const handleSend = async (question) => {
    const userMsg = { id: nextId(), role: "user", content: question };
    const loadingMsg = { id: nextId(), role: "bot", isLoading: true, content: "" };

    setMessages((prev) => [...prev, userMsg, loadingMsg]);
    setIsThinking(true);

    try {
      const data = await askQuestion(question);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === loadingMsg.id
            ? { ...msg, isLoading: false, content: data.answer }
            : msg
        )
      );
    } catch (err) {
      const errorText =
        err.response?.data?.error || "Something went wrong. Please try again.";
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === loadingMsg.id
            ? { ...msg, isLoading: false, content: `❌ ${errorText}` }
            : msg
        )
      );
    } finally {
      setIsThinking(false);
    }
  };

  const handleReset = async () => {
    try {
      await resetChat();
      setPdfInfo(null);
      setMessages([]);
    } catch {
      // Silently fail — user can try again
    }
  };

  return (
    <div className="app">
      <Sidebar
        pdfInfo={pdfInfo}
        onReset={handleReset}
        isUploading={isUploading}
        user={user}
        onLogout={logout}
      />

      <main className="main-content">
        <div className="chat-container">
          {!pdfInfo && !isUploading ? (
            <div className="welcome-screen">
              <div className="welcome-header">
                <div className="welcome-icon-wrapper">
                  <div className="welcome-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                    </svg>
                  </div>
                </div>
                <h2>Chat with your PDF</h2>
                <p>Upload a PDF document and start asking questions. The AI will find answers directly from your document content.</p>
              </div>
              <FileUpload
                onUploadSuccess={handleUploadSuccess}
                isUploading={isUploading}
                setIsUploading={setIsUploading}
              />
              <div className="feature-grid">
                <div className="feature-card">
                  <div className="feature-icon">⚡</div>
                  <h4>Lightning Fast</h4>
                  <p>Instant answers from your documents</p>
                </div>
                <div className="feature-card">
                  <div className="feature-icon">🎯</div>
                  <h4>Accurate</h4>
                  <p>Answers grounded in actual content</p>
                </div>
                <div className="feature-card">
                  <div className="feature-icon">🔒</div>
                  <h4>Private</h4>
                  <p>Your documents stay on your machine</p>
                </div>
              </div>
            </div>
          ) : isUploading ? (
            <div className="welcome-screen">
              <FileUpload
                onUploadSuccess={handleUploadSuccess}
                isUploading={isUploading}
                setIsUploading={setIsUploading}
              />
            </div>
          ) : (
            <>
              <div className="messages-area" id="messages-area">
                {messages.map((msg) => (
                  <ChatMessage key={msg.id} message={msg} />
                ))}
                <div ref={chatEndRef} />
              </div>
              <ChatInput onSend={handleSend} disabled={isThinking} />
            </>
          )}
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRouter />
    </AuthProvider>
  );
}

function AppRouter() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="auth-loading">
        <div className="auth-loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  return isAuthenticated ? <ChatApp /> : <AuthPage />;
}
