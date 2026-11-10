/**
 * Authentication and RBAC type contracts for CLIMAFORGE M16A.6.
 */

export type RoleName = 'ADMIN' | 'OPERATOR' | 'ANALYST' | 'AUDITOR' | 'VIEWER';

export type PermissionName =
  | 'scenario.read'
  | 'scenario.run'
  | 'scenario.create'
  | 'scenario.update'
  | 'scenario.run_adhoc'
  | 'chatbot.ask'
  | 'ml.predict'
  | 'audit.read'
  | 'audit.create'
  | 'intervention.recommend'
  | 'intervention.approve'
  | 'intervention.deploy'
  | 'admin.users'
  | 'admin.roles'
  | 'admin.scenario_grants';

export interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  created_at: string;
}

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated' | 'session-expired';

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginErrorResponse {
  detail: string;
}

/**
 * Server-controlled default role to permissions mapping.
 * Aligns with backend `DEFAULT_ROLE_PERMISSIONS` in `backend/app/security/rbac.py`.
 */
export const DEFAULT_ROLE_PERMISSIONS: Record<RoleName, readonly PermissionName[]> = {
  VIEWER: ['scenario.read', 'chatbot.ask', 'audit.read'],
  ANALYST: [
    'scenario.read',
    'chatbot.ask',
    'audit.read',
    'scenario.run',
    'scenario.run_adhoc',
    'ml.predict',
  ],
  OPERATOR: [
    'scenario.read',
    'chatbot.ask',
    'audit.read',
    'scenario.run',
    'scenario.run_adhoc',
    'ml.predict',
    'intervention.recommend',
    'intervention.approve',
    'audit.create',
  ],
  AUDITOR: ['audit.read'],
  ADMIN: [
    'scenario.read',
    'scenario.run',
    'scenario.create',
    'scenario.update',
    'scenario.run_adhoc',
    'chatbot.ask',
    'ml.predict',
    'audit.read',
    'audit.create',
    'intervention.recommend',
    'intervention.approve',
    'admin.users',
    'admin.roles',
    'admin.scenario_grants',
  ],
} as const;

/**
 * Normalizes role string to canonical uppercase RoleName.
 */
export function normalizeRole(role: string | null | undefined): RoleName | null {
  if (!role) return null;
  const upper = role.trim().toUpperCase();
  if (upper in DEFAULT_ROLE_PERMISSIONS) {
    return upper as RoleName;
  }
  return null;
}

/**
 * Resolves permissions for a given role based on least-privilege defaults.
 */
export function getPermissionsForRole(role: string | null | undefined): PermissionName[] {
  const norm = normalizeRole(role);
  if (!norm) return [];
  return [...DEFAULT_ROLE_PERMISSIONS[norm]];
}

/**
 * Checks if a user has a specific permission.
 */
export function userHasPermission(user: UserProfile | null, permission: PermissionName): boolean {
  if (!user || !user.is_active) return false;
  const perms = getPermissionsForRole(user.role);
  return perms.includes(permission);
}

/**
 * Checks if a user possesses any of the specified roles.
 */
export function userHasAnyRole(user: UserProfile | null, ...roles: string[]): boolean {
  if (!user || !user.is_active) return false;
  const userRole = normalizeRole(user.role);
  if (!userRole) return false;
  const targetRoles = roles.map((r) => r.trim().toUpperCase());
  return targetRoles.includes(userRole);
}

