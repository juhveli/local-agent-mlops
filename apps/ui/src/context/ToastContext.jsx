import React, { createContext, useState, useContext, useCallback } from 'react';
import { ToastContainer } from '../components/Toast';

const ToastContext = createContext();

export const useToast = () => {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within a ToastProvider');
    }
    return context;
};

export const ToastProvider = ({ children }) => {
    const [toasts, setToasts] = useState([]);

    const addToast = useCallback(({ message, title, type = 'info', duration = 5000 }) => {
        const id = Date.now() + Math.random();
        setToasts(prev => [...prev, { id, message, title, type, duration }]);
    }, []);

    const removeToast = useCallback((id) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    }, []);

    // Convenience methods
    const toast = {
        success: (message, title) => addToast({ message, title, type: 'success' }),
        error: (message, title) => addToast({ message, title, type: 'error' }),
        info: (message, title) => addToast({ message, title, type: 'info' }),
        custom: addToast
    };

    return (
        <ToastContext.Provider value={toast}>
            {children}
            <ToastContainer toasts={toasts} removeToast={removeToast} />
        </ToastContext.Provider>
    );
};
