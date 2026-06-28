import { useEffect, useRef } from "react";

export default function ChatMessage({ message }) {
  const messageRef = useRef(null);

  useEffect(() => {
    messageRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const isUser = message.role === "user";
  const isLoading = message.isLoading;

  return (
    <div
      className={`chat-message ${isUser ? "user" : "bot"}`}
      ref={messageRef}
      id={`message-${message.id}`}
    >
      <div className="message-avatar">
        {isUser ? (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        ) : (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2a4 4 0 0 1 4 4v1h1a3 3 0 0 1 3 3v1a3 3 0 0 1-3 3h-1v4H8v-4H7a3 3 0 0 1-3-3v-1a3 3 0 0 1 3-3h1V6a4 4 0 0 1 4-4z" />
            <circle cx="9" cy="10" r="1" />
            <circle cx="15" cy="10" r="1" />
          </svg>
        )}
      </div>
      <div className="message-content">
        <div className="message-label">{isUser ? "You" : "PDF Assistant"}</div>
        {isLoading ? (
          <div className="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        ) : (
          <div className="message-text">{message.content}</div>
        )}
      </div>
    </div>
  );
}
