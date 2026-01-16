import React, { useState } from 'react';
import ResearchView from './components/ResearchView';
import ChatInterface from './components/ChatInterface';
import { LayoutDashboard, MessageSquare } from 'lucide-react';

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
                        className={`nav-item ${activeTab === 'research' ? 'active' : ''}`}
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
                        className={`nav-item ${activeTab === 'chat' ? 'active' : ''}`}
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
                </nav>
            </aside>

            {/* Main Content - Both components always mounted, visibility controlled by CSS */}
            <main style={{ flex: 1, overflow: 'auto', padding: '2rem' }}>
                <div className="container">
                    <div style={{ display: activeTab === 'research' ? 'block' : 'none' }}>
                        <ResearchView />
                    </div>
                    <div style={{ display: activeTab === 'chat' ? 'block' : 'none' }}>
                        <ChatInterface />
                    </div>
                </div>
            </main>
        </div>
    );
}

export default App;
