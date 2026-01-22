import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, Paperclip, Settings, Globe, Trash2, Loader2 } from 'lucide-react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { useToast } from '../context/ToastContext';

const MessageItem = React.memo(({ msg }) => (
    <div
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
                typeof msg.content === 'string' ? <ReactMarkdown>{msg.content}</ReactMarkdown> : msg.content
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
));

const ChatInterface = () => {
    const { toast } = useToast();
    const [messages, setMessages] = useState([
        { id: 1, role: 'assistant', content: 'Hello! I can help you query the knowledge base. Ask me anything about topics you\'ve researched!' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [isDragging, setIsDragging] = useState(false);
    const fileInputRef = useRef(null);

    // Search Settings
    const [showSettings, setShowSettings] = useState(false);
    const [useWebSearch, setUseWebSearch] = useState(false);
    const [provider, setProvider] = useState('tavily');
    const [searchDepth, setSearchDepth] = useState('basic');
    const [highAuthorityOnly, setHighAuthorityOnly] = useState(false);

    const suggestions = [
        "Summarize my documents",
        "What are the key entities?",
        "Explain the connections found"
    ];

    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const processFile = async (file) => {
        if (!file) return;

        if (file.type !== 'application/pdf') {
            toast.error('Please upload a PDF file.', 'Invalid File Type');
            return;
        }

        if (file.size > 2.5 * 1024 * 1024) {
            toast.error('File size exceeds 2.5MB limit.', 'File Too Large');
            return;
        }

        setUploading(true);
        const formData = new FormData();
        formData.append('file', file);

        try {
            const assistantMsgId = Date.now();
            setMessages(prev => [...prev, {
                id: assistantMsgId,
                role: 'assistant',
                content: `📄 Ingesting **${file.name}**... (This may take a moment using Vision LLM)`
            }]);

            const response = await axios.post('/api/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            setMessages(prev => prev.map(msg =>
                msg.id === assistantMsgId
                ? { ...msg, content: `✅ Successfully ingested **${file.name}**.\n\nExtracted ${response.data.chunks} chunks.` }
                : msg
            ));
        } catch (error) {
            console.error('Upload error:', error);
            // Remove the temporary message if failed, or update it
             setMessages(prev => prev.filter(msg => msg.id !== Date.now())); // Simple cleanup, ideally update to error state
             toast.error('Error uploading file: ' + (error.response?.data?.detail || error.message), 'Upload Failed');
        } finally {
            setUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    const handleFileChange = (e) => {
        processFile(e.target.files[0]);
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = (e) => {
        e.preventDefault();
        setIsDragging(false);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files[0];
        processFile(file);
    };

    const handleSend = async (e) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMsg = { id: Date.now(), role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

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
                 toast.error('Web search failed. Please try again.', 'Error');
                 setMessages(prev => prev.map(msg =>
                    msg.id === assistantMsgId ? { ...msg, content: 'Sorry, I encountered an error while searching.' } : msg
                ));
             } finally {
                 setLoading(false);
             }
        } else {
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
                toast.error('Chat failed. Please check backend connection.', 'Error');
                setMessages(prev => [...prev, {
                    id: Date.now() + 1,
                    role: 'assistant',
                    content: 'Sorry, I encountered an error. Please try again.'
                }]);
            } finally {
                setLoading(false);
            }
        }
    };

    const handleClear = async () => {
        try {
            await axios.post('/api/chat/clear');
            setMessages([
                { id: Date.now(), role: 'assistant', content: 'Chat history cleared. How can I help you?' }
            ]);
            toast.success('Chat history cleared.', 'Success');
        } catch (error) {
            console.error('Clear error:', error);
            toast.error('Failed to clear chat history.', 'Error');
        }
    };

    return (
        <div
            style={{ maxWidth: '900px', margin: '0 auto', height: 'calc(100vh - 4rem)', display: 'flex', flexDirection: 'column', position: 'relative' }}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
        >
            {isDragging && (
                <div style={{
                    position: 'absolute', inset: 0, background: 'rgba(59, 130, 246, 0.1)',
                    border: '2px dashed var(--accent)', zIndex: 50, borderRadius: '12px',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none',
                    backdropFilter: 'blur(2px)'
                }}>
                    <div style={{ background: 'var(--bg-secondary)', padding: '1.5rem 2.5rem', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', textAlign: 'center' }}>
                        <Paperclip size={48} style={{ display: 'block', margin: '0 auto 1rem', color: 'var(--accent)' }} />
                        <p style={{ margin: 0, fontWeight: 600, fontSize: '1.2rem' }}>Drop PDF to Upload</p>
                    </div>
                </div>
            )}

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
                    <MessageItem key={msg.id} msg={msg} />
                ))}
                {messages.length === 1 && (
                    <div style={{ padding: '0 1rem', marginTop: '1rem' }}>
                        <p style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Quick actions:</p>
                        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                            {suggestions.map(s => (
                                <button
                                    key={s}
                                    onClick={() => setInput(s)}
                                    style={{
                                        background: 'var(--bg-secondary)',
                                        border: '1px solid var(--border)',
                                        padding: '0.5rem 1rem',
                                        borderRadius: '20px',
                                        color: 'var(--text-primary)',
                                        cursor: 'pointer',
                                        fontSize: '0.9rem'
                                    }}
                                >
                                    {s}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
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
                <input
                    type="file"
                    ref={fileInputRef}
                    style={{ display: 'none' }}
                    accept="application/pdf"
                    onChange={handleFileChange}
                />
                <button
                    type="button"
                    onClick={() => setShowSettings(!showSettings)}
                    style={{ background: showSettings ? 'var(--bg-secondary)' : 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: '0.3rem', borderRadius: '4px' }}
                >
                    <Settings size={20} />
                </button>
                <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                    style={{ background: 'none', border: 'none', color: uploading ? 'var(--accent)' : 'var(--text-secondary)', cursor: 'pointer', padding: '0.3rem', borderRadius: '4px' }}
                    title="Upload PDF (max 2.5MB)"
                >
                     {uploading ? <Loader2 size={20} style={{ animation: 'spin 1s linear infinite' }} /> : <Paperclip size={20} />}
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
                    style={{ border: 'none', background: 'transparent', padding: '0.5rem', flex: 1 }}
                    placeholder={useWebSearch ? "Search the web..." : "Ask a question about your knowledge base..."}
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
