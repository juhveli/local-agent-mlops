import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Database, RefreshCw, Loader2, Info, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';
import axios from 'axios';
import ForceGraph3D from 'react-force-graph-3d';

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
        // Focus camera on node
        if (graphRef.current) {
            const distance = 100;
            const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z);
            graphRef.current.cameraPosition(
                { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
                node,
                1500
            );
        }
    }, []);

    const handleZoomIn = () => {
        if (graphRef.current) {
            const camera = graphRef.current.camera();
            camera.zoom = (camera.zoom || 1) * 1.3;
            camera.updateProjectionMatrix();
        }
    };

    const handleZoomOut = () => {
        if (graphRef.current) {
            const camera = graphRef.current.camera();
            camera.zoom = (camera.zoom || 1) / 1.3;
            camera.updateProjectionMatrix();
        }
    };

    const handleResetView = () => {
        if (graphRef.current) {
            graphRef.current.cameraPosition({ x: 0, y: 0, z: 500 }, null, 1000);
        }
    };

    // Custom node color based on group
    const getNodeColor = (node) => {
        if (node.group === 1) return '#3b82f6'; // Blue for Neo4j nodes
        return '#8b5cf6'; // Purple for Qdrant nodes
    };

    // Custom link color based on type
    const getLinkColor = (link) => {
        if (link.type === 'same_query') return 'rgba(59, 130, 246, 0.6)'; // Blue
        if (link.type === 'same_domain') return 'rgba(139, 92, 246, 0.4)'; // Purple
        return 'rgba(255, 255, 255, 0.2)';
    };

    return (
        <div style={{ maxWidth: '100%', margin: '0 auto', height: 'calc(100vh - 4rem)', display: 'flex', flexDirection: 'column' }}>
            <header style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h2 style={{ fontSize: '1.5rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <Database size={24} color="#3b82f6" />
                        Memory Graph
                        <span style={{ fontSize: '0.75rem', background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', padding: '0.25rem 0.5rem', borderRadius: '4px', fontWeight: 'normal' }}>3D</span>
                    </h2>
                    <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '0.9rem' }}>
                        {graphData.nodes.length} nodes • {graphData.links.length} connections
                    </p>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button onClick={handleZoomIn} title="Zoom In" style={{ padding: '0.5rem', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '8px', cursor: 'pointer', color: 'var(--text-primary)' }}>
                        <ZoomIn size={18} />
                    </button>
                    <button onClick={handleZoomOut} title="Zoom Out" style={{ padding: '0.5rem', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '8px', cursor: 'pointer', color: 'var(--text-primary)' }}>
                        <ZoomOut size={18} />
                    </button>
                    <button onClick={handleResetView} title="Reset View" style={{ padding: '0.5rem', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '8px', cursor: 'pointer', color: 'var(--text-primary)' }}>
                        <RotateCcw size={18} />
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
                    style={{ flex: 1, position: 'relative', overflow: 'hidden', padding: 0, background: '#050510' }}
                >
                    {loading && (
                        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(5,5,16,0.9)', zIndex: 10 }}>
                            <div style={{ textAlign: 'center' }}>
                                <Loader2 size={48} className="spin" style={{ marginBottom: '1rem' }} />
                                <p>Loading 3D knowledge graph...</p>
                            </div>
                        </div>
                    )}

                    {error && !loading && (
                        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#050510' }}>
                            <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
                                <Database size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                                <p>{error}</p>
                                <button onClick={fetchGraph} className="btn" style={{ marginTop: '1rem' }}>Retry</button>
                            </div>
                        </div>
                    )}

                    {!loading && !error && graphData.nodes.length === 0 && (
                        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#050510' }}>
                            <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
                                <Database size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                                <p>No data in knowledge graph yet.</p>
                                <p style={{ fontSize: '0.9rem' }}>Run some research queries to populate it!</p>
                            </div>
                        </div>
                    )}

                    {!loading && !error && graphData.nodes.length > 0 && dimensions.width > 0 && (
                        <ForceGraph3D
                            ref={graphRef}
                            graphData={graphData}
                            width={dimensions.width}
                            height={dimensions.height}
                            nodeLabel={(node) => `${node.name}\n${node.content?.substring(0, 80)}...`}
                            nodeColor={getNodeColor}
                            nodeOpacity={0.9}
                            nodeResolution={16}
                            linkColor={getLinkColor}
                            linkWidth={(link) => link.type === 'same_query' ? 2 : 1}
                            linkOpacity={0.6}
                            backgroundColor="#050510"
                            onNodeClick={handleNodeClick}
                            showNavInfo={false}
                            enableNodeDrag={true}
                            enableNavigationControls={true}
                            controlType="orbit"
                        />
                    )}

                    {/* Legend */}
                    {!loading && !error && graphData.nodes.length > 0 && (
                        <div style={{ position: 'absolute', bottom: '1rem', left: '1rem', background: 'rgba(0,0,0,0.7)', padding: '0.75rem', borderRadius: '8px', fontSize: '0.8rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                                <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#3b82f6' }}></div>
                                <span>Neo4j Nodes</span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                                <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#8b5cf6' }}></div>
                                <span>Vector Memory</span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                                <div style={{ width: 20, height: 2, background: 'rgba(59, 130, 246, 0.8)' }}></div>
                                <span>Same Query</span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <div style={{ width: 20, height: 1, background: 'rgba(139, 92, 246, 0.6)' }}></div>
                                <span>Same Domain</span>
                            </div>
                        </div>
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
                                <div style={{ fontFamily: 'monospace', fontSize: '0.8rem', wordBreak: 'break-all', background: 'var(--bg-secondary)', padding: '0.5rem', borderRadius: '4px' }}>{selectedNode.id}</div>
                            </div>
                            <div style={{ marginBottom: '1rem' }}>
                                <div style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Source URL</div>
                                <a href={selectedNode.name?.startsWith('http') ? selectedNode.name : `https://${selectedNode.name}`} target="_blank" rel="noopener noreferrer" style={{ color: '#3b82f6', wordBreak: 'break-all', fontSize: '0.85rem' }}>
                                    {selectedNode.name}
                                </a>
                            </div>
                            {selectedNode.query && (
                                <div style={{ marginBottom: '1rem' }}>
                                    <div style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Query</div>
                                    <div style={{ fontSize: '0.85rem', fontStyle: 'italic' }}>"{selectedNode.query}"</div>
                                </div>
                            )}
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
