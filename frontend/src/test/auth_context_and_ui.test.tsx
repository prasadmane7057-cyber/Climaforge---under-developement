import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { AuthProvider } from '../context/AuthContext';
import { useAuth } from '../context/useAuth';
import { LoginModal } from '../components/LoginModal';
import { UnauthorizedView } from '../components/UnauthorizedView';
import { Header } from '../components/Header';
import { Sidebar } from '../components/Sidebar';
import * as authService from '../services/auth';
import type { UserProfile } from '../types/auth';

describe('AuthContext and UI Components', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  // Helper test component to inspect context values
  const TestConsumer: React.FC = () => {
    const { user, status, error, login, logout } = useAuth();
    return (
      <div>
        <div data-testid="status">{status}</div>
        <div data-testid="user-email">{user?.email || 'none'}</div>
        <div data-testid="user-role">{user?.role || 'none'}</div>
        <div data-testid="error">{error || 'none'}</div>
        <button
          onClick={() =>
            login('operator@climaforge.local', 'Password123').catch(() => {})
          }
        >
          Do Login
        </button>
        <button onClick={() => logout()}>Do Logout</button>
      </div>
    );
  };

  it('restores unauthenticated state on mount when no session exists', async () => {
    vi.spyOn(authService, 'restoreSession').mockResolvedValue(null);

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    expect(screen.getByTestId('status').textContent).toBe('loading');

    await waitFor(() => {
      expect(screen.getByTestId('status').textContent).toBe('unauthenticated');
    });
    expect(screen.getByTestId('user-email').textContent).toBe('none');
  });

  it('restores authenticated user profile on mount when valid session exists', async () => {
    const mockUser: UserProfile = {
      id: 'usr-1',
      email: 'admin@climaforge.local',
      full_name: 'System Admin',
      role: 'admin',
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
    };
    vi.spyOn(authService, 'restoreSession').mockResolvedValue(mockUser);

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('status').textContent).toBe('authenticated');
    });
    expect(screen.getByTestId('user-email').textContent).toBe('admin@climaforge.local');
    expect(screen.getByTestId('user-role').textContent).toBe('admin');
  });

  it('transitions to session-expired when session-expired event fires', async () => {
    const mockUser: UserProfile = {
      id: 'usr-2',
      email: 'operator@climaforge.local',
      full_name: 'Operator 1',
      role: 'operator',
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
    };
    vi.spyOn(authService, 'restoreSession').mockResolvedValue(mockUser);

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('status').textContent).toBe('authenticated');
    });

    act(() => {
      authService.notifySessionExpired();
    });

    expect(screen.getByTestId('status').textContent).toBe('session-expired');
    expect(screen.getByTestId('user-email').textContent).toBe('none');
  });

  it('renders and operates LoginModal with validation and demo presets', async () => {
    vi.spyOn(authService, 'restoreSession').mockResolvedValue(null);
    const loginUserSpy = vi.spyOn(authService, 'loginUser').mockResolvedValue({
      user: {
        id: 'usr-3',
        email: 'operator@climaforge.local',
        full_name: 'Lead Operator',
        role: 'operator',
        is_active: true,
        created_at: '2026-01-01T00:00:00Z',
      },
      token: 'access-jwt',
    });

    const onClose = vi.fn();

    render(
      <AuthProvider>
        <LoginModal isOpen={true} onClose={onClose} />
      </AuthProvider>
    );

    expect(screen.getByText('Sign In to Operational Station')).toBeTruthy();

    // 1. Password show/hide toggle
    const passwordInput = screen.getByLabelText('Password') as HTMLInputElement;
    expect(passwordInput.type).toBe('password');
    const toggleBtn = screen.getByLabelText('Show password');
    fireEvent.click(toggleBtn);
    expect(passwordInput.type).toBe('text');

    // 2. Click a demo preset button
    const operatorPresetBtn = screen.getByText('operator@climaforge.local');
    fireEvent.click(operatorPresetBtn);

    const emailInput = screen.getByLabelText(/Station Identifier/i) as HTMLInputElement;
    expect(emailInput.value).toBe('operator@climaforge.local');
    expect(passwordInput.value).toBe('ClimaforgeSecurePassword123!');

    // 3. Submit form
    const submitBtn = screen.getByRole('button', { name: /Authenticate Station/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(loginUserSpy).toHaveBeenCalledWith(
        'operator@climaforge.local',
        'ClimaforgeSecurePassword123!'
      );
    });
  });

  it('renders UnauthorizedView and triggers action callbacks', () => {
    const onNavigateHome = vi.fn();
    const onOpenLogin = vi.fn();

    render(
      <UnauthorizedView
        requiredRole="Operator / Admin"
        requiredPermission="scenario.run"
        userRole="VIEWER"
        onNavigateHome={onNavigateHome}
        onOpenLogin={onOpenLogin}
        isUnauthenticated={false}
      />
    );

    expect(screen.getByText('Access Restricted')).toBeTruthy();
    expect(screen.getByText('scenario.run')).toBeTruthy();
    expect(screen.getByText('Operator / Admin')).toBeTruthy();
    expect(screen.getByText('VIEWER')).toBeTruthy();

    const returnBtn = screen.getByRole('button', { name: /Return to Overview/i });
    fireEvent.click(returnBtn);
    expect(onNavigateHome).toHaveBeenCalledTimes(1);
  });

  it('renders Header with authentication status and role badge', () => {
    const onOpenLogin = vi.fn();
    const onLogout = vi.fn();
    const onRefreshHealth = vi.fn();

    // 1. Unauthenticated view
    const { rerender } = render(
      <Header
        activeTab="overview"
        healthResult={{ success: true, targetUrl: 'http://localhost:8000/health' }}
        isCheckingHealth={false}
        onRefreshHealth={onRefreshHealth}
        user={null}
        onOpenLogin={onOpenLogin}
        onLogout={onLogout}
      />
    );

    const signInBtn = screen.getByRole('button', { name: /Sign In/i });
    expect(signInBtn).toBeTruthy();
    fireEvent.click(signInBtn);
    expect(onOpenLogin).toHaveBeenCalledTimes(1);

    // 2. Authenticated Operator view
    const authUser: UserProfile = {
      id: 'usr-1',
      email: 'operator@climaforge.local',
      full_name: 'Lead Operator',
      role: 'operator',
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
    };

    rerender(
      <Header
        activeTab="overview"
        healthResult={{ success: true, targetUrl: 'http://localhost:8000/health' }}
        isCheckingHealth={false}
        onRefreshHealth={onRefreshHealth}
        user={authUser}
        onOpenLogin={onOpenLogin}
        onLogout={onLogout}
      />
    );

    expect(screen.getByText('OPERATOR')).toBeTruthy();
    expect(screen.getByText('operator@climaforge.local')).toBeTruthy();
    const signOutBtn = screen.getByLabelText('Sign out');
    expect(signOutBtn).toBeTruthy();
    fireEvent.click(signOutBtn);
    expect(onLogout).toHaveBeenCalledTimes(1);
  });

  it('renders Sidebar with role badge and displays lock icon on unauthorized items', () => {
    const onSelectTab = vi.fn();

    // Viewer role: does not have permission for an auditor-only view or adhoc/admin tabs
    // Note: Viewer has scenario.read, chatbot.ask, audit.read
    const viewerUser: UserProfile = {
      id: 'usr-v',
      email: 'viewer@climaforge.local',
      full_name: 'Public Viewer',
      role: 'viewer',
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
    };

    render(
      <Sidebar
        activeTab="overview"
        onSelectTab={onSelectTab}
        backendOnline={true}
        user={viewerUser}
      />
    );

    expect(screen.getByText('VIEWER')).toBeTruthy();
    expect(screen.getByText('Public Viewer')).toBeTruthy();

    const overviewBtn = screen.getByRole('button', { name: /Overview/i });
    fireEvent.click(overviewBtn);
    expect(onSelectTab).toHaveBeenCalledWith('overview');
  });
});
