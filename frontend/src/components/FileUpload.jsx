import { useState, useRef } from "react";
import { uploadPDF } from "../api/client";

export default function FileUpload({ onUploadSuccess, isUploading, setIsUploading }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleFile = async (file) => {
    if (!file) return;

    // Validate file type
    if (file.type !== "application/pdf" && !file.name.endsWith(".pdf")) {
      setError("Only PDF files are accepted.");
      return;
    }

    // Validate file size (50 MB)
    if (file.size > 50 * 1024 * 1024) {
      setError("File size exceeds 50 MB limit.");
      return;
    }

    setError(null);
    setIsUploading(true);
    setUploadProgress(0);

    try {
      const result = await uploadPDF(file, (progress) => {
        setUploadProgress(progress);
      });
      onUploadSuccess(result);
    } catch (err) {
      const message =
        err.response?.data?.error || "Upload failed. Please try again.";
      setError(message);
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    handleFile(file);
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleInputChange = (e) => {
    const file = e.target.files[0];
    handleFile(file);
    e.target.value = "";
  };

  return (
    <div
      className={`file-upload-zone ${isDragging ? "dragging" : ""} ${isUploading ? "uploading" : ""}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={!isUploading ? handleClick : undefined}
      id="file-upload-zone"
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        onChange={handleInputChange}
        style={{ display: "none" }}
        id="file-input"
      />

      {isUploading ? (
        <div className="upload-progress">
          <div className="upload-spinner"></div>
          <p className="upload-status">Processing PDF...</p>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${uploadProgress}%` }}
            ></div>
          </div>
          <p className="upload-percent">{uploadProgress}%</p>
        </div>
      ) : (
        <div className="upload-content">
          <div className="upload-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14,2 14,8 20,8" />
              <line x1="12" y1="18" x2="12" y2="12" />
              <polyline points="9,15 12,12 15,15" />
            </svg>
          </div>
          <p className="upload-title">Drop your PDF here</p>
          <p className="upload-subtitle">or click to browse • Max 50 MB</p>
        </div>
      )}

      {error && (
        <div className="upload-error">
          <span>⚠</span> {error}
        </div>
      )}
    </div>
  );
}
