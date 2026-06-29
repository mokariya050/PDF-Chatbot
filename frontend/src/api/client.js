import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5000/api";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 min timeout for large PDF processing
});

// ----------------------------------------------------------------
// Auth API
// ----------------------------------------------------------------

/**
 * Register a new user.
 * @param {string} name
 * @param {string} email
 * @param {string} password
 */
export const signupUser = async (name, email, password) => {
  const response = await api.post("/auth/signup", { name, email, password });
  return response.data;
};

/**
 * Login an existing user.
 * @param {string} email
 * @param {string} password
 */
export const loginUser = async (email, password) => {
  const response = await api.post("/auth/login", { email, password });
  return response.data;
};

/**
 * Get the current user's profile.
 */
export const getProfile = async () => {
  const response = await api.get("/auth/me");
  return response.data;
};

// ----------------------------------------------------------------
// App API (all require JWT — handled by AuthContext interceptor)
// ----------------------------------------------------------------

/**
 * Check backend status and whether a PDF is loaded.
 */
export const getStatus = async () => {
  const response = await api.get("/status");
  return response.data;
};

/**
 * Upload a PDF file for processing.
 * @param {File} file - The PDF file to upload
 * @param {Function} onProgress - Progress callback (0-100)
 */
export const uploadPDF = async (file, onProgress) => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percent = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        onProgress(percent);
      }
    },
  });
  return response.data;
};

/**
 * Send a question about the uploaded PDF.
 * @param {string} question - The user's question
 */
export const askQuestion = async (question) => {
  const response = await api.post("/chat", { question });
  return response.data;
};

/**
 * Reset the backend state (clear PDF and vector store).
 */
export const resetChat = async () => {
  const response = await api.delete("/reset");
  return response.data;
};

/**
 * Get chat history for the current user.
 * @param {string} [pdfId] - Optional PDF ID filter
 * @param {number} [limit=50] - Max results
 */
export const getHistory = async (pdfId, limit = 50) => {
  const params = { limit };
  if (pdfId) params.pdf_id = pdfId;

  const response = await api.get("/history", { params });
  return response.data;
};

export default api;
