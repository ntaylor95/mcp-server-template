import { useState, useRef, useEffect, type KeyboardEvent } from 'react';
import { askQuestion } from './api';
import './App.css';

interface Message {
  id: number;
  role: 'user' | 'assistant' | 'error';
  content: string;
  source?: { name: string; url: string };
}

let nextId = 1;

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Auto-resize textarea as user types
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  }, [input]);

  const canSend = input.trim().length > 0 && !loading;

  async function send() {
    if (!canSend) return;
    const question = input.trim();
    setInput('');

    setMessages(prev => [...prev, { id: nextId++, role: 'user', content: question }]);
    setLoading(true);

    try {
      const res = await askQuestion(question);
      setMessages(prev => [
        ...prev,
        {
          id: nextId++,
          role: 'assistant',
          content: res.answer,
          source: res.source ?? undefined,
        },
      ]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          id: nextId++,
          role: 'error',
          content: err instanceof Error ? err.message : 'Something went wrong.',
        },
      ]);
    } finally {
      setLoading(false);
      textareaRef.current?.focus();
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Tricentis Policy Assistant</h1>
        <p>Ask questions about Tricentis company policies</p>
      </header>

      {messages.length === 0 && !loading ? (
        <div className="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <p>Ask anything about Tricentis company policies.</p>
          <p className="hint">Answers are grounded in the original policy documents.</p>
        </div>
      ) : (
        <div className="messages">
          {messages.map(msg => (
            <div key={msg.id} className={`message ${msg.role}`}>
              <div className="bubble">{msg.content}</div>
              {msg.source && (
                <div className="source">
                  Source:{' '}
                  <a href={msg.source.url} target="_blank" rel="noreferrer">
                    {msg.source.name}
                  </a>
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="message assistant">
              <div className="typing">
                <span /><span /><span />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      )}

      <div className="input-area">
        <textarea
          ref={textareaRef}
          rows={1}
          placeholder="Ask a policy question… (Enter to send, Shift+Enter for newline)"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={loading}
        />
        <button className="send-btn" onClick={send} disabled={!canSend}>
          Send
        </button>
      </div>
    </div>
  );
}
