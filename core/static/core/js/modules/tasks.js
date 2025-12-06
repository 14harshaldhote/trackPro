/**
 * Tasks Module
 * Handles task interactions: toggling, edit, delete, adding.
 * Implements "Optimistic UI" for instant feedback.
 */
import { api } from './api.js';
import { ui } from './ui.js';

export class TaskManager {
    constructor() {
        this.init();
    }

    init() {
        // Delegate task clicks to document (for dynamically loaded panels)
        document.addEventListener('click', (e) => {
            // Toggle Status (Checkbox)
            const checkbox = e.target.closest('input[type="checkbox"][data-task-id]');
            if (checkbox) {
                this.handleTaskToggle(checkbox);
                return;
            }

            // Delete Task
            const deleteBtn = e.target.closest('[data-action="delete-task"]');
            if (deleteBtn) {
                const taskId = deleteBtn.dataset.taskId;
                this.deleteTask(taskId);
                return;
            }

            // Edit Task (click on task text)
            const taskText = e.target.closest('.task-content');
            if (taskText) {
                // Open edit modal
            }
        });

        // Expose global functions for backward compatibility with templates
        window.toggleTask = this.toggleTaskById.bind(this);

        console.log('[TaskManager] Initialized');
    }

    // Global function for templates: toggleTask(taskId)
    async toggleTaskById(taskId) {
        console.log(`[Tasks] ⚡️ toggleTask called for ${taskId}`);

        // Find the task item
        const taskItem = document.querySelector(`[data-task-id="${taskId}"]`);
        if (!taskItem) {
            console.warn(`[Tasks] Task item not found for ${taskId}`);
        }

        try {
            const response = await api.post(`/api/task/${taskId}/toggle/`);
            console.log(`[Tasks] ✅ Task ${taskId} toggled, new status:`, response.data?.status);

            // Update UI based on new status
            if (taskItem && response.data) {
                const newStatus = response.data.status;
                const isDone = newStatus === 'DONE';

                // Update checkbox (if exists - used in tracker detail page)
                const checkbox = taskItem.querySelector('input[type="checkbox"]');
                if (checkbox) {
                    checkbox.checked = isDone;
                }

                // Update button (if exists - used in today page)
                const button = taskItem.querySelector('button');
                if (button && !checkbox) {
                    // Update button classes
                    if (isDone) {
                        button.classList.add('bg-success', 'border-success', 'text-white');
                        button.classList.remove('border-border', 'hover:border-primary');
                        // Add checkmark if not present
                        if (!button.querySelector('svg')) {
                            button.innerHTML = `
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="4">
                                    <polyline points="20 6 9 17 4 12"></polyline>
                                </svg>
                            `;
                        }
                    } else {
                        button.classList.remove('bg-success', 'border-success', 'text-white');
                        button.classList.add('border-border', 'hover:border-primary');
                        button.innerHTML = '';
                    }
                }

                // Update text styling
                const taskText = taskItem.querySelector('.font-medium, .task-content');
                if (taskText) {
                    if (isDone) {
                        taskText.classList.add('line-through', 'text-secondary');
                    } else {
                        taskText.classList.remove('line-through', 'text-secondary');
                    }
                }

                // Toggle completed class on task item
                if (isDone) {
                    taskItem.classList.add('completed');
                } else {
                    taskItem.classList.remove('completed');
                }
            }

            if (response.message) {
                ui.showToast(response.message, 'success');
            }
            return response;
        } catch (error) {
            console.error(`[Tasks] ❌ toggleTask failed:`, error);
            ui.showToast('Failed to update task', 'error');
            throw error;
        }
    }

    async handleTaskToggle(checkbox) {
        const taskId = checkbox.dataset.taskId;
        const taskItem = checkbox.closest('.task-item');
        const label = taskItem?.querySelector('.task-label');

        console.log(`[Tasks] ⚡️ Toggling task ${taskId} (Optimistic Update)`);

        // Optimistic Update
        const originalState = !checkbox.checked; // previous state
        const newState = checkbox.checked;

        // Visual update immediately
        if (taskItem) {
            taskItem.classList.toggle('completed', newState);
            if (newState) {
                ui.createConfetti(checkbox);
            }
        }

        if (label) {
            label.classList.toggle('line-through', newState);
            label.classList.toggle('text-muted', newState);
        }

        try {
            console.log(`[Tasks] Syncing state for task ${taskId} with server...`);
            const response = await api.post(`/api/task/${taskId}/toggle/`);

            console.log(`[Tasks] ✅ Sync complete for task ${taskId}`);
            if (response.data && response.feedback) {
                ui.showToast(response.message, 'success');
            }

        } catch (error) {
            console.error(`[Tasks] ❌ Toggle failed for task ${taskId}:`, error);
            console.log(`[Tasks] Reverting optimistic update for task ${taskId}`);
            checkbox.checked = originalState;
            if (taskItem) taskItem.classList.toggle('completed', originalState);
            ui.showToast('Failed to update task', 'error');
        }
    }

    async deleteTask(taskId) {
        if (!confirm('Are you sure you want to delete this task?')) return;

        console.log(`[Tasks] 🗑 Attempting to delete task ${taskId}`);
        try {
            await api.post(`/api/task/${taskId}/delete/`);
            console.log(`[Tasks] ✅ Task ${taskId} deleted`);
            const taskEl = document.querySelector(`[data-task-id="${taskId}"]`)?.closest('.task-item');
            if (taskEl) {
                taskEl.remove();
            }
            ui.showToast('Task deleted', 'success');
        } catch (error) {
            console.error(`[Tasks] ❌ Failed to delete task ${taskId}:`, error);
            ui.showToast('Failed to delete task', 'error');
        }
    }
}

export const tasks = new TaskManager();
