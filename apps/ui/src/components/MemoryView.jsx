import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Database, RefreshCw, Loader2, Info, ZoomIn, ZoomOut } from 'lucide-react';
import axios from 'axios';

// Dynamic import for ForceGraph2D (it's a client-side only component)
let ForceGraph2D = null;

const MemoryView = () => {
    const [graphData, setGraphData] = useState({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedNode, setSelectedNode] = useState(null);
    const [graphLoaded, setGraphLoaded] = useState(false);
    const graphRef = useRef();

    // Dynamically import ForceGraph2D on client side
    useEffect(() => {
        import('react-force-graph').then((module) => {
            ForceGraph2D = module.ForceGraph2D;
            setGraphLoaded(true);
        });
    }, []);

    const fetchGraph = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await axios.get('/api/memory/graph');
            setGraphData(response.data);
        } catch (err) {
            console.error('Failed to fetch graph:', err);
            setError('Failed to load knowledge graph. Is NornicDB running?');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchGraph();
    }, [fetchGraph]);

    const handleNodeClick = useCallback((node) => {
        setSelectedNode(node);
    }, []);

    const handleZoomIn = () => {
        if (graphRef.current) {
            graphRef.current.zoom(graphRef.current.zoom() * 1.5, 300);
        }
    };

    const handleZoomOut = () => {
        if (graphRef.current) {
            graphRef.current.zoom(graphRef.current.zoom() / 1.5, 300);
        }
    };

    return (
        <div style={{ maxWidth: '100%', margin: '0 auto', height: 'calc(100vh - 4rem)' }}>
            <header style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h2 style={{ fontSize: '1.5rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <Database size={24} color="#3b82f6" />
                        Memory Graph
                    </h2>
                    <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '0.9rem' }}>
                        Visualize your NornicDB knowledge graph
                    </p>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button onClick={handleZoomIn} className="btn-secondary" style={{ padding: '0.5rem', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '8px', cursor: 'pointer' }}>
                        <ZoomIn size={18} />
                    </button>
                    <button onClick={handleZoomOut} className="btn-secondary" style={{ padding: '0.5rem', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '8px', cursor: 'pointer' }}>
                        <ZoomOut size={18} />
                    </button>
                    <button onClick={fetchGraph} disabled={loading} className="btn" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem' }}>
                        {loading ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> : <RefreshCw size={18} />}
                        Refresh
                    </button>
                </div>
            </header>

            <div style={{ display: 'flex', gap: '1rem', height: 'calc(100% - 4rem)' }}>
                {/* Graph Container */}
                <div className="card" style={{ flex: 1, position: 'relative', overflow: 'hidden', padding: 0 }}>
                    {loading && (
                        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-secondary)', zIndex: 10 }}>
                            <div style={{ textAlign: 'center' }}>
                                <Loader2 size={48} style={{ animation: 'spin 1s linear infinite', marginBottom: '1rem' }} />
                                <p>Loading knowledge graph...</p>
                            </div>
                        </div>
                    )}

                    {error && (
                        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-secondary)' }}>
                            <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
                                <Database size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                                <p>{error}</p>
                                <button onClick={fetchGraph} className="btn" style={{ marginTop: '1rem' }}>
                                    Retry
                                </button>
                            </div>
                        </div>
                    )}

                    {!loading && !error && graphData.nodes.length === 0 && (
                        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-secondary)' }}>
                            <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
                                <Database size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                                <p>No data in knowledge graph yet.</p>
                                <p style={{ fontSize: '0.9rem' }}>Run some research queries to populate it!</p>
                            </div>
                        </div>
                    )}

                    {graphLoaded && ForceGraph2D && !loading && !error && graphData.nodes.length > 0 && (
                        <ForceGraph2D
                            ref={graphRef}
                            graphData={graphData}
                            nodeLabel="name"
                            nodeColor={(node) => node.group === 1 ? '#3b82f6' : '#8b5cf6'}
                            nodeRelSize={6}
                            linkColor={() => 'rgba(255,255,255,0.2)'}
                            linkWidth={1}
                            backgroundColor="#0a0a0a"
                            onNodeClick={handleNodeClick}
                            nodeCanvasObject={(node, ctx, globalScale) => {
                                const label = node.name || node.id;
                                const fontSize = 12 / globalScale;
                                ctx.font = `${fontSize}px Inter, sans-serif`;
                                ctx.fillStyle = node.group === 1 ? '#3b82f6' : '#8b5cf6';
                                ctx.beginPath();
                                ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI, false);
                                ctx.fill();
                                ctx.fillStyle = '#ededed';
                                ctx.textAlign = 'center';
                                ctx.textBaseline = 'middle';
                                if (globalScale > 0.5) {
                                    ctx.fillText(label.substring(0, 20), node.x, node.y + 12);
                                }
                            }}
                        />
                    )}
                </div>

                {/* Details Panel */}
                {selectedNode && (
                    <div className="card" style={{ width: '300px', overflow: 'auto' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', paddingBottom: '1rem', borderBottom: '1px solid var(--border)' }}>
                            <Info size={20} color="#3b82f6" />
                            <h3 style={{ margin: 0 }}>Node Details</h3>
                        </div>
                        <div style={{ fontSize: '0.9rem' }}>
                            <div style={{ marginBottom: '1rem' }}>
                                <div style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>ID</div>
                                <div style={{ fontFamily: 'monospace', fontSize: '0.85rem', wordBreak: 'break-all' }}>{selectedNode.id}</div>
                            </div>
                            <div style={{ marginBottom: '1rem' }}>
                                <div style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Name</div>
                                <div>{selectedNode.name}</div>
                            </div>
                            {selectedNode.content && (
                                <div>
                                    <div style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Content Preview</div>
                                    <div style={{ fontSize: '0.85rem', lineHeight: 1.5, opacity: 0.9 }}>{selectedNode.content}</div>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>

            <style>{`
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
      `}</style>
        </div>
    );
};

export default MemoryView;
