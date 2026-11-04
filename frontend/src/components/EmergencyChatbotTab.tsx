import React, { useState } from 'react';
import type { FormEvent } from 'react';
import { AlertTriangle, Bot, Send, ShieldCheck, Wifi, WifiOff } from 'lucide-react';
import { askGroundedChatbot } from '../services/api';
import type { ChatHistoryItem } from '../types/api';

interface EmergencyChatbotTabProps {
  backendOnline: boolean;
  scenarioId: string;
  scenarioName?: string;
}

interface ChatMessage {
  id: string;
  role: 'assistant' | 'user';
  text: string;
  source: 'DETERMINISTIC_FALLBACK' | 'LLM' | 'SYSTEM';
}

const suggestedPrompts = [
  'Explain the current risk assessment in simple language',
  'Which locations are most affected?',
  'What are the main consequences identified by the engine?',
  'Why is this intervention recommended?',
  'What happens if available resources are reduced?',
  'What information is missing from this assessment?',
];

export const EmergencyChatbotTab: React.FC<EmergencyChatbotTabProps> = ({
  backendOnline,
  scenarioId,
  scenarioName,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      text: 'This grounded assistant answers from the selected CLIMAFORGE scenario and deterministic engine outputs. It does not confirm floods, verify live conditions, or record deployments.',
      source: 'SYSTEM',
    },
  ]);
  const [draft, setDraft] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentMode, setCurrentMode] = useState<'grounded_llm' | 'deterministic_fallback' | null>(null);

  const sendMessage = async (text: string) => {
    const cleanText = text.trim();
    if (!cleanText || isSending || !backendOnline) return;

    setMessages((current) => [
      ...current,
      { id: `user-${Date.now()}`, role: 'user', text: cleanText, source: 'SYSTEM' },
    ]);
    setDraft('');
    setIsSending(true);
    setError(null);

    const history: ChatHistoryItem[] = messages
      .filter((message) => message.role === 'user' || message.role === 'assistant')
      .filter((message) => message.id !== 'welcome')
      .map((message) => ({ role: message.role, content: message.text }));

    try {
      const response = await askGroundedChatbot(scenarioId, cleanText, history);
      setMessages((current) => [
        ...current,
        {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          source: response.source,
          text: response.answer,
        },
      ]);
      setCurrentMode(response.mode);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'The assistant request failed.';
      setError(message);
      setMessages((current) => [
        ...current,
        {
          id: `assistant-error-${Date.now()}`,
          role: 'assistant',
          source: 'DETERMINISTIC_FALLBACK',
          text: 'The grounded assistant request could not be completed. Backend context is unavailable for this response; no system values were inferred.',
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    sendMessage(draft);
  };

  return (
    <div className="tab-pane m8-chat-pane">
      <div className="m8-page-heading">
        <div>
          <span className="m8-kicker">Emergency decision support</span>
          <h2>Emergency Assistant</h2>
          <p>Structured guidance for reviewing hazard information. This interface is advisory and not an autonomous command system.</p>
        </div>
        <div className={`m8-service-status ${backendOnline ? 'online' : 'offline'}`}>
          {backendOnline ? <Wifi size={15} /> : <WifiOff size={15} />}
          <div>
            <strong>Backend {backendOnline ? 'connected' : 'disconnected'}</strong>
            <span>Scenario: {scenarioName || scenarioId}</span>
          </div>
        </div>
      </div>

      <div className="m8-safety-banner">
        <ShieldCheck size={18} />
        <div>
          <strong>Human verification required</strong>
          <span>Important recommendations require authorization and verification through established emergency procedures.</span>
        </div>
      </div>

      <div className="m8-chat-layout">
        <aside className="dashboard-card m8-chat-context">
          <div className="m8-card-header">
            <span className="m8-panel-label">Conversation context</span>
            <h3>Supported workflow</h3>
          </div>
          <div className="m8-context-list">
            <div><span>01</span><strong>Review scenario evidence</strong></div>
            <div><span>02</span><strong>Inspect risk and dependencies</strong></div>
            <div><span>03</span><strong>Verify intervention evidence</strong></div>
            <div><span>04</span><strong>Escalate for human decision</strong></div>
          </div>
          <div className="m8-advisory-note">
            <AlertTriangle size={16} />
            <span>{currentMode === 'grounded_llm' ? 'Grounded LLM mode is configured.' : 'Deterministic fallback is used unless a supported backend LLM is configured.'}</span>
          </div>
        </aside>

        <section className="dashboard-card m8-chat-shell" aria-label="Emergency assistant conversation">
          <div className="m8-chat-header">
            <div className="m8-assistant-avatar"><Bot size={17} /></div>
            <div>
              <strong>Emergency Assistant</strong>
              <span>{scenarioName || scenarioId} · Read-only context grounding</span>
            </div>
            <span className="m8-count-pill">{messages.length} message{messages.length === 1 ? '' : 's'}</span>
          </div>

          <div className="m8-message-list" aria-live="polite">
            {messages.length === 0 ? (
              <div className="m8-empty-chat">
                <Bot size={24} />
                <strong>No conversation yet</strong>
                <span>Choose a suggested prompt or enter a question.</span>
              </div>
            ) : messages.map((message) => (
              <div key={message.id} className={`m8-message-row ${message.role}`}>
                <div className="m8-message-meta">
                  <span>{message.role === 'assistant' ? 'Assistant' : 'Operator'}</span>
                  <span className="m8-source-tag">{message.source}</span>
                </div>
                <div className="m8-message-bubble">{message.text}</div>
              </div>
            ))}
            {isSending && (
              <div className="m8-message-row assistant">
                <div className="m8-message-meta"><span>Assistant</span><span className="m8-source-tag">PROCESSING</span></div>
                <div className="m8-message-bubble m8-loading"><span /><span /><span /></div>
              </div>
            )}
            {error && (
              <div className="m8-advisory-note" role="alert">
                <AlertTriangle size={16} />
                <span>{error}</span>
              </div>
            )}
          </div>

          <div className="m8-suggestions">
            {suggestedPrompts.map((prompt) => (
              <button key={prompt} type="button" onClick={() => sendMessage(prompt)} disabled={isSending || !backendOnline}>
                {prompt}
              </button>
            ))}
          </div>

          <form className="m8-chat-form" onSubmit={handleSubmit}>
            <input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Enter a decision-support question..."
              aria-label="Emergency assistant message"
              disabled={!backendOnline || isSending}
            />
            <button type="submit" disabled={!draft.trim() || isSending || !backendOnline} aria-label="Send message">
              <Send size={16} />
            </button>
          </form>
        </section>
      </div>
    </div>
  );
};
