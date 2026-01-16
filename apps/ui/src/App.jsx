import React, { useState } from 'react';
import ResearchView from './components/ResearchView';
import ChatInterface from './components/ChatInterface';
import MemoryView from './components/MemoryView';
import { LayoutDashboard, MessageSquare, Database } from 'lucide-react';

function App() {
    const [activeTab, setActiveTab] = useState('research');

    return (
        <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
            {/* Sidebar */}
            <aside style={{
                width: '260px',
                background: 'var(--bg-secondary)',
                borderRight: '1px solid var(--border)',
                padding: '1.5rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '1rem'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2rem' }}>
                    <div style={{ width: '32px', height: '32px', background: 'var(--accent)', borderRadius: '8px' }}></div>
                    <h1 style={{ fontSize: '1.25rem', fontWeight: 'bold', margin: 0 }}>Agent Ops</h1>
                </div>

                <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    <button
                        onClick={() => setActiveTab('research')}
                        style={{
                            display: 'flex', alignItems: 'center', gap: '0.75rem',
                            padding: '0.75rem', borderRadius: '8px',
                            background: activeTab === 'research' ? 'var(--bg-primary)' : 'transparent',
                            border: 'none', color: 'var(--text-primary)', cursor: 'pointer', textAlign: 'left'
                        }}
                    >
                        <LayoutDashboard size={20} />
                        Deep Research
                    </button>

                    <button
                        onClick={() => setActiveTab('chat')}
                        style={{
                            display: 'flex', alignItems: 'center', gap: '0.75rem',
                            padding: '0.75rem', borderRadius: '8px',
                            background: activeTab === 'chat' ? 'var(--bg-primary)' : 'transparent',
                            border: 'none', color: 'var(--text-primary)', cursor: 'pointer', textAlign: 'left'
                        }}
                    >
                        <MessageSquare size={20} />
                        Graph Chat
                    </button>

                    <button
                        onClick={() => setActiveTab('memory')}
                        style={{
                            display: 'flex', alignItems: 'center', gap: '0.75rem',
                            padding: '0.75rem', borderRadius: '8px',
                            background: activeTab === 'memory' ? 'var(--bg-primary)' : 'transparent',
                            border: 'none', color: 'var(--text-primary)', cursor: 'pointer', textAlign: 'left'
                        }}
                    >
                        <Database size={20} />
                        Memory Graph
                    </button>
                </nav>
            </aside>

            {/* Main Content - All components always mounted, visibility controlled by CSS */}
            <main style={{ flex: 1, overflow: 'auto', padding: '2rem' }}>
                <div className="container" style={{ height: '100%' }}>
                    <div style={{ display: activeTab === 'research' ? 'block' : 'none' }}>
                        <ResearchView />
                    </div>
                    <div style={{ display: activeTab === 'chat' ? 'block' : 'none' }}>
                        <ChatInterface />
                    </div>
                    <div style={{ display: activeTab === 'memory' ? 'block' : 'none', height: '100%' }}>
                        <MemoryView />
                    </div>
                </div>
            </main>
        </div>
    );
}

export default App;
