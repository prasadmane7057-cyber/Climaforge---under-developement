import React, { useState } from 'react';
import type { FormEvent } from 'react';
import { AlertTriangle, Bot, Send, ShieldCheck, Wifi, WifiOff } from 'lucide-react';

interface EmergencyChatbotTabProps {
  backendOnline: boolean;
}

interface ChatMessage {
  id: string;
  role: 'assistant' | 'user';
  text: string;
  source: 'LOCAL MOCK';
}

const suggestedPrompts = [
  'Explain the purpose of this assistant',
  'What information should I verify before acting?',
  'Where can I review this scenario?',
];

export const EmergencyChatbotTab: React.FC<EmergencyChatbotTabProps> = ({ backendOnline }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      text: 'This is a local advisory interface for decision support. It does not access external intelligence, issue commands, or verify conditions. Review hazard analysis, model evidence, and local instructions through authorized channels before acting.',
      source: 'LOCAL MOCK',
    },
  ]);
  const [draft, setDraft] = useState('');
  const [isSending, setIsSending] = useState(false);

  const sendMessage = (text: string) => {
    const cleanText = text.trim();
    if (!cleanText || isSending) return;

    setMessages((current) => [
      ...current,
      { id: `user-${Date.now()}`, role: 'user', text: cleanText, source: 'LOCAL MOCK' },
    ]);
    setDraft('');
    setIsSending(true);

    window.setTimeout(() => {
      setMessages((current) => [
        ...current,
        {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          source: 'LOCAL MOCK',
          text: 'This mock response does not contain verified emergency instructions or external intelligence. Use the Risk Map, Consequence Graph, Interventions, and local authoritative guidance as supporting information. Any operational action requires human verification.',
        },
      ]);
      setIsSending(false);
    }, 350);
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
            <span>Assistant response source: local mock</span>
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
            <span>No external AI service or live intelligence feed is connected.</span>
          </div>
        </aside>

        <section className="dashboard-card m8-chat-shell" aria-label="Emergency assistant conversation">
          <div className="m8-chat-header">
            <div className="m8-assistant-avatar"><Bot size={17} /></div>
            <div>
              <strong>Emergency Assistant</strong>
              <span>Local advisory mock · Not a verified external service</span>
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
                <div className="m8-message-meta"><span>Assistant</span><span className="m8-source-tag">LOCAL MOCK</span></div>
                <div className="m8-message-bubble m8-loading"><span /><span /><span /></div>
              </div>
            )}
          </div>

          <div className="m8-suggestions">
            {suggestedPrompts.map((prompt) => (
              <button key={prompt} type="button" onClick={() => sendMessage(prompt)} disabled={isSending}>
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
            />
            <button type="submit" disabled={!draft.trim() || isSending} aria-label="Send message">
              <Send size={16} />
            </button>
          </form>
        </section>
      </div>
    </div>
  );
};
