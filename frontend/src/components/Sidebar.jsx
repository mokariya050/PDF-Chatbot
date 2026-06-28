export default function Sidebar({ pdfInfo, onReset, isUploading }) {
  return (
    <aside className="sidebar" id="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <div className="logo-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14,2 14,8 20,8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10,9 9,9 8,9" />
            </svg>
          </div>
          <div className="logo-text">
            <h1>PDF ChatBot</h1>
            <span className="logo-subtitle">AI-Powered Document Q&A</span>
          </div>
        </div>
      </div>

      <div className="sidebar-content">
        {pdfInfo ? (
          <div className="pdf-info-card">
            <div className="pdf-info-header">
              <div className="pdf-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14,2 14,8 20,8" />
                </svg>
              </div>
              <span className="pdf-status-badge">Active</span>
            </div>
            <p className="pdf-filename" title={pdfInfo.filename}>
              {pdfInfo.filename}
            </p>
            <div className="pdf-stats">
              <div className="stat">
                <span className="stat-value">{pdfInfo.num_pages}</span>
                <span className="stat-label">Pages</span>
              </div>
              <div className="stat-divider"></div>
              <div className="stat">
                <span className="stat-value">{pdfInfo.num_chunks}</span>
                <span className="stat-label">Chunks</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="no-pdf-card">
            <div className="no-pdf-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <p>No PDF uploaded yet</p>
            <span>Upload a document to start chatting</span>
          </div>
        )}

        <div className="sidebar-section">
          <h3 className="section-title">How it works</h3>
          <div className="steps">
            <div className="step">
              <div className="step-number">1</div>
              <p>Upload a PDF document</p>
            </div>
            <div className="step">
              <div className="step-number">2</div>
              <p>AI processes & indexes content</p>
            </div>
            <div className="step">
              <div className="step-number">3</div>
              <p>Ask questions, get instant answers</p>
            </div>
          </div>
        </div>
      </div>

      <div className="sidebar-footer">
        {pdfInfo && (
          <button
            className="reset-button"
            onClick={onReset}
            disabled={isUploading}
            id="reset-button"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="1,4 1,10 7,10" />
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
            </svg>
            Reset & Upload New PDF
          </button>
        )}
        <div className="powered-by">
          Powered by <strong>Gemini</strong> + <strong>LangChain</strong>
        </div>
      </div>
    </aside>
  );
}
