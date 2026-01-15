import React, { useState } from 'react';
import { Send, User, Bot, Paperclip } from 'lucide-react';

const ChatInterface = () => {
    const [messages, setMessages] = useState([
        { id: 1, role: 'assistant', content: 'Hello! I can help you query the NornicDB knowledge graph. What would you like to know?' }
    ]);
    const [input, setInput] = useState('');

    const handleSend = (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMsg = { id: Date.now(), role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput('');

        // Simulate response for now (GraphRAG placeholder)
        setTimeout(() => {
            setMessages(prev => [...prev, {
                id: Date.now() + 1,
                role: 'assistant',
                content: 'GraphRAG chat capability is coming in Phase 4. For now, try the Deep Research tab!'
            }]);
        }, 1000);
    };

    return (
        <div style={{ maxWidth: '900px', margin: '0 auto', height: 'calc(100vh - 4rem)', display: 'flex', flexDirection: 'column' }}>
            <header style={{ marginBottom: '1rem', borderBottom: '1px solid var(--border)', paddingBottom: '1rem' }}>
                <h2 style={{ fontSize: '1.5rem', margin: 0 }}>Graph Chat</h2>
                <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '0.9rem' }}>
                    Interactive RAG over your knowledge base
                </p>
            </header>

            {/* Messages Area */}
            <div style={{
                flex: 1,
                overflowY: 'auto',
                display: 'flex',
                flexDirection: 'column',
                gap: '1.5rem',
                paddingRight: '1rem',
                marginBottom: '1rem'
            }}>
                {messages.map((msg) => (
                    <div
                        key={msg.id}
                        style={{
                            display: 'flex',
                            gap: '1rem',
                            alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                            maxWidth: '80%',
                            flexDirection: msg.role === 'user' ? 'row-reverse' : 'row'
                        }}
                    >
                        <div style={{
                            width: '32px', height: '32px',
                            borderRadius: '50%',
                            background: msg.role === 'user' ? 'var(--accent)' : 'var(--bg-secondary)',
                            border: '1px solid var(--border)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            flexShrink: 0
                        }}>
                            {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                        </div>

                        <div style={{
                            background: msg.role === 'user' ? 'var(--accent)' : 'var(--bg-secondary)',
                            padding: '1rem',
                            borderRadius: '12px',
                            borderTopRightRadius: msg.role === 'user' ? '2px' : '12px',
                            borderTopLeftRadius: msg.role === 'assistant' ? '2px' : '12px',
                            border: msg.role === 'assistant' ? '1px solid var(--border)' : 'none'
                        }}>
                            {msg.content}
                        </div>
                    </div>
                ))}
            </div>

            {/* Input Area */}
            <form onSubmit={handleSend} className="card" style={{ padding: '0.75rem', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                <button type="button" style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                    <Paperclip size={20} />
                </button>
                <input
                    type="text"
                    className="input"
                    style={{ border: 'none', background: 'transparent', padding: '0.5rem' }}
                    placeholder="Ask a question..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                />
                <button type="submit" className="btn" disabled={!input.trim()} style={{ padding: '0.5rem 1rem' }}>
                    <Send size={18} />
                </button>
            </form>
        </div>
    );
};

export default ChatInterface;
