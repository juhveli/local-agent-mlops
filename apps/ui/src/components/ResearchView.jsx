import React, { useState } from 'react';
import { Search, Loader2, Sparkles, BookOpen } from 'lucide-react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

const ResearchView = () => {
    const [query, setQuery] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);

    const handleSearch = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setResult(null);
        try {
            const response = await axios.post('/api/research', { query, max_iterations: 3 });
            setResult(response.data);
        } catch (error) {
            console.error(error);
            alert('Research failed. Check console.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ maxWidth: '800px', margin: '0 auto' }}>
            <header style={{ marginBottom: '3rem', textAlign: 'center' }}>
                <h2 style={{ fontSize: '2.5rem', marginBottom: '1rem', background: 'linear-gradient(to right, #3b82f6, #8b5cf6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                    Deep Research Agent
                </h2>
                <p style={{ color: 'var(--text-secondary)' }}>
                    Autonomous multi-step research powered by LLMs and Knowledge Graphs.
                </p>
            </header>

            <div className="card" style={{ marginBottom: '2rem' }}>
                <form onSubmit={handleSearch} style={{ display: 'flex', gap: '1rem' }}>
                    <div style={{ position: 'relative', flex: 1 }}>
                        <Search style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} size={20} />
                        <input
                            type="text"
                            className="input"
                            style={{ paddingLeft: '3rem' }}
                            placeholder="What do you want to research likely?"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            disabled={loading}
                        />
                    </div>
                    <button type="submit" className="btn" disabled={loading} style={{ minWidth: '120px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
                        {loading ? <><Loader2 className="spin" size={20} /> Thinking</> : <><Sparkles size={20} /> Research</>}
                    </button>
                </form>
            </div>

            {loading && (
                <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-secondary)' }}>
                    <Loader2 style={{ animation: 'spin 1s linear infinite', marginBottom: '1rem' }} size={48} />
                    <p>Decomposing query, searching Tavily, and verifying sources...</p>
                </div>
            )}

            {result && (
                <div style={{ display: 'grid', gap: '2rem' }}>
                    <section className="card">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--border)', paddingBottom: '1rem' }}>
                            <Sparkles size={24} color="#3b82f6" />
                            <h3 style={{ margin: 0 }}>Synthesized Answer</h3>
                        </div>
                        <div style={{ lineHeight: '1.6', fontSize: '1.1rem' }}>
                            <ReactMarkdown>{result.answer}</ReactMarkdown>
                        </div>
                    </section>

                    <section>
                        <h3 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <BookOpen size={20} /> Sources Used ({result.sources.length})
                        </h3>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '1rem' }}>
                            {result.sources.map((source) => (
                                <a
                                    key={source.id}
                                    href={source.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="card"
                                    style={{ textDecoration: 'none', color: 'inherit', transition: 'transform 0.2s', display: 'block' }}
                                    onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                                    onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                                >
                                    <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                                        Source #{source.id}
                                    </div>
                                    <div style={{ fontWeight: 600, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                                        {source.title}
                                    </div>
                                </a>
                            ))}
                        </div>
                    </section>
                </div>
            )}

            <style>{`
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
      `}</style>
        </div>
    );
};

export default ResearchView;
