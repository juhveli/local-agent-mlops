import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Database, RefreshCw, Loader2, Info, ZoomIn, ZoomOut } from 'lucide-react';
import axios from 'axios';
import ForceGraph2D from 'react-force-graph-2d';

const MemoryView = () => {
    const [graphData, setGraphData] = useState({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedNode, setSelectedNode] = useState(null);
    const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
    const containerRef = useRef(null);
    const graphRef = useRef();

    // Handle container resize
    useEffect(() => {
        const updateDimensions = () => {
            if (containerRef.current) {
                const rect = containerRef.current.getBoundingClientRect();
                setDimensions({ width: rect.width || 800, height: rect.height || 600 });
            }
        };

        updateDimensions();
        window.addEventListener('resize', updateDimensions);

        // Also update after a short delay to ensure container is rendered
        const timer = setTimeout(updateDimensions, 100);

        return () => {
            window.removeEventListener('resize', updateDimensions);
            clearTimeout(timer);
        };
    }, []);

    const fetchGraph = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await axios.get('/api/memory/graph');
            console.log('Graph data received:', response.data);
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
        // Center on node
        if (graphRef.current) {
            graphRef.current.centerAt(node.x, node.y, 500);
            graphRef.current.zoom(2, 500);
        }
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

    const handleCenterGraph = () => {
        if (graphRef.current) {
            graphRef.current.zoomToFit(400, 50);
        }
    };

    return (
        <div style={{ maxWidth: '100%', margin: '0 auto', height: 'calc(100vh - 4rem)', display: 'flex', flexDirection: 'column' }}>
            <header style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h2 style={{ fontSize: '1.5rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <Database size={24} color="#3b82f6" />
                        Memory Graph
                    </h2>
                    <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '0.9rem' }}>
                        Visualize your NornicDB knowledge graph • {graphData.nodes.length} nodes
                    </p>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button onClick={handleZoomIn} title="Zoom In" style={{ padding: '0.5rem', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '8px', cursor: 'pointer', color: 'var(--text-primary)' }}>
                        <ZoomIn size={18} />
                    </button>
                    <button onClick={handleZoomOut} title="Zoom Out" style={{ padding: '0.5rem', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '8px', cursor: 'pointer', color: 'var(--text-primary)' }}>
                        <ZoomOut size={18} />
                    </button>
                    <button onClick={handleCenterGraph} title="Fit to View" style={{ padding: '0.5rem 1rem', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '8px', cursor: 'pointer', color: 'var(--text-primary)', fontSize: '0.85rem' }}>
                        Fit
                    </button>
                    <button onClick={fetchGraph} disabled={loading} className="btn" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem' }}>
                        {loading ? <Loader2 size={18} className="spin" /> : <RefreshCw size={18} />}
                        Refresh
                    </button>
                </div>
            </header>

            <div style={{ display: 'flex', gap: '1rem', flex: 1, minHeight: 0 }}>
                {/* Graph Container */}
                <div
                    ref={containerRef}
                    className="card"
                    style={{ flex: 1, position: 'relative', overflow: 'hidden', padding: 0, background: '#0a0a0a' }}
                >
                    {loading && (
                        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(10,10,10,0.9)', zIndex: 10 }}>
                            <div style={{ textAlign: 'center' }}>
                                <Loader2 size={48} className="spin" style={{ marginBottom: '1rem' }} />
                                <p>Loading knowledge graph...</p>
                            </div>
                        </div>
                    )}

                    {error && !loading && (
                        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0a0a0a' }}>
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
                        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0a0a0a' }}>
                            <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
                                <Database size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                                <p>No data in knowledge graph yet.</p>
                                <p style={{ fontSize: '0.9rem' }}>Run some research queries to populate it!</p>
                            </div>
                        </div>
                    )}

                    {!loading && !error && graphData.nodes.length > 0 && dimensions.width > 0 && (
                        <ForceGraph2D
                            ref={graphRef}
                            graphData={graphData}
                            width={dimensions.width}
                            height={dimensions.height}
                            nodeLabel={(node) => `${node.name}\n${node.content?.substring(0, 100)}...`}
                            nodeColor={(node) => node.group === 1 ? '#3b82f6' : '#8b5cf6'}
                            nodeRelSize={6}
                            nodeVal={3}
                            linkColor={() => 'rgba(255,255,255,0.3)'}
                            linkWidth={1}
                            backgroundColor="#0a0a0a"
                            onNodeClick={handleNodeClick}
                            cooldownTicks={100}
                            onEngineStop={() => {
                                if (graphRef.current) {
                                    graphRef.current.zoomToFit(400, 50);
                                }
                            }}
                        />
                    )}
                </div>

                {/* Details Panel */}
                {selectedNode && (
                    <div className="card" style={{ width: '300px', overflow: 'auto', flexShrink: 0 }}>
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
                                <div style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Source URL</div>
                                <a href={selectedNode.name.startsWith('http') ? selectedNode.name : `https://${selectedNode.name}`} target="_blank" rel="noopener noreferrer" style={{ color: '#3b82f6', wordBreak: 'break-all' }}>
                                    {selectedNode.name}
                                </a>
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
        .spin { animation: spin 1s linear infinite; }
      `}</style>
        </div>
    );
};

export default MemoryView;
