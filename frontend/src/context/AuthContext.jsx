import { createContext, useContext, useState, useEffect } from "react";
import api from "../api/client";

const AuthContext = createContext(null);

/**
 * AuthProvider wraps the app and provides auth state + methods.
 *
 * Manages:
 *   - user object (id, name, email)
 *   - JWT token (stored in localStorage)
 *   - login / signup / logout functions
 *   - Auto-restore session on page refresh
 *   - Axios interceptor for attaching Bearer token
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [loading, setLoading] = useState(true);

  // Set up axios interceptor to attach token to every request
  useEffect(() => {
    const interceptor = api.interceptors.request.use(
      (config) => {
        const storedToken = localStorage.getItem("token");
        if (storedToken) {
          config.headers.Authorization = `Bearer ${storedToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    return () => api.interceptors.request.eject(interceptor);
  }, []);

  // Auto-restore session on mount
  useEffect(() => {
    const restoreSession = async () => {
      const storedToken = localStorage.getItem("token");
      if (!storedToken) {
        setLoading(false);
        return;
      }

      try {
        const response = await api.get("/auth/me");
        setUser(response.data.user);
        setToken(storedToken);
      } catch {
        // Token expired or invalid — clear it
        localStorage.removeItem("token");
        setToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    restoreSession();
  }, []);

  const login = async (email, password) => {
    const response = await api.post("/auth/login", { email, password });
    const { token: newToken, user: userData } = response.data;

    localStorage.setItem("token", newToken);
    setToken(newToken);
    setUser(userData);

    return response.data;
  };

  const signup = async (name, email, password) => {
    const response = await api.post("/auth/signup", {
      name,
      email,
      password,
    });
    const { token: newToken, user: userData } = response.data;

    localStorage.setItem("token", newToken);
    setToken(newToken);
    setUser(userData);

    return response.data;
  };

  const logout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  };

  const value = {
    user,
    token,
    isAuthenticated: !!user && !!token,
    loading,
    login,
    signup,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Hook to access auth state and methods.
 *
 * Usage:
 *   const { user, login, logout, isAuthenticated } = useAuth();
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
