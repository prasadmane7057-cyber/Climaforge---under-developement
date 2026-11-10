/**
 * Unauthorized / Access Restricted placeholder component.
 * Rendered when the current user's role lacks permissions for the selected view.
 */

import React from 'react';
import { ShieldAlert, ArrowLeft, LogIn } from 'lucide-react';
import type { RoleName } from '../types/auth';

interface UnauthorizedViewProps {
  requiredRole?: string;
  requiredPermission?: string;
  userRole?: string | null;
  onNavigateHome: () => void;
  onOpenLogin?: () => void;
  isUnauthenticated?: boolean;
}

export const UnauthorizedView: React.FC<UnauthorizedViewProps> = ({
  requiredRole,
  requiredPermission,
  userRole,
  onNavigateHome,
  onOpenLogin,
  isUnauthenticated,
}) => {
  return (
    <div className="unauthorized-container" role="alert" aria-live="assertive">
      <div className="unauthorized-card">
        <div className="unauthorized-icon-badge">
          <ShieldAlert size={36} className="unauthorized-icon" />
        </div>

        <h2 className="unauthorized-title">Access Restricted</h2>

        <p className="unauthorized-description">
          {isUnauthenticated
            ? 'This operational module requires an authenticated station session with verified role permissions.'
            : 'Your active account role lacks authorization to access this operational module.'}
        </p>

        <div className="unauthorized-details">
          {requiredRole && (
            <div className="unauthorized-detail-row">
              <span className="detail-label">Required Role:</span>
              <span className="detail-badge role-required">{requiredRole}</span>
            </div>
          )}
          {requiredPermission && (
            <div className="unauthorized-detail-row">
              <span className="detail-label">Required Permission:</span>
              <code className="detail-code">{requiredPermission}</code>
            </div>
          )}
          <div className="unauthorized-detail-row">
            <span className="detail-label">Current Role:</span>
            <span className="detail-badge role-current">
              {(userRole as RoleName) || (isUnauthenticated ? 'Unauthenticated (Viewer/Public)' : 'None')}
            </span>
          </div>
        </div>

        <div className="unauthorized-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onNavigateHome}
          >
            <ArrowLeft size={14} />
            <span>Return to Overview</span>
          </button>

          {isUnauthenticated && onOpenLogin && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={onOpenLogin}
            >
              <LogIn size={14} />
              <span>Authenticate Station</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

