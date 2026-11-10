import { describe, it, expect } from 'vitest';
import {
  normalizeRole,
  getPermissionsForRole,
  userHasPermission,
  userHasAnyRole,
  type UserProfile,
} from '../types/auth';

describe('RBAC Role and Permission Verification', () => {
  it('normalizes role names case-insensitively', () => {
    expect(normalizeRole('admin')).toBe('ADMIN');
    expect(normalizeRole('OPERATOR')).toBe('OPERATOR');
    expect(normalizeRole('  analyst  ')).toBe('ANALYST');
    expect(normalizeRole('auditor')).toBe('AUDITOR');
    expect(normalizeRole('viewer')).toBe('VIEWER');
    expect(normalizeRole('unknown_role')).toBeNull();
    expect(normalizeRole(null)).toBeNull();
    expect(normalizeRole(undefined)).toBeNull();
  });

  it('matches backend canonical least-privilege role permissions', () => {
    // 1. Viewer
    const viewerPerms = getPermissionsForRole('VIEWER');
    expect(viewerPerms).toContain('scenario.read');
    expect(viewerPerms).toContain('chatbot.ask');
    expect(viewerPerms).toContain('audit.read');
    expect(viewerPerms).not.toContain('scenario.run');
    expect(viewerPerms).not.toContain('intervention.approve');
    expect(viewerPerms).not.toContain('admin.users');

    // 2. Analyst
    const analystPerms = getPermissionsForRole('ANALYST');
    expect(analystPerms).toContain('scenario.read');
    expect(analystPerms).toContain('scenario.run');
    expect(analystPerms).toContain('scenario.run_adhoc');
    expect(analystPerms).toContain('ml.predict');
    expect(analystPerms).not.toContain('intervention.approve');
    expect(analystPerms).not.toContain('admin.roles');

    // 3. Operator
    const operatorPerms = getPermissionsForRole('OPERATOR');
    expect(operatorPerms).toContain('scenario.read');
    expect(operatorPerms).toContain('scenario.run');
    expect(operatorPerms).toContain('scenario.run_adhoc');
    expect(operatorPerms).toContain('ml.predict');
    expect(operatorPerms).toContain('intervention.recommend');
    expect(operatorPerms).toContain('intervention.approve');
    expect(operatorPerms).toContain('audit.create');
    // Crucial security invariant: intervention.deploy is NEVER granted automatically
    expect(operatorPerms).not.toContain('intervention.deploy');
    expect(operatorPerms).not.toContain('admin.users');

    // 4. Auditor
    const auditorPerms = getPermissionsForRole('AUDITOR');
    expect(auditorPerms).toEqual(['audit.read']);
    expect(auditorPerms).not.toContain('scenario.read');
    expect(auditorPerms).not.toContain('scenario.run');

    // 5. Admin
    const adminPerms = getPermissionsForRole('ADMIN');
    expect(adminPerms).toContain('scenario.read');
    expect(adminPerms).toContain('scenario.run');
    expect(adminPerms).toContain('scenario.create');
    expect(adminPerms).toContain('scenario.update');
    expect(adminPerms).toContain('admin.users');
    expect(adminPerms).toContain('admin.roles');
    expect(adminPerms).toContain('admin.scenario_grants');
  });

  it('evaluates user permissions correctly', () => {
    const operatorUser: UserProfile = {
      id: 'usr-1',
      email: 'operator@climaforge.local',
      full_name: 'Test Operator',
      role: 'operator',
      is_active: true,
      created_at: new Date().toISOString(),
    };

    expect(userHasPermission(operatorUser, 'scenario.read')).toBe(true);
    expect(userHasPermission(operatorUser, 'scenario.run')).toBe(true);
    expect(userHasPermission(operatorUser, 'intervention.approve')).toBe(true);
    expect(userHasPermission(operatorUser, 'admin.users')).toBe(false);

    const viewerUser: UserProfile = {
      id: 'usr-2',
      email: 'viewer@climaforge.local',
      full_name: 'Test Viewer',
      role: 'viewer',
      is_active: true,
      created_at: new Date().toISOString(),
    };

    expect(userHasPermission(viewerUser, 'scenario.read')).toBe(true);
    expect(userHasPermission(viewerUser, 'scenario.run')).toBe(false);
    expect(userHasPermission(viewerUser, 'intervention.approve')).toBe(false);
  });

  it('rejects inactive accounts regardless of role', () => {
    const inactiveAdmin: UserProfile = {
      id: 'usr-3',
      email: 'inactive@climaforge.local',
      full_name: 'Inactive Admin',
      role: 'admin',
      is_active: false,
      created_at: new Date().toISOString(),
    };

    expect(userHasPermission(inactiveAdmin, 'scenario.read')).toBe(false);
    expect(userHasPermission(inactiveAdmin, 'admin.users')).toBe(false);
    expect(userHasAnyRole(inactiveAdmin, 'ADMIN')).toBe(false);
  });

  it('evaluates user role membership correctly', () => {
    const user: UserProfile = {
      id: 'usr-4',
      email: 'operator@climaforge.local',
      full_name: 'Test Operator',
      role: 'OPERATOR',
      is_active: true,
      created_at: new Date().toISOString(),
    };

    expect(userHasAnyRole(user, 'OPERATOR')).toBe(true);
    expect(userHasAnyRole(user, 'ADMIN', 'OPERATOR')).toBe(true);
    expect(userHasAnyRole(user, 'VIEWER')).toBe(false);
    expect(userHasAnyRole(null, 'OPERATOR')).toBe(false);
  });
});
