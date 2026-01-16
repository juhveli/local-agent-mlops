import React, { useState } from 'react';
import { Send, User, Bot, Paperclip, Settings, Globe } from 'lucide-react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

const ChatInterface = () => {
    const [messages, setMessages] = useState([
        { id: 1, role: 'assistant', content: 'Hello! I can help you query the NornicDB knowledge graph. What would you like to know?' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);

    // Search Settings
    const [showSettings, setShowSettings] = useState(false);
    const [useWebSearch, setUseWebSearch] = useState(false);
    const [provider, setProvider] = useState('tavily');
    const [searchDepth, setSearchDepth] = useState('basic');
    const [highAuthorityOnly, setHighAuthorityOnly] = useState(false);

    const handleSend = async (e) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMsg = { id: Date.now(), role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput('');

        if (useWebSearch) {
             setLoading(true);
             const assistantMsgId = Date.now() + 1;
             setMessages(prev => [...prev, { id: assistantMsgId, role: 'assistant', content: 'Searching web...' }]);

             try {
                const payload = {
                    query: userMsg.content,
                    max_iterations: 1, // Keep it fast for chat
                    provider,
                    search_depth: searchDepth,
                    include_domains: highAuthorityOnly ? ["HIGH_AUTHORITY"] : []
                };
                const response = await axios.post('/api/research', payload);
                const answer = response.data.answer;
                const sources = response.data.sources;

                const formattedContent = (
                    <div>
                        <ReactMarkdown>{answer}</ReactMarkdown>
                        {sources && sources.length > 0 && (
                             <div style={{ marginTop: '1rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                <div style={{ fontWeight: 600, marginBottom: '0.5rem' }}>Sources:</div>
                                <ul style={{ paddingLeft: '1.2rem', margin: 0 }}>
                                    {sources.slice(0, 3).map(s => (
                                        <li key={s.id}>
                                            <a href={s.url} target="_blank" rel="noopener noreferrer" style={{ color: 'inherit' }}>{s.title}</a>
                                        </li>
                                    ))}
                                </ul>
                             </div>
                        )}
                    </div>
                );

                setMessages(prev => prev.map(msg =>
                    msg.id === assistantMsgId ? { ...msg, content: formattedContent } : msg
                ));

             } catch (error) {
                 console.error(error);
                 setMessages(prev => prev.map(msg =>
                    msg.id === assistantMsgId ? { ...msg, content: 'Sorry, I encountered an error while searching.' } : msg
                ));
             } finally {
                 setLoading(false);
             }
        } else {
            // Simulate response for now (GraphRAG placeholder)
            setTimeout(() => {
                setMessages(prev => [...prev, {
                    id: Date.now() + 1,
                    role: 'assistant',
                    content: 'GraphRAG chat capability is coming in Phase 4. Enable "Web Search" to search the web instead!'
                }]);
            }, 1000);
        }
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

            {/* Settings Area */}
            {showSettings && (
                <div style={{ padding: '1rem', background: 'var(--bg-secondary)', marginBottom: '1rem', borderRadius: '8px', fontSize: '0.9rem' }}>
                     <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
                        <div>
                            <label style={{ display: 'block', marginBottom: '0.3rem', color: 'var(--text-secondary)' }}>Provider</label>
                            <select className="input" value={provider} onChange={(e) => setProvider(e.target.value)} style={{ width: '100%', padding: '0.4rem' }}>
                                <option value="tavily">Tavily</option>
                                <option value="duckduckgo">DuckDuckGo</option>
                            </select>
                        </div>
                        <div>
                            <label style={{ display: 'block', marginBottom: '0.3rem', color: 'var(--text-secondary)' }}>Depth</label>
                            <select className="input" value={searchDepth} onChange={(e) => setSearchDepth(e.target.value)} disabled={provider === 'duckduckgo'} style={{ width: '100%', padding: '0.4rem' }}>
                                <option value="basic">Basic</option>
                                <option value="advanced">Advanced</option>
                            </select>
                        </div>
                     </div>
                     <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                        <input type="checkbox" checked={highAuthorityOnly} onChange={(e) => setHighAuthorityOnly(e.target.checked)} />
                        <span>High Authority Sources Only</span>
                    </label>
                </div>
            )}

            {/* Input Area */}
            <form onSubmit={handleSend} className="card" style={{ padding: '0.75rem', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                <button
                    type="button"
                    onClick={() => setShowSettings(!showSettings)}
                    style={{ background: showSettings ? 'var(--bg-secondary)' : 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: '0.3rem', borderRadius: '4px' }}
                >
                    <Settings size={20} />
                </button>
                <button
                    type="button"
                    onClick={() => setUseWebSearch(!useWebSearch)}
                    style={{ background: useWebSearch ? 'var(--accent)' : 'none', border: 'none', color: useWebSearch ? 'white' : 'var(--text-secondary)', cursor: 'pointer', padding: '0.3rem', borderRadius: '4px' }}
                    title={useWebSearch ? "Web Search Enabled" : "Enable Web Search"}
                >
                    <Globe size={20} />
                </button>
                <input
                    type="text"
                    className="input"
                    style={{ border: 'none', background: 'transparent', padding: '0.5rem' }}
                    placeholder={useWebSearch ? "Search the web..." : "Ask a question..."}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    disabled={loading}
                />
                <button type="submit" className="btn" disabled={!input.trim() || loading} style={{ padding: '0.5rem 1rem' }}>
                    <Send size={18} />
                </button>
            </form>
        </div>
    );
};

export default ChatInterface;
