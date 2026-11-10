/**
 * Station Login Modal for CLIMAFORGE M16A.6.
 *
 * Implements:
 * - Direct authentication against POST /api/auth/login.
 * - Display of specific authentication, authorization, or rate-limit error messages.
 * - In-memory access token storage (no tokens or passwords logged or written to storage).
 * - Fast-fill presets for demonstration testing.
 */

import React, { useState } from 'react';
import { Lock, Mail, Eye, EyeOff, AlertCircle, X, Shield, Loader2 } from 'lucide-react';
import { useAuth } from '../context/useAuth';

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const LoginModal: React.FC<LoginModalProps> = ({ isOpen, onClose }) => {
  const { login, error, clearError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleClose = () => {
    setPassword('');
    setValidationError(null);
    clearError();
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setValidationError('Please enter your account email address.');
      return;
    }
    if (!password) {
      setValidationError('Please enter your station password.');
      return;
    }

    setIsSubmitting(true);
    try {
      await login(trimmedEmail, password);
      // login success closes modal via AuthContext
    } catch {
      // Error message is set in AuthContext state
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSelectDemoAccount = (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword('ClimaforgeSecurePassword123!');
    setValidationError(null);
    clearError();
  };

  return (
    <div
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="login-modal-title"
    >
      <div className="modal-backdrop" onClick={handleClose} />
      <div className="modal-card">
        {/* Header */}
        <div className="modal-header">
          <div className="modal-brand-badge">
            <Shield size={18} className="modal-brand-icon" />
            <span className="modal-brand-text">CLIMAFORGE AUTHENTICATION</span>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={handleClose}
            aria-label="Close authentication dialog"
          >
            <X size={16} />
          </button>
        </div>

        <div className="modal-body">
          <h2 id="login-modal-title" className="modal-title">
            Sign In to Operational Station
          </h2>
          <p className="modal-subtitle">
            Enter authorized credentials to activate role-based simulation, analysis execution, and intervention commands.
          </p>

          {/* Validation or API Error Alert */}
          {(validationError || error) && (
            <div className="modal-error-alert" role="alert">
              <AlertCircle size={16} className="modal-error-icon" />
              <span className="modal-error-text">{validationError || error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="login-form">
            {/* Email Field */}
            <div className="form-group">
              <label htmlFor="auth-email" className="form-label">
                Station Identifier / Email
              </label>
              <div className="input-with-icon">
                <Mail size={16} className="input-icon" />
                <input
                  id="auth-email"
                  type="email"
                  className="form-input"
                  placeholder="operator@climaforge.local"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isSubmitting}
                  autoComplete="username"
                  required
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="form-group">
              <label htmlFor="auth-password" className="form-label">
                Password
              </label>
              <div className="input-with-icon">
                <Lock size={16} className="input-icon" />
                <input
                  id="auth-password"
                  type={showPassword ? 'text' : 'password'}
                  className="form-input"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isSubmitting}
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  className="input-action-btn"
                  onClick={() => setShowPassword((prev) => !prev)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              className="btn btn-primary btn-block modal-submit-btn"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={16} className="spin-animation" />
                  <span>Verifying Credentials...</span>
                </>
              ) : (
                <>
                  <Lock size={16} />
                  <span>Authenticate Station</span>
                </>
              )}
            </button>
          </form>

          {/* Demonstration Quick-Select */}
          <div className="demo-accounts-section">
            <span className="demo-section-label">DEMONSTRATION PRESETS</span>
            <div className="demo-presets-grid">
              <button
                type="button"
                className="demo-preset-btn"
                onClick={() => handleSelectDemoAccount('admin@climaforge.local')}
              >
                <span className="preset-role role-admin">ADMIN</span>
                <span className="preset-email">admin@climaforge.local</span>
              </button>
              <button
                type="button"
                className="demo-preset-btn"
                onClick={() => handleSelectDemoAccount('operator@climaforge.local')}
              >
                <span className="preset-role role-operator">OPERATOR</span>
                <span className="preset-email">operator@climaforge.local</span>
              </button>
              <button
                type="button"
                className="demo-preset-btn"
                onClick={() => handleSelectDemoAccount('viewer@climaforge.local')}
              >
                <span className="preset-role role-viewer">VIEWER</span>
                <span className="preset-email">viewer@climaforge.local</span>
              </button>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <span className="modal-security-notice">
            Session tokens secured via in-memory storage and HttpOnly refresh cookies.
          </span>
        </div>
      </div>
    </div>
  );
};
