import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Sparkles, BookOpen, Download } from 'lucide-react';

const ResearchResult = React.memo(({ result }) => {
    if (!result) return null;

    const handleExport = () => {
        const sourcesText = result.sources.map(s => `- [${s.title}](${s.url})`).join('\n');
        const content = `# Research Result\n\n## Answer\n\n${result.answer}\n\n## Sources\n\n${sourcesText}`;

        const blob = new Blob([content], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `research-result-${Date.now()}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    return (
        <div style={{ display: 'grid', gap: '2rem' }}>
            <section className="card">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', borderBottom: '1px solid var(--border)', paddingBottom: '1rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <Sparkles size={24} color="#3b82f6" />
                        <h3 style={{ margin: 0 }}>Synthesized Answer</h3>
                    </div>
                    <button
                        onClick={handleExport}
                        style={{
                            display: 'flex', alignItems: 'center', gap: '0.5rem',
                            padding: '0.5rem 1rem', background: 'var(--bg-primary)',
                            border: '1px solid var(--border)', borderRadius: '8px',
                            color: 'var(--text-primary)', cursor: 'pointer'
                        }}
                    >
                        <Download size={16} /> Export
                    </button>
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
    );
});

export default ResearchResult;
