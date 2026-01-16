import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, Trash2, Loader2 } from 'lucide-react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

const ChatInterface = () => {
    const [messages, setMessages] = useState([
        { id: 1, role: 'assistant', content: 'Hello! I can help you query the knowledge base. Ask me anything about topics you\'ve researched!' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async (e) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMsg = { id: Date.now(), role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            const response = await axios.post('/api/chat', { message: input });
            setMessages(prev => [...prev, {
                id: Date.now() + 1,
                role: 'assistant',
                content: response.data.message,
                sourcesUsed: response.data.sources_used
            }]);
        } catch (error) {
            console.error('Chat error:', error);
            setMessages(prev => [...prev, {
                id: Date.now() + 1,
                role: 'assistant',
                content: 'Sorry, I encountered an error. Please try again.'
            }]);
        } finally {
            setLoading(false);
        }
    };

    const handleClear = async () => {
        try {
            await axios.post('/api/chat/clear');
            setMessages([
                { id: Date.now(), role: 'assistant', content: 'Chat history cleared. How can I help you?' }
            ]);
        } catch (error) {
            console.error('Clear error:', error);
        }
    };

    return (
        <div style={{ maxWidth: '900px', margin: '0 auto', height: 'calc(100vh - 4rem)', display: 'flex', flexDirection: 'column' }}>
            <header style={{ marginBottom: '1rem', borderBottom: '1px solid var(--border)', paddingBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h2 style={{ fontSize: '1.5rem', margin: 0 }}>Graph Chat</h2>
                    <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '0.9rem' }}>
                        Interactive RAG over your knowledge base
                    </p>
                </div>
                <button
                    onClick={handleClear}
                    style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '8px', padding: '0.5rem 1rem', color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                >
                    <Trash2 size={16} /> Clear
                </button>
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
                            {msg.role === 'assistant' ? (
                                <ReactMarkdown>{msg.content}</ReactMarkdown>
                            ) : (
                                msg.content
                            )}
                            {msg.sourcesUsed > 0 && (
                                <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                    📚 {msg.sourcesUsed} sources used
                                </div>
                            )}
                        </div>
                    </div>
                ))}
                {loading && (
                    <div style={{ display: 'flex', gap: '1rem', alignSelf: 'flex-start' }}>
                        <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'var(--bg-secondary)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <Bot size={16} />
                        </div>
                        <div className="card" style={{ padding: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} />
                            Thinking...
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <form onSubmit={handleSend} className="card" style={{ padding: '0.75rem', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                <input
                    type="text"
                    className="input"
                    style={{ border: 'none', background: 'transparent', padding: '0.5rem', flex: 1 }}
                    placeholder="Ask a question about your knowledge base..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    disabled={loading}
                />
                <button type="submit" className="btn" disabled={!input.trim() || loading} style={{ padding: '0.5rem 1rem' }}>
                    <Send size={18} />
                </button>
            </form>

            <style>{`
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
      `}</style>
        </div>
    );
};

export default ChatInterface;
