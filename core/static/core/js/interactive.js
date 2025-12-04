/**
 * Tracker Pro - Interactive Components
 * Optimistic UI, Undo, Form Validation, Auto-save
 */

// ============================================================================
// OPTIMISTIC UI UPDATES
// ============================================================================
App.optimisticToggle = async function (taskId, rowElement) {
    const oldStatus = rowElement.dataset.status;
    const statusIcon = rowElement.querySelector('.status-icon');
    const description = rowElement.querySelector('.task-description');

    // Determine new status
    const statusCycle = {
        'PENDING': 'DONE',
        'DONE': 'SKIPPED',
        'SKIPPED': 'PENDING',
        'MISSED': 'DONE'
    };
    const newStatus = statusCycle[oldStatus] || 'DONE';

    // Optimistic update
    rowElement.dataset.status = newStatus;
    statusIcon.className = `status-icon status-${newStatus.toLowerCase()}`;

    if (newStatus === 'DONE') {
        description?.classList.add('completed');
    } else {
        description?.classList.remove('completed');
    }

    // Add visual feedback
    rowElement.classList.add('updating');

    try {
        const response = await fetch(`${this.config.apiBase}task/${taskId}/toggle/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            }
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed');
        }

        // Show undo toast
        this.showUndoToast('Task updated', {
            type: 'task_toggle',
            data: { task_id: taskId, old_status: oldStatus }
        });

    } catch (error) {
        // Rollback on error
        rowElement.dataset.status = oldStatus;
        statusIcon.className = `status-icon status-${oldStatus.toLowerCase()}`;

        if (oldStatus === 'DONE') {
            description?.classList.add('completed');
        } else {
            description?.classList.remove('completed');
        }

        this.showToast('error', 'Failed to update', error.message);
    } finally {
        rowElement.classList.remove('updating');
    }
};

// Override default toggle with optimistic version
App.toggleTask = App.optimisticToggle;


// ============================================================================
// UNDO FUNCTIONALITY
// ============================================================================
App.undoStack = [];

App.showUndoToast = function (message, undoData) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'toast success with-action';
    toast.innerHTML = `
        <div class="toast-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
        </div>
        <div class="toast-content">
            <div class="toast-title">${message}</div>
        </div>
        <button type="button" class="toast-action" data-undo>Undo</button>
        <button type="button" class="toast-close" aria-label="Close">×</button>
    `;

    container.appendChild(toast);

    // Store undo data
    this.undoStack.push(undoData);
    toast.dataset.undoIndex = this.undoStack.length - 1;

    // Bind undo action
    toast.querySelector('[data-undo]').addEventListener('click', async () => {
        await this.performUndo(undoData);
        this.dismissToast(toast);
    });

    // Close button
    toast.querySelector('.toast-close').addEventListener('click', () => {
        this.dismissToast(toast);
    });

    // Auto dismiss after 5s
    setTimeout(() => {
        if (toast.parentElement) {
            this.dismissToast(toast);
        }
    }, 5000);
};

App.performUndo = async function (undoData) {
    try {
        const response = await fetch(`${this.config.apiBase}undo/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify(undoData)
        });

        const data = await response.json();

        if (response.ok && data.success) {
            this.showToast('success', 'Action undone');
            this.loadPanel(window.location.pathname, false);
        } else {
            throw new Error(data.error || 'Undo failed');
        }

    } catch (error) {
        this.showToast('error', 'Could not undo', error.message);
    }
};


// ============================================================================
// FORM VALIDATION
// ============================================================================
App.bindFormValidation = function (form) {
    if (!form) return;

    const inputs = form.querySelectorAll('input, textarea, select');

    inputs.forEach(input => {
        // Real-time validation on blur
        input.addEventListener('blur', () => this.validateField(input));

        // Clear error on input
        input.addEventListener('input', () => {
            const group = input.closest('.form-group');
            group?.classList.remove('has-error');
            group?.querySelector('.field-error')?.remove();
        });
    });

    // Form submit validation
    form.addEventListener('submit', (e) => {
        if (!this.validateForm(form)) {
            e.preventDefault();
        }
    });
};

App.validateField = async function (input) {
    const name = input.name;
    const value = input.value;
    const group = input.closest('.form-group');

    // Clear previous errors
    group?.classList.remove('has-error');
    group?.querySelector('.field-error')?.remove();

    // Required validation
    if (input.hasAttribute('required') && !value.trim()) {
        this.showFieldError(input, 'This field is required');
        return false;
    }

    // Min length
    const minLength = input.getAttribute('minlength');
    if (minLength && value.length < parseInt(minLength)) {
        this.showFieldError(input, `Must be at least ${minLength} characters`);
        return false;
    }

    // Max length
    const maxLength = input.getAttribute('maxlength');
    if (maxLength && value.length > parseInt(maxLength)) {
        this.showFieldError(input, `Must be no more than ${maxLength} characters`);
        return false;
    }

    // Email validation
    if (input.type === 'email' && value) {
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailPattern.test(value)) {
            this.showFieldError(input, 'Please enter a valid email');
            return false;
        }
    }

    // Server-side validation for specific fields
    const validateAsync = ['tracker_name', 'email'];
    if (validateAsync.includes(name) && value.trim()) {
        try {
            const response = await fetch(`${this.config.apiBase}validate/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({ field: name, value })
            });

            const data = await response.json();

            if (!data.valid && data.errors.length) {
                this.showFieldError(input, data.errors[0]);
                return false;
            }

        } catch (e) {
            // Ignore server validation errors
        }
    }

    return true;
};

App.validateForm = function (form) {
    let isValid = true;
    const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');

    inputs.forEach(input => {
        if (!input.value.trim()) {
            this.showFieldError(input, 'This field is required');
            isValid = false;
        }
    });

    return isValid;
};

App.showFieldError = function (input, message) {
    const group = input.closest('.form-group');
    if (!group) return;

    group.classList.add('has-error');
    input.classList.add('error');

    const existing = group.querySelector('.field-error');
    if (existing) {
        existing.textContent = message;
    } else {
        const errorEl = document.createElement('div');
        errorEl.className = 'field-error';
        errorEl.textContent = message;
        group.appendChild(errorEl);
    }
};


// ============================================================================
// AUTO-SAVE DRAFTS
// ============================================================================
App.draftKey = (formId) => `draft_${formId}_${window.location.pathname}`;

App.bindAutoSave = function (form) {
    if (!form || !form.id) return;

    const key = this.draftKey(form.id);
    let saveTimeout;

    // Restore draft
    const draft = localStorage.getItem(key);
    if (draft) {
        try {
            const data = JSON.parse(draft);
            this.restoreDraft(form, data);
            this.showDraftNotice(form);
        } catch (e) { }
    }

    // Auto-save on input
    form.addEventListener('input', () => {
        clearTimeout(saveTimeout);
        saveTimeout = setTimeout(() => this.saveDraft(form), 2000);
    });

    // Clear draft on submit
    form.addEventListener('submit', () => {
        localStorage.removeItem(key);
    });
};

App.saveDraft = function (form) {
    const key = this.draftKey(form.id);
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    localStorage.setItem(key, JSON.stringify({
        data,
        timestamp: Date.now()
    }));
};

App.restoreDraft = function (form, draft) {
    if (!draft.data) return;

    Object.entries(draft.data).forEach(([name, value]) => {
        const input = form.querySelector(`[name="${name}"]`);
        if (input && input.type !== 'hidden' && input.type !== 'password') {
            input.value = value;
        }
    });
};

App.showDraftNotice = function (form) {
    const notice = document.createElement('div');
    notice.className = 'draft-notice';
    notice.innerHTML = `
        <span>📝 Draft restored</span>
        <button type="button" class="btn btn-ghost btn-sm" data-clear-draft>Clear</button>
    `;

    form.prepend(notice);

    notice.querySelector('[data-clear-draft]').addEventListener('click', () => {
        localStorage.removeItem(this.draftKey(form.id));
        form.reset();
        notice.remove();
    });
};

App.clearDraft = function (formId) {
    localStorage.removeItem(this.draftKey(formId));
};


// ============================================================================
// DOUBLE-CLICK DELETE
// ============================================================================
App.bindDoubleClickDelete = function () {
    document.addEventListener('dblclick', (e) => {
        const deleteBtn = e.target.closest('[data-dblclick-delete]');
        if (!deleteBtn) return;

        const id = deleteBtn.dataset.dblclickDelete;
        const type = deleteBtn.dataset.type || 'item';

        this.confirmDelete(type, id);
    });

    // Single click shows hint
    document.addEventListener('click', (e) => {
        const deleteBtn = e.target.closest('[data-dblclick-delete]');
        if (!deleteBtn) return;

        // Show hint tooltip
        if (!deleteBtn.dataset.hintShown) {
            deleteBtn.dataset.hintShown = 'true';
            const hint = document.createElement('span');
            hint.className = 'delete-hint';
            hint.textContent = 'Double-click to delete';
            deleteBtn.appendChild(hint);

            setTimeout(() => hint.remove(), 2000);
        }
    });
};


// ============================================================================
// RICH TEXT EDITOR (Simple)
// ============================================================================
App.initRichTextEditor = function (textareas) {
    textareas.forEach(textarea => {
        if (textarea.dataset.richEditor) return;
        textarea.dataset.richEditor = 'true';

        const wrapper = document.createElement('div');
        wrapper.className = 'rich-editor';
        textarea.parentNode.insertBefore(wrapper, textarea);

        // Toolbar
        const toolbar = document.createElement('div');
        toolbar.className = 'rich-editor-toolbar';
        toolbar.innerHTML = `
            <button type="button" data-format="bold" title="Bold (Ctrl+B)"><strong>B</strong></button>
            <button type="button" data-format="italic" title="Italic (Ctrl+I)"><em>I</em></button>
            <button type="button" data-format="list" title="Bullet List">• List</button>
        `;

        wrapper.appendChild(toolbar);
        wrapper.appendChild(textarea);

        // Format handlers
        toolbar.querySelectorAll('[data-format]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const format = btn.dataset.format;
                this.applyFormat(textarea, format);
            });
        });

        // Keyboard shortcuts
        textarea.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                if (e.key === 'b') {
                    e.preventDefault();
                    this.applyFormat(textarea, 'bold');
                } else if (e.key === 'i') {
                    e.preventDefault();
                    this.applyFormat(textarea, 'italic');
                }
            }
        });
    });
};

App.applyFormat = function (textarea, format) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    const selected = text.substring(start, end);

    let formatted;
    switch (format) {
        case 'bold':
            formatted = `**${selected}**`;
            break;
        case 'italic':
            formatted = `*${selected}*`;
            break;
        case 'list':
            formatted = selected.split('\n').map(line => `• ${line}`).join('\n');
            break;
        default:
            formatted = selected;
    }

    textarea.value = text.substring(0, start) + formatted + text.substring(end);
    textarea.focus();
    textarea.setSelectionRange(start + formatted.length, start + formatted.length);
};


// ============================================================================
// INITIALIZE
// ============================================================================
App.initInteractive = function () {
    // Bind validation to forms
    document.querySelectorAll('form[data-validate]').forEach(form => {
        this.bindFormValidation(form);
    });

    // Bind auto-save to forms
    document.querySelectorAll('form[data-autosave]').forEach(form => {
        this.bindAutoSave(form);
    });

    // Bind rich text editors
    this.initRichTextEditor(document.querySelectorAll('textarea[data-rich]'));

    // Double-click delete
    this.bindDoubleClickDelete();
};

// Auto-run on panel load
const originalBindPanelEvents2 = App.bindPanelEvents.bind(App);
App.bindPanelEvents = function () {
    originalBindPanelEvents2();
    this.initInteractive();
};
