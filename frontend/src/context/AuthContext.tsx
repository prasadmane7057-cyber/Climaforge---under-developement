/**
 * Centralized Authentication & RBAC Provider for CLIMAFORGE M16A.6.
 *
 * Provides:
 * - Centralized auth state: 'loading' | 'authenticated' | 'unauthenticated' | 'session-expired'
 * - Session restoration on initial load via silent refresh
 * - Permission and role evaluation based on canonical backend definitions
 * - Login / Logout handlers
 * - Login modal display control
 */

import React, {
  useState,
  useEffect,
  useCallback,
  useMemo,
  type ReactNode,
} from 'react';
import type {
  UserProfile,
  AuthStatus,
  PermissionName,
} from '../types/auth';
import {
  userHasPermission,
  userHasAnyRole,
} from '../types/auth';
import {
  loginUser,
  logoutUser,
  restoreSession,
  onSessionExpired,
  fetchCurrentUser,
} from '../services/auth';
import { onAuthBroadcast } from '../services/authSync';
import { AuthContext, type AuthContextType } from './authContextDef';

export interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [error, setError] = useState<string | null>(null);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState<boolean>(false);

  // 1. Session Restoration on initial mount
  useEffect(() => {
    let isMounted = true;

    async function initSession() {
      try {
        const restoredUser = await restoreSession();
        if (!isMounted) return;

        if (restoredUser) {
          setUser(restoredUser);
          setStatus('authenticated');
        } else {
          setUser(null);
          setStatus('unauthenticated');
        }
      } catch {
        if (!isMounted) return;
        setUser(null);
        setStatus('unauthenticated');
      }
    }

    initSession();

    // 2. Subscribe to session expiration events from API interceptor
    const unsubscribeLocal = onSessionExpired(() => {
      if (!isMounted) return;
      setUser((currentUser) => {
        if (currentUser) {
          setStatus('session-expired');
        }
        return null;
      });
    });

    // 3. Subscribe to cross-tab auth broadcast events (M16A.7)
    const unsubscribeSync = onAuthBroadcast(async (msg) => {
      if (!isMounted) return;

      if (msg.type === 'AUTH_LOGOUT') {
        setUser(null);
        setStatus('unauthenticated');
        setError(null);
      } else if (msg.type === 'SESSION_EXPIRED') {
        setUser(null);
        setStatus('session-expired');
      } else if (msg.type === 'AUTH_LOGIN') {
        try {
          const profile = await fetchCurrentUser();
          if (isMounted) {
            setUser(profile);
            setStatus('authenticated');
            setError(null);
            setIsLoginModalOpen(false);
          }
        } catch {
          // Ignore sync failure
        }
      } else if (msg.type === 'REFRESH_COMPLETED') {
        setUser((currentUser) => {
          if (!currentUser) {
            fetchCurrentUser()
              .then((profile) => {
                if (isMounted) {
                  setUser(profile);
                  setStatus('authenticated');
                }
              })
              .catch(() => {});
          }
          return currentUser;
        });
      }
    });

    return () => {
      isMounted = false;
      unsubscribeLocal();
      unsubscribeSync();
    };
  }, []);

  // 3. Clear auth error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // 4. Modal controls
  const openLoginModal = useCallback(() => {
    clearError();
    setIsLoginModalOpen(true);
  }, [clearError]);

  const closeLoginModal = useCallback(() => {
    clearError();
    setIsLoginModalOpen(false);
  }, [clearError]);

  // 5. Login action
  const login = useCallback(
    async (email: string, password: string) => {
      clearError();
      try {
        const result = await loginUser(email, password);
        setUser(result.user);
        setStatus('authenticated');
        setIsLoginModalOpen(false);
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Login failed';
        setError(msg);
        throw err;
      }
    },
    [clearError]
  );

  // 6. Logout action
  const logout = useCallback(async () => {
    clearError();
    try {
      await logoutUser();
    } finally {
      setUser(null);
      setStatus('unauthenticated');
    }
  }, [clearError]);

  // 7. Role check
  const hasRole = useCallback(
    (...roles: string[]): boolean => {
      return userHasAnyRole(user, ...roles);
    },
    [user]
  );

  // 8. Permission check
  const hasPermission = useCallback(
    (permission: PermissionName): boolean => {
      return userHasPermission(user, permission);
    },
    [user]
  );

  const contextValue = useMemo<AuthContextType>(
    () => ({
      user,
      status,
      error,
      isLoginModalOpen,
      login,
      logout,
      clearError,
      openLoginModal,
      closeLoginModal,
      hasRole,
      hasPermission,
    }),
    [
      user,
      status,
      error,
      isLoginModalOpen,
      login,
      logout,
      clearError,
      openLoginModal,
      closeLoginModal,
      hasRole,
      hasPermission,
    ]
  );

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
};

export default AuthProvider;
