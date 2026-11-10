import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { EmergencyChatbotTab } from '../components/EmergencyChatbotTab';
import * as api from '../services/api';
import type {
  ScenarioAlertsResponse,
  ScenarioSafePointsResponse,
} from '../types/api';

describe('Nugen AI Chatbot Integration Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const mockAlerts: ScenarioAlertsResponse = {
    scenario_id: 'scenario-flash-flood',
    scenario_name: 'Flash Flood Emergency',
    generated_at: new Date().toISOString(),
    highest_severity: 'CRITICAL',
    affected_zone_count: 1,
    is_simulated: true,
    is_live_confirmed: false,
    disclaimer: 'SIMULATED / ILLUSTRATIVE ALERTS ONLY.',
    alerts: [
      {
        alert_id: 'ALERT-001',
        scenario_id: 'scenario-flash-flood',
        zone_id: 'ZONE-001',
        zone_name: 'Riverside Industrial District',
        severity: 'CRITICAL',
        risk_score: 82.6,
        dominant_cause: 'Rainfall Inundation',
        headline: 'CRITICAL EVACUATION WARNING: Severe Inundation Threat',
        description: 'Immediate pre-calamity warning for Riverside.',
        action_recommendation: 'Immediate evacuation required along safe corridors.',
        is_simulated: true,
        is_live_confirmed: false,
        disclaimer: 'SIMULATED / ILLUSTRATIVE ALERT ONLY.',
        generated_at: new Date().toISOString(),
      },
    ],
  };

  const mockSafePoints: ScenarioSafePointsResponse = {
    scenario_id: 'scenario-flash-flood',
    total_shelter_capacity: 500,
    highest_elevation_m: 22.0,
    safe_points: [
      {
        safe_point_id: 'SP-001',
        name: 'Community Center Shelter',
        zone_id: 'ZONE-001',
        capacity_persons: 500,
        elevation_m: 22.0,
        label: 'SYNTHETIC / ILLUSTRATIVE',
        is_operational: true,
        amenities: ['Emergency Shelter', 'Water'],
      },
    ],
  };

  it('renders CLIMAFORGE AI Assistant with Nugen AI badge and simulation notice', async () => {
    vi.spyOn(api, 'fetchScenarioAlerts').mockResolvedValue(mockAlerts);
    vi.spyOn(api, 'fetchScenarioSafePoints').mockResolvedValue(mockSafePoints);

    render(
      <EmergencyChatbotTab
        backendOnline={true}
        scenarioId="scenario-flash-flood"
        scenarioName="Flash Flood Emergency"
      />
    );

    expect(screen.getByText(/CLIMAFORGE AI Assistant/i)).toBeTruthy();
    expect(screen.getByText(/NUGEN AI • Qwen\/Qwen2\.5-0\.5B-Instruct/i)).toBeTruthy();
    expect(
      screen.getByText(/Non-authoritative simulated emergency guidance/i)
    ).toBeTruthy();
  });

  it('streams response tokens incrementally from Nugen AI', async () => {
    vi.spyOn(api, 'fetchScenarioAlerts').mockResolvedValue(mockAlerts);
    vi.spyOn(api, 'fetchScenarioSafePoints').mockResolvedValue(mockSafePoints);

    const streamSpy = vi.spyOn(api, 'streamChatbotMessage').mockImplementation(
      async (_scenarioId, _question, _history, callbacks) => {
        // Simulate streaming tokens
        callbacks.onToken('Evacuate ');
        callbacks.onToken('to Community Center ');
        callbacks.onToken('immediately via High Road.');
        callbacks.onDone?.({
          fullText: 'Evacuate to Community Center immediately via High Road.',
          source: 'NUGEN_AI',
        });
      }
    );

    render(
      <EmergencyChatbotTab
        backendOnline={true}
        scenarioId="scenario-flash-flood"
        scenarioName="Flash Flood Emergency"
      />
    );

    const input = screen.getByPlaceholderText(/Ask a grounded scenario question\.\.\./i);
    const sendButton = screen.getByTitle(/Send grounded question/i);

    fireEvent.change(input, { target: { value: 'Where should I evacuate?' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(streamSpy).toHaveBeenCalledTimes(1);
    });

    await waitFor(() => {
      expect(
        screen.getByText(/Evacuate to Community Center immediately via High Road\./i)
      ).toBeTruthy();
    });
  });

  it('allows clearing conversation and resets to initial welcome message', async () => {
    vi.spyOn(api, 'fetchScenarioAlerts').mockResolvedValue(mockAlerts);
    vi.spyOn(api, 'fetchScenarioSafePoints').mockResolvedValue(mockSafePoints);

    render(
      <EmergencyChatbotTab
        backendOnline={true}
        scenarioId="scenario-flash-flood"
        scenarioName="Flash Flood Emergency"
      />
    );

    const clearButton = screen.getByRole('button', { name: /Clear Conversation/i });
    expect(clearButton).toBeTruthy();

    fireEvent.click(clearButton);

    expect(
      screen.getByText(/CLIMAFORGE AI, your climate-risk and disaster-management assistant powered by Nugen AI/i)
    ).toBeTruthy();
  });

  it('displays error message and retry button when streaming and fallback fail', async () => {
    vi.spyOn(api, 'fetchScenarioAlerts').mockResolvedValue(mockAlerts);
    vi.spyOn(api, 'fetchScenarioSafePoints').mockResolvedValue(mockSafePoints);

    vi.spyOn(api, 'streamChatbotMessage').mockImplementation(
      async (_scenarioId, _question, _history, callbacks) => {
        callbacks.onError?.(new Error('Nugen AI service connection timed out'));
      }
    );

    vi.spyOn(api, 'askGroundedChatbot').mockRejectedValue(
      new Error('Backend fallback also unavailable')
    );

    render(
      <EmergencyChatbotTab
        backendOnline={true}
        scenarioId="scenario-flash-flood"
        scenarioName="Flash Flood Emergency"
      />
    );

    const input = screen.getByPlaceholderText(/Ask a grounded scenario question\.\.\./i);
    const sendButton = screen.getByTitle(/Send grounded question/i);

    fireEvent.change(input, { target: { value: 'Is the bridge safe?' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(screen.getByText(/Backend fallback also unavailable/i)).toBeTruthy();
    });

    const retryButton = screen.getByRole('button', { name: /Retry Question/i });
    expect(retryButton).toBeTruthy();
  });
});
