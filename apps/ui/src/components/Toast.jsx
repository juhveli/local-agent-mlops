import React, { useEffect } from 'react';
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react';

const ToastItem = ({ toast, onRemove }) => {
    useEffect(() => {
        const timer = setTimeout(() => {
            onRemove(toast.id);
        }, toast.duration || 5000);

        return () => clearTimeout(timer);
    }, [toast, onRemove]);

    const getIcon = () => {
        switch (toast.type) {
            case 'success': return <CheckCircle size={20} color="#22c55e" />;
            case 'error': return <AlertCircle size={20} color="#ef4444" />;
            default: return <Info size={20} color="#3b82f6" />;
        }
    };

    const getBorderColor = () => {
        switch (toast.type) {
            case 'success': return '#22c55e';
            case 'error': return '#ef4444';
            default: return '#3b82f6';
        }
    };

    return (
        <div style={{
            background: 'var(--bg-secondary)',
            border: `1px solid var(--border)`,
            borderLeft: `4px solid ${getBorderColor()}`,
            borderRadius: '8px',
            padding: '1rem',
            marginBottom: '0.75rem',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.75rem',
            minWidth: '300px',
            maxWidth: '400px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
            animation: 'slideIn 0.3s ease-out',
            color: 'var(--text-primary)',
            position: 'relative'
        }}>
            <div style={{ flexShrink: 0, paddingTop: '2px' }}>
                {getIcon()}
            </div>
            <div style={{ flex: 1 }}>
                {toast.title && <div style={{ fontWeight: '600', marginBottom: '0.25rem' }}>{toast.title}</div>}
                <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{toast.message}</div>
            </div>
            <button
                onClick={() => onRemove(toast.id)}
                style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                    padding: '2px'
                }}
            >
                <X size={16} />
            </button>
        </div>
    );
};

export const ToastContainer = ({ toasts, removeToast }) => {
    return (
        <div style={{
            position: 'fixed',
            bottom: '2rem',
            right: '2rem',
            zIndex: 9999,
            display: 'flex',
            flexDirection: 'column'
        }}>
            {toasts.map(toast => (
                <ToastItem key={toast.id} toast={toast} onRemove={removeToast} />
            ))}
            <style>{`
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            `}</style>
        </div>
    );
};
