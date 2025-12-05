/**
 * Tracker Pro - Phase 2 Enhancements
 * Panel-specific functionality: filters, bulk actions, drag-drop, context menus
 */

// ============================================================================
// VIEW TOGGLE (Grid/List)
// ============================================================================
App.bindViewToggle = function () {
    document.querySelectorAll('.view-toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            const container = document.getElementById('trackers-container');

            // Update buttons
            document.querySelectorAll('.view-toggle-btn').forEach(b => {
                b.classList.remove('active');
                b.setAttribute('aria-pressed', 'false');
            });
            btn.classList.add('active');
            btn.setAttribute('aria-pressed', 'true');

            // Update container
            if (container) {
                container.setAttribute('data-view', view);
                localStorage.setItem('tracker-view', view);
            }
        });
    });

    // Restore saved view
    const savedView = localStorage.getItem('tracker-view') || 'grid';
    document.querySelector(`[data-view="${savedView}"]`)?.click();
};

// ============================================================================
// FILTERS WITH URL PARAMS
// ============================================================================
App.bindFilters = function () {
    const filters = document.querySelectorAll('[name^="filter-"]');
    const clearBtn = document.getElementById('clear-filters');

    filters.forEach(filter => {
        filter.addEventListener('change', () => this.applyFilters());
    });

    clearBtn?.addEventListener('click', () => {
        filters.forEach(f => f.checked = false);
        this.applyFilters();
    });

    // Restore from URL
    const params = new URLSearchParams(window.location.search);
    params.getAll('status').forEach(s => {
        document.querySelector(`[name="filter-status"][value="${s}"]`)?.setAttribute('checked', true);
    });
    params.getAll('period').forEach(p => {
        document.querySelector(`[name="filter-period"][value="${p}"]`)?.setAttribute('checked', true);
    });
};

App.applyFilters = function () {
    const params = new URLSearchParams();

    document.querySelectorAll('[name="filter-status"]:checked').forEach(cb => {
        params.append('status', cb.value);
    });
    document.querySelectorAll('[name="filter-period"]:checked').forEach(cb => {
        params.append('period', cb.value);
    });

    // Update URL without reload
    const newUrl = params.toString()
        ? `${window.location.pathname}?${params.toString()}`
        : window.location.pathname;
    history.replaceState({}, '', newUrl);

    // Update filter count
    const count = document.querySelectorAll('[name^="filter-"]:checked').length;
    const badge = document.getElementById('filter-count');
    if (badge) {
        badge.style.display = count > 0 ? 'inline' : 'none';
        badge.textContent = count;
    }

    // Reload with filters
    this.loadPanel(newUrl, false);
};

// ============================================================================
// SORT
// ============================================================================
App.bindSort = function () {
    document.querySelectorAll('[data-sort]').forEach(btn => {
        btn.addEventListener('click', () => {
            const sort = btn.dataset.sort;
            document.getElementById('current-sort').textContent = btn.textContent;
            this.closeDropdowns();

            // Add to URL and reload
            const params = new URLSearchParams(window.location.search);
            params.set('sort', sort);
            const newUrl = `${window.location.pathname}?${params.toString()}`;
            history.replaceState({}, '', newUrl);
            this.loadPanel(newUrl, false);
        });
    });
};

// ============================================================================
// FILTER TABS
// ============================================================================
App.bindFilterTabs = function () {
    document.querySelectorAll('.filter-tab, .tab[data-filter]').forEach(tab => {
        tab.addEventListener('click', () => {
            const filter = tab.dataset.filter;

            // Update active state
            tab.parentElement.querySelectorAll('.filter-tab, .tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Filter items
            const items = document.querySelectorAll('[data-status]');
            items.forEach(item => {
                if (filter === 'all') {
                    item.style.display = '';
                } else if (filter === 'pending') {
                    item.style.display = item.dataset.status !== 'DONE' ? '' : 'none';
                } else if (filter === 'done') {
                    item.style.display = item.dataset.status === 'DONE' ? '' : 'none';
                } else if (filter === 'missed') {
                    item.style.display = item.dataset.status === 'MISSED' ? '' : 'none';
                }
            });
        });
    });
};

// ============================================================================
// BULK SELECTION
// ============================================================================
App.bindBulkSelection = function () {
    const selectAll = document.getElementById('select-all');
    const bulkToolbar = document.getElementById('bulk-toolbar');
    const bulkCount = document.getElementById('bulk-count');
    const cancelBtn = document.getElementById('bulk-cancel');

    // Select all
    selectAll?.addEventListener('change', (e) => {
        document.querySelectorAll('.bulk-select').forEach(cb => {
            cb.checked = e.target.checked;
        });
        this.updateBulkToolbar();
    });

    // Individual checkboxes
    document.querySelectorAll('.bulk-select').forEach(cb => {
        cb.addEventListener('change', () => this.updateBulkToolbar());
    });

    // Cancel selection
    cancelBtn?.addEventListener('click', () => {
        document.querySelectorAll('.bulk-select').forEach(cb => cb.checked = false);
        if (selectAll) selectAll.checked = false;
        this.updateBulkToolbar();
    });

    // Bulk actions
    document.querySelectorAll('[data-bulk-action]').forEach(btn => {
        btn.addEventListener('click', () => {
            const action = btn.dataset.bulkAction;
            const selected = Array.from(document.querySelectorAll('.bulk-select:checked'))
                .map(cb => cb.dataset.taskId);

            if (selected.length === 0) return;

            this.handleBulkAction(action, selected);
        });
    });
};

App.updateBulkToolbar = function () {
    const toolbar = document.getElementById('bulk-toolbar');
    const count = document.getElementById('bulk-count');
    const selected = document.querySelectorAll('.bulk-select:checked').length;

    if (toolbar) {
        toolbar.style.display = selected > 0 ? 'flex' : 'none';
    }
    if (count) {
        count.textContent = selected;
    }
};

App.handleBulkAction = async function (action, taskIds) {
    try {
        const response = await fetch(`${this.config.apiBase}tasks/bulk/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify({ action, task_ids: taskIds })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            this.showToast('success', `${taskIds.length} tasks updated`);
            this.loadPanel(window.location.pathname, false);
        } else {
            throw new Error(data.error || 'Action failed');
        }
    } catch (error) {
        console.error('Bulk action error:', error);
        this.showToast('error', 'Failed to perform action', error.message);
    }
};

// ============================================================================
// CONTEXT MENU
// ============================================================================
App.bindContextMenu = function () {
    let activeMenu = null;
    let targetElement = null;

    // Right-click on tasks/trackers
    document.addEventListener('contextmenu', (e) => {
        const taskRow = e.target.closest('.task-row');
        const trackerItem = e.target.closest('.tracker-item');

        if (taskRow) {
            e.preventDefault();
            targetElement = taskRow;
            this.showContextMenu('task-context-menu', e.pageX, e.pageY);
        } else if (trackerItem) {
            e.preventDefault();
            targetElement = trackerItem;
            this.showContextMenu('tracker-context-menu', e.pageX, e.pageY);
        }
    });

    // Three-dot menu button
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-action="context-menu"]');
        if (btn) {
            e.preventDefault();
            e.stopPropagation();
            targetElement = btn.closest('.task-row') || btn.closest('.tracker-item');
            const rect = btn.getBoundingClientRect();
            const menuId = targetElement.classList.contains('task-row') ? 'task-context-menu' : 'tracker-context-menu';
            this.showContextMenu(menuId, rect.left, rect.bottom + 5);
        }
    });

    // Context menu actions
    document.querySelectorAll('.context-menu-item').forEach(item => {
        item.addEventListener('click', () => {
            if (!targetElement) return;

            const action = item.dataset.action;
            const id = targetElement.dataset.taskId || targetElement.dataset.trackerId;

            this.hideContextMenu();
            this.handleContextAction(action, id, targetElement);
        });
    });

    // Close on click outside
    document.addEventListener('click', () => this.hideContextMenu());
    document.addEventListener('scroll', () => this.hideContextMenu());
};

App.showContextMenu = function (menuId, x, y) {
    this.hideContextMenu();

    const menu = document.getElementById(menuId);
    if (!menu) return;

    menu.style.display = 'block';
    menu.style.left = `${Math.min(x, window.innerWidth - 200)}px`;
    menu.style.top = `${Math.min(y, window.innerHeight - 200)}px`;
};

App.hideContextMenu = function () {
    document.querySelectorAll('.context-menu').forEach(menu => {
        menu.style.display = 'none';
    });
};

App.handleContextAction = function (action, id, element) {
    switch (action) {
        case 'complete':
            this.toggleTask(id, element);
            break;
        case 'skip':
            this.updateTaskStatus(id, 'SKIPPED');
            break;
        case 'edit':
            if (element.dataset.taskId) {
                this.loadModal(`/modals/edit_task/?task_id=${id}`);
            } else {
                this.loadModal(`/modals/edit_tracker/?tracker_id=${id}`);
            }
            break;
        case 'duplicate':
            this.duplicateItem(id, element);
            break;
        case 'archive':
            this.archiveTracker(id);
            break;
        case 'delete':
            this.confirmDelete(element.dataset.taskId ? 'task' : 'tracker', id);
            break;
    }
};

App.updateTaskStatus = async function (taskId, status) {
    try {
        const response = await fetch(`${this.config.apiBase}task/${taskId}/status/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify({ status })
        });

        if (response.ok) {
            this.showToast('success', 'Task updated');
            this.loadPanel(window.location.pathname, false);
        }
    } catch (error) {
        this.showToast('error', 'Failed to update task');
    }
};

// ============================================================================
// DRAG & DROP (Using native HTML5)
// ============================================================================
App.bindDragDrop = function () {
    const container = document.getElementById('task-list');
    if (!container?.classList.contains('sortable')) return;

    let draggedElement = null;

    container.addEventListener('dragstart', (e) => {
        const taskRow = e.target.closest('.task-row');
        if (!taskRow) return;

        draggedElement = taskRow;
        taskRow.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', taskRow.dataset.taskId);
    });

    container.addEventListener('dragend', (e) => {
        const taskRow = e.target.closest('.task-row');
        if (taskRow) taskRow.classList.remove('dragging');
        draggedElement = null;
    });

    container.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';

        const afterElement = this.getDragAfterElement(container, e.clientY);
        if (afterElement == null) {
            container.appendChild(draggedElement);
        } else {
            container.insertBefore(draggedElement, afterElement);
        }
    });

    container.addEventListener('drop', (e) => {
        e.preventDefault();
        this.saveTaskOrder(container);
    });
};

App.getDragAfterElement = function (container, y) {
    const draggableElements = [...container.querySelectorAll('.task-row:not(.dragging)')];

    return draggableElements.reduce((closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;

        if (offset < 0 && offset > closest.offset) {
            return { offset, element: child };
        } else {
            return closest;
        }
    }, { offset: Number.NEGATIVE_INFINITY }).element;
};

App.saveTaskOrder = async function (container) {
    const taskIds = [...container.querySelectorAll('.task-row')]
        .map(row => row.dataset.taskId);

    try {
        const trackerId = container.dataset.trackerId;
        await fetch(`${this.config.apiBase}tracker/${trackerId}/reorder/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify({ order: taskIds })
        });

        this.showToast('success', 'Order saved');
    } catch (error) {
        console.error('Reorder failed:', error);
    }
};

// ============================================================================
// QUICK ADD TASK
// ============================================================================
App.bindQuickAdd = function () {
    const input = document.getElementById('quick-task-input');
    const btn = document.getElementById('quick-add-btn');

    if (!input) return;

    const addTask = async () => {
        const description = input.value.trim();
        if (!description) return;

        const trackerId = document.querySelector('[data-tracker-id]')?.dataset.trackerId;
        if (!trackerId) return;

        this.setButtonLoading(btn, true);

        try {
            const response = await fetch(`${this.config.apiBase}tracker/${trackerId}/task/add/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({ description })
            });

            if (response.ok) {
                input.value = '';
                this.loadPanel(window.location.pathname, false);
            }
        } catch (error) {
            this.showToast('error', 'Failed to add task');
        } finally {
            this.setButtonLoading(btn, false);
        }
    };

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addTask();
        }
    });

    btn?.addEventListener('click', addTask);
};

// ============================================================================
// PAGINATION / INFINITE SCROLL
// ============================================================================
App.bindPagination = function () {
    const loadMoreBtn = document.getElementById('load-more');
    const loadMoreTasks = document.getElementById('load-more-tasks');

    loadMoreBtn?.addEventListener('click', () => this.loadMore(loadMoreBtn, 'trackers'));
    loadMoreTasks?.addEventListener('click', () => this.loadMore(loadMoreTasks, 'tasks'));
};

App.loadMore = async function (btn, type) {
    const page = parseInt(btn.dataset.page);
    this.setButtonLoading(btn, true);

    try {
        const response = await fetch(`${window.location.pathname}?page=${page}`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });

        const html = await response.text();
        const temp = document.createElement('div');
        temp.innerHTML = html;

        // Get items from response
        const container = type === 'trackers'
            ? document.getElementById('trackers-container')
            : document.getElementById('task-list');

        const newItems = temp.querySelectorAll(type === 'trackers' ? '.tracker-item' : '.task-row');
        newItems.forEach(item => container.appendChild(item));

        // Update button
        const newLoadMore = temp.querySelector(`#load-more${type === 'tasks' ? '-tasks' : ''}`);
        if (newLoadMore) {
            btn.dataset.page = newLoadMore.dataset.page;
        } else {
            btn.parentElement.remove();
        }

        // Rebind events
        this.bindPanelEvents();

    } catch (error) {
        this.showToast('error', 'Failed to load more');
    } finally {
        this.setButtonLoading(btn, false);
    }
};

// ============================================================================
// DATE PICKER
// ============================================================================
App.bindDatePicker = function () {
    const toggle = document.getElementById('date-picker-toggle');
    const popup = document.getElementById('date-picker-popup');

    if (!toggle || !popup) return;

    let currentDate = new Date();

    toggle.addEventListener('click', (e) => {
        e.stopPropagation();
        popup.style.display = popup.style.display === 'none' ? 'block' : 'none';
        this.renderDatePicker(currentDate);
    });

    document.addEventListener('click', (e) => {
        if (!popup.contains(e.target) && e.target !== toggle) {
            popup.style.display = 'none';
        }
    });

    document.getElementById('prev-month')?.addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() - 1);
        this.renderDatePicker(currentDate);
    });

    document.getElementById('next-month')?.addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() + 1);
        this.renderDatePicker(currentDate);
    });
};

App.renderDatePicker = function (date) {
    const monthYear = document.getElementById('current-month-year');
    const datesContainer = document.getElementById('date-picker-dates');

    if (!monthYear || !datesContainer) return;

    monthYear.textContent = date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    const year = date.getFullYear();
    const month = date.getMonth();
    const today = new Date();

    // First day of month
    const firstDay = new Date(year, month, 1);
    const startDay = firstDay.getDay();

    // Days in month
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    let html = '';

    // Empty cells before first day
    for (let i = 0; i < startDay; i++) {
        html += '<div class="date-picker-date"></div>';
    }

    // Days
    for (let day = 1; day <= daysInMonth; day++) {
        const d = new Date(year, month, day);
        const isToday = d.toDateString() === today.toDateString();
        const dateStr = d.toISOString().split('T')[0];

        html += `<div class="date-picker-date ${isToday ? 'today' : ''}" data-date="${dateStr}">${day}</div>`;
    }

    datesContainer.innerHTML = html;

    // Bind date clicks
    datesContainer.querySelectorAll('.date-picker-date[data-date]').forEach(el => {
        el.addEventListener('click', () => {
            const selectedDate = el.dataset.date;
            window.location.href = `/today/?date=${selectedDate}`;
        });
    });
};

// ============================================================================
// DAY NOTE
// ============================================================================
App.bindDayNote = function () {
    const textarea = document.getElementById('day-note');
    const saveBtn = document.getElementById('save-note');

    if (!textarea || !saveBtn) return;

    let saveTimeout;

    // Auto-save on typing (debounced)
    textarea.addEventListener('input', () => {
        clearTimeout(saveTimeout);
        saveTimeout = setTimeout(() => this.saveDayNote(textarea), 2000);
    });

    // Manual save
    saveBtn.addEventListener('click', () => {
        clearTimeout(saveTimeout);
        this.saveDayNote(textarea);
    });
};

App.saveDayNote = async function (textarea) {
    const date = textarea.dataset.date;
    const note = textarea.value;

    try {
        await fetch(`${this.config.apiBase}notes/${date}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify({ note })
        });

        this.showToast('success', 'Note saved', '', 2000);
    } catch (error) {
        this.showToast('error', 'Failed to save note');
    }
};

// ============================================================================
// INITIALIZE PANEL-SPECIFIC FEATURES
// ============================================================================
App.initPanelFeatures = function () {
    this.bindViewToggle();
    this.bindFilters();
    this.bindSort();
    this.bindFilterTabs();
    this.bindBulkSelection();
    this.bindContextMenu();
    this.bindDragDrop();
    this.bindQuickAdd();
    this.bindPagination();
    this.bindDatePicker();
    this.bindDayNote();
};

// Extend bindPanelEvents to include Phase 2 features
const originalBindPanelEvents = App.bindPanelEvents.bind(App);
App.bindPanelEvents = function () {
    originalBindPanelEvents();
    this.initPanelFeatures();
};
