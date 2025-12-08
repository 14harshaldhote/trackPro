/**
 * Undo System
 * Allows users to undo recent destructive actions like deletions
 */

class UndoManager {
    constructor(options = {}) {
        this.timeout = options.timeout || 10000; // 10 seconds default
        this.maxActions = options.maxActions || 10;
        this.pendingActions = [];
        this.toastContainer = null;

        this.init();
    }

    init() {
        this.createToastContainer();

        // Listen for custom undo events
        document.addEventListener('action:undoable', (e) => {
            this.trackAction(e.detail);
        });
    }

    createToastContainer() {
        this.toastContainer = document.createElement('div');
        this.toastContainer.className = 'undo-toast-container';
        this.toastContainer.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 10000;
            display: flex;
            flex-direction: column;
            gap: 12px;
        `;
        document.body.appendChild(this.toastContainer);
    }

    trackAction(action) {
        /**
         * Track an undoable action
         * 
         * action: {
         *   id: unique identifier
         *   type: 'delete_task', 'delete_goal', 'clear_data'
         *   message: 'Task deleted'
         *   data: serialized object data
         *   onUndo: callback function (optional - for client-side undo)
         * }
         */

        // Add to pending actions
        this.pendingActions.push(action);

        // Limit queue size
        if (this.pendingActions.length > this.maxActions) {
            const removed = this.pendingActions.shift();
            this.expireAction(removed);
        }

        // Show undo toast
        this.showUndoToast(action);
    }

    showUndoToast(action) {
        const toast = document.createElement('div');
        toast.className = 'undo-toast';
        toast.dataset.actionId = action.id;
        toast.style.cssText = `
            background: #333;
            color: white;
            padding: 16px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            display: flex;
            align-items: center;
            gap: 16px;
            min-width: 320px;
            animation: slideIn 0.3s ease-out;
        `;

        toast.innerHTML = `
            <span class="undo-message" style="flex: 1;">${this.escapeHtml(action.message)}</span>
            <button class="undo-btn" style="
                background: #fff;
                color: #333;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
            ">Undo</button>
            <button class="dismiss-btn" style="
                background: transparent;
                color: #999;
                border: none;
                padding: 8px;
                cursor: pointer;
                font-size: 20px;
            ">×</button>
        `;

        // Undo button click
        const undoBtn = toast.querySelector('.undo-btn');
        undoBtn.addEventListener('click', () => {
            undoBtn.disabled = true;
            undoBtn.textContent = 'Undoing...';
            this.executeUndo(action, toast);
        });

        // Dismiss button
        toast.querySelector('.dismiss-btn').addEventListener('click', () => {
            this.dismissToast(toast, action);
        });

        // Add to container
        this.toastContainer.appendChild(toast);

        // Auto-expire after timeout
        const timer = setTimeout(() => {
            this.expireToast(toast, action);
        }, this.timeout);

        action.timer = timer;
        action.toast = toast;
    }

    async executeUndo(action, toast) {
        try {
            // If action has client-side undo callback
            if (action.onUndo) {
                await action.onUndo(action.data);
                this.showSuccess(action, toast);
                return;
            }

            // Otherwise call server-side undo API
            const response = await fetch('/api/v1/undo/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    action_id: action.id,
                    action_type: action.type,
                    action_data: action.data
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Undo failed');
            }

            this.showSuccess(action, toast);

        } catch (error) {
            console.error('[UndoManager] Undo failed:', error);
            this.showError(action, toast, error.message);
        }
    }

    showSuccess(action, toast) {
        clearTimeout(action.timer);

        toast.className = 'undo-toast undo-success';
        toast.innerHTML = `
            <span style="flex: 1;">✓ Undone successfully</span>
        `;

        setTimeout(() => {
            this.dismissToast(toast, action);
        }, 2000);

        // Remove from pending
        this.pendingActions = this.pendingActions.filter(a => a.id !== action.id);

        // Trigger undo success event
        document.dispatchEvent(new CustomEvent('action:undone', {
            detail: { action, success: true }
        }));
    }

    showError(action, toast, errorMessage) {
        toast.className = 'undo-toast undo-error';
        toast.innerHTML = `
            <span style="flex: 1;">✗ Undo failed: ${this.escapeHtml(errorMessage)}</span>
            <button class="dismiss-btn" style="
                background: transparent;
                color: #999;
                border: none;
                padding: 8px;
                cursor: pointer;
                font-size: 20px;
            ">×</button>
        `;

        toast.querySelector('.dismiss-btn').addEventListener('click', () => {
            this.dismissToast(toast, action);
        });

        setTimeout(() => {
            this.dismissToast(toast, action);
        }, 5000);
    }

    dismissToast(toast, action) {
        if (action.timer) {
            clearTimeout(action.timer);
        }

        toast.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => {
            toast.remove();
        }, 300);

        this.pendingActions = this.pendingActions.filter(a => a.id !== action.id);
    }

    expireToast(toast, action) {
        console.log('[UndoManager] Action expired:', action.id);

        toast.style.animation = 'fadeOut 0.3s ease-in';
        setTimeout(() => {
            toast.remove();
        }, 300);

        this.pendingActions = this.pendingActions.filter(a => a.id !== action.id);

        // Trigger expire event
        document.dispatchEvent(new CustomEvent('action:expired', {
            detail: { action }
        }));
    }

    expireAction(action) {
        if (action.toast) {
            this.expireToast(action.toast, action);
        }
    }

    getCsrfToken() {
        const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Public methods
    clear() {
        this.pendingActions.forEach(action => {
            if (action.timer) clearTimeout(action.timer);
            if (action.toast) action.toast.remove();
        });
        this.pendingActions = [];
    }
}

// CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    @keyframes fadeOut {
        from {
            opacity: 1;
        }
        to {
            opacity: 0;
        }
    }
    
    .undo-btn:hover {
        transform: scale(1.05);
    }
    
    .undo-toast.undo-success {
        background: #10B981 !important;
    }
    
    .undo-toast.undo-error {
        background: #EF4444 !important;
    }
`;
document.head.appendChild(style);

// Global instance
window.undoManager = new UndoManager({
    timeout: 10000,  // 10 seconds
    maxActions: 5
});

// Helper function for easy undo tracking
window.trackUndoableAction = function (message, type, data, onUndo) {
    const actionId = `undo_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    document.dispatchEvent(new CustomEvent('action:undoable', {
        detail: {
            id: actionId,
            type,
            message,
            data,
            onUndo
        }
    }));

    return actionId;
};

console.log('[UndoManager] Initialized - tracking undoable actions');
