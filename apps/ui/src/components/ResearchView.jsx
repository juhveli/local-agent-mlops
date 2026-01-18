import React, { useState } from 'react';
import { Search, Loader2, Sparkles, Settings } from 'lucide-react';
import axios from 'axios';
import ResearchResult from './ResearchResult';

const ResearchView = () => {
    const [query, setQuery] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [showSettings, setShowSettings] = useState(false);

    // Search Settings
    const [provider, setProvider] = useState('tavily'); // 'tavily' | 'duckduckgo'
    const [searchDepth, setSearchDepth] = useState('basic'); // 'basic' | 'advanced'
    const [highAuthorityOnly, setHighAuthorityOnly] = useState(false);

    const handleSearch = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setResult(null);
        try {
            const payload = {
                query,
                max_iterations: 3,
                provider,
                search_depth: searchDepth,
                include_domains: highAuthorityOnly ? ["HIGH_AUTHORITY"] : []
            };
            const response = await axios.post('/api/research', payload);
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
                <form onSubmit={handleSearch} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div style={{ display: 'flex', gap: '1rem' }}>
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
                        <button
                            type="button"
                            className="btn-secondary"
                            onClick={() => setShowSettings(!showSettings)}
                            style={{ padding: '0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', background: showSettings ? 'var(--bg-secondary)' : 'transparent', border: '1px solid var(--border)' }}
                        >
                            <Settings size={20} />
                        </button>
                        <button type="submit" className="btn" disabled={loading} style={{ minWidth: '120px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
                            {loading ? <><Loader2 className="spin" size={20} /> Thinking</> : <><Sparkles size={20} /> Research</>}
                        </button>
                    </div>

                    {showSettings && (
                        <div style={{ padding: '1rem', background: 'var(--bg-secondary)', borderRadius: '8px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                            <div>
                                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Search Provider</label>
                                <select
                                    className="input"
                                    value={provider}
                                    onChange={(e) => setProvider(e.target.value)}
                                    style={{ width: '100%' }}
                                >
                                    <option value="tavily">Tavily (Standard)</option>
                                    <option value="duckduckgo">DuckDuckGo (Free)</option>
                                </select>
                            </div>

                            <div>
                                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Search Depth</label>
                                <select
                                    className="input"
                                    value={searchDepth}
                                    onChange={(e) => setSearchDepth(e.target.value)}
                                    style={{ width: '100%' }}
                                    disabled={provider === 'duckduckgo'}
                                >
                                    <option value="basic">Basic (Faster)</option>
                                    <option value="advanced">Advanced (Better Quality)</option>
                                </select>
                            </div>

                            <div style={{ display: 'flex', alignItems: 'center' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                    <input
                                        type="checkbox"
                                        checked={highAuthorityOnly}
                                        onChange={(e) => setHighAuthorityOnly(e.target.checked)}
                                        style={{ width: '16px', height: '16px' }}
                                    />
                                    <span>High Authority Sources Only</span>
                                </label>
                            </div>
                        </div>
                    )}
                </form>
            </div>

            {loading && (
                <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-secondary)' }}>
                    <Loader2 style={{ animation: 'spin 1s linear infinite', marginBottom: '1rem' }} size={48} />
                    <p>Decomposing query, searching Tavily, and verifying sources...</p>
                </div>
            )}

            {result && <ResearchResult result={result} />}

            <style>{`
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
      `}</style>
        </div>
    );
};

export default ResearchView;
