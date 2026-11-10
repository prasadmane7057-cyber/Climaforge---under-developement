import { createContext } from 'react';
import type { UserProfile, AuthStatus, PermissionName } from '../types/auth';

export interface AuthContextType {
  user: UserProfile | null;
  status: AuthStatus;
  error: string | null;
  isLoginModalOpen: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
  openLoginModal: () => void;
  closeLoginModal: () => void;
  hasRole: (...roles: string[]) => boolean;
  hasPermission: (permission: PermissionName) => boolean;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

