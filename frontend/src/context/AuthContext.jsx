/**
 * AuthContext.jsx
 * Cung cấp trạng thái xác thực (user, loading) và các hàm auth cho toàn app.
 */
import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { authService } from "../services/authService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null);   // null = chưa đăng nhập
  const [loading, setLoading] = useState(true);   // true khi đang kiểm tra session

  // Kiểm tra session hiện tại khi load app (cookie tự gửi cùng request)
  useEffect(() => {
    let cancelled = false;
    let retryTimer;

    const restoreSession = async (attempt = 0) => {
      try {
        const data = await authService.me();
        if (cancelled) return;
        setUser(data);
        setLoading(false);
      } catch (err) {
        if (cancelled) return;

        // Backend có thể mất vài giây khi đang reload/restart.
        // Retry để không làm mất role admin chỉ vì lỗi kết nối tạm thời.
        if (attempt < 20) {
          retryTimer = window.setTimeout(() => restoreSession(attempt + 1), 500);
          return;
        }

        setUser(null);
        setLoading(false);
      }
    };

    restoreSession();
    return () => {
      cancelled = true;
      if (retryTimer) window.clearTimeout(retryTimer);
    };
  }, []);

  /** Đăng nhập → cập nhật user state */
  const login = useCallback(async (email, password) => {
    const data = await authService.login(email, password);
    setUser(data.user);
    return data;
  }, []);

  /** Đăng nhập / đăng ký qua Google → cập nhật user state */
  const loginWithGoogle = useCallback(async (credential) => {
    const data = await authService.loginWithGoogle(credential);
    setUser(data.user);
    return data;
  }, []);

  /** Đăng ký → cập nhật user state */
  const register = useCallback(async (username, email, password) => {
    const data = await authService.register(username, email, password);
    setUser(data.user);
    return data;
  }, []);

  /** Đăng xuất → xoá user state */
  const logout = useCallback(async () => {
    await authService.logout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, loginWithGoogle, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

/** Hook để dùng trong component */
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth phải được dùng bên trong <AuthProvider>");
  return ctx;
}
