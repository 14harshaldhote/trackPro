# Template Analysis - Panel HTML Files

This document provides a comprehensive analysis of all panel HTML templates, including:
- **Data Needed**: Context variables required from the backend
- **Data Accessing**: How data is accessed/displayed in the template
- **Interactive Elements**: Buttons, click events, links, and other UI interactions

---

## 1. `analytics.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `stats.completion_rate` | Number | Overall completion percentage |
| `stats.rate_change` | Float | Rate change vs previous period |
| `stats.total_completed` | Number | Total tasks completed |
| `stats.best_streak` | Number | Best streak count |
| `stats.avg_per_day` | Float | Average tasks per day |
| `trackers` | List | List of tracker objects for comparison |
| `forecast.message` | String | Forecast message |
| `forecast.days_analyzed` | Number | Days analyzed for forecast |

### Data Accessing
- Stats displayed in `.analytics-stat` cards
- Chart data loaded via partials: `chart_line.html`, `chart_pie.html`, `chart_bar.html`, `chart_heatmap.html`
- Insight banner loaded via `partials/insight_banner.html`
- Tracker list used in comparison dropdowns

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Time range buttons | Filter by 7D/30D/90D/1Y | `data-range="7/30/90/365"` |
| Export button | Export charts | `id="export-charts"` |
| Chart type toggle | Switch line/bar | `data-type="line/bar"` |
| Tracker comparison select | Compare trackers | `id="compare-tracker-1"`, `id="compare-tracker-2"` |
| Breadcrumb links | SPA navigation | `data-nav` |

---

## 2. `dashboard.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `time_of_day` | String | Morning/Afternoon/Evening |
| `user.first_name` | String | User's first name |
| `user.email` | String | User's email (fallback) |
| `today` | Date | Current date |
| `stats.completed_today` | Number | Tasks completed today |
| `stats.completion_rate` | Number | Today's completion rate |
| `stats.pending_today` | Number | Pending tasks count |
| `stats.current_streak` | Number | Current streak |
| `stats.active_trackers` | Number | Active trackers count |
| `today_tasks` | List | List of today's task objects |
| `active_trackers` | List | List of active tracker objects |

### Data Accessing
- Personalized greeting using `user.first_name` or `user.email`
- Stats displayed in `.stat-card` elements
- Task list with status, description, category, tracker_name
- Tracker cards with name, time_period, progress, completed_count, task_count

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| New Tracker button | Open modal | `data-action="open-modal"`, `data-modal="add-tracker"`, `data-modal-url="/modals/add_tracker/"` |
| Task toggle button | Toggle task status | `data-action="toggle"` |
| Task edit button | Edit task | `data-action="edit"` |
| Tracker cards | Navigate to tracker | `data-nav` |
| View All links | SPA navigation | `data-nav` |
| Quick Action: New Tracker | Open modal | `data-action="open-modal"`, `data-modal="add-tracker"` |
| Quick Action: Add Task | Open modal | `data-action="open-modal"`, `data-modal="add-task"` |
| Quick Action: Set Goal | Open modal | `data-action="open-modal"`, `data-modal="add-goal"` |
| Quick Action: Analytics | Navigate | `data-nav` |

---

## 3. `error_404.html`

### Data Needed
- **No backend data required** (static error page)

### Data Accessing
- Pure static HTML content

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Go to Dashboard button | SPA navigation | `data-nav` |
| Go Back button | Browser history | `onclick="history.back()"` |
| View all trackers link | SPA navigation | `data-nav` |
| Help center link | SPA navigation | `data-nav` |

---

## 4. `error_500.html`

### Data Needed
- **No backend data required** (static error page)

### Data Accessing
- Error ID generated client-side (random string)
- Timestamp generated client-side

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Refresh Page button | Page reload | `onclick="location.reload()"` |
| Go to Dashboard link | SPA navigation | `data-nav` |
| Show technical details button | Toggle details | `onclick="this.nextElementSibling.classList.toggle('show')"` |

---

## 5. `goals.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `active_goals` | List | List of active goal objects |
| `completed_goals` | List | List of completed goal objects |

### Goal Object Properties
| Property | Type | Description |
|----------|------|-------------|
| `id` | Number | Goal ID |
| `icon` | String/HTML | Goal icon (optional) |
| `name` | String | Goal name |
| `tracker_name` | String | Associated tracker name |
| `progress` | Number | Progress percentage |
| `target` | Number | Target value |
| `current` | Number | Current value |
| `unit` | String | Unit label |
| `days_left` | Number | Days remaining |
| `on_track` | Boolean | Is goal on track |
| `behind_by` | String | Amount behind pace |
| `completed_at` | DateTime | Completion timestamp |

### Data Accessing
- Goal cards display progress via `partials/goal_progress.html`
- Completed goals shown with celebration icon
- Uses Django's `timesince` filter for relative time

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| New Goal button | Open modal | `data-action="open-modal"`, `data-modal="add-goal"` |
| Goal context menu button | Open context menu | `data-action="context-menu"` |
| Breadcrumb links | SPA navigation | `data-nav` |
| Canvas | Confetti animation | `id="confetti-canvas"` |

---

## 6. `help.html`

### Data Needed
- **No backend data required** (static help content)

### Data Accessing
- Static FAQ content with `<details>` elements
- Keyboard shortcut reference

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Search input | Search help | `id="help-search"` |
| Quick links | Anchor navigation | `href="#getting-started"`, etc. |
| FAQ items | Expand/collapse | Native `<details>` behavior |
| View All Shortcuts link | SPA navigation | `data-nav` |
| Contact Support link | Email | `href="mailto:support@trackerpro.app"` |

---

## 7. `insights.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `primary_insight` | Object | Main insight to highlight |
| `insights` | Object | Various insight metrics |
| `patterns` | List | Behavioral pattern objects |
| `recommendations` | List | Recommendation objects |
| `comparison` | Object | Week comparison data |

### Insights Object Properties
| Property | Type | Description |
|----------|------|-------------|
| `best_day` | String | Best performing day name |
| `best_day_rate` | Number | Completion rate on best day |
| `best_time` | String | Peak productivity hours |
| `current_streak` | Number | Current streak |
| `longest_streak` | Number | Longest streak achieved |
| `consistency_score` | Number | 30-day consistency percentage |
| `top_category` | String | Most completed category |
| `top_category_count` | Number | Tasks in top category |
| `improvement_area` | String | Area needing improvement |
| `improvement_tip` | String | Improvement suggestion |

### Comparison Object Properties
| Property | Type | Description |
|----------|------|-------------|
| `last_week_tasks` | Number | Tasks completed last week |
| `last_week_tasks_pct` | Number | Last week bar percentage |
| `this_week_tasks` | Number | Tasks completed this week |
| `this_week_tasks_pct` | Number | This week bar percentage |
| `last_week_rate` | Number | Last week completion rate |
| `this_week_rate` | Number | This week completion rate |

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Primary insight action button | Navigate to action | `data-nav` |
| Breadcrumb links | SPA navigation | `data-nav` |

---

## 8. `month.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `current_month` | Date | Current viewing month |
| `prev_month` | Date | Previous month date |
| `next_month` | Date | Next month date |
| `is_current_month` | Boolean | Is viewing current month |
| `month_stats` | Object | Monthly statistics |
| `calendar_days` | List | Calendar day objects |
| `tracker_stats` | List | Tracker performance data |

### Month Stats Properties
| Property | Type | Description |
|----------|------|-------------|
| `completion_rate` | Number | Overall completion % |
| `total_tasks` | Number | Total tasks |
| `completed` | Number | Completed tasks |
| `longest_streak` | Number | Best streak |
| `active_days` | Number | Days with activity |

### Calendar Day Properties
| Property | Type | Description |
|----------|------|-------------|
| `date` | Date | The day's date |
| `in_month` | Boolean | Is in current month |
| `is_today` | Boolean | Is today |
| `is_future` | Boolean | Is future date |
| `total` | Number | Total tasks |
| `completed` | Number | Completed tasks |
| `progress` | Number | Progress percentage |

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Navigation arrows | Navigate months | `data-nav` |
| Month picker toggle | Open picker | `id="month-picker-toggle"` |
| Current Month button | Go to current | `data-nav` |
| Calendar day links | Go to day view | `data-nav` |
| Tracker breakdown links | Go to tracker | `data-nav` |
| Export Report button | Export | `id="export-month"` |

---

## 9. `offline.html`

### Data Needed
- **No backend data required** (offline state page)

### Data Accessing
- Static content with dynamic connection status

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Retry Connection button | Check connection | `id="retry-connection"` |

### JavaScript Events
- `click` on retry button → fetch `/api/auth/status/` → reload on success
- `online` window event → update UI and reload

---

## 10. `templates.html`

### Data Needed
- **Mostly static** (template library with hardcoded templates)

### Data Accessing
- Hardcoded template cards with category, name, description, task count, type

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Create Template button | Create template | `data-action="create-template"` |
| Category filter buttons | Filter by category | `data-category="all/health/productivity/learning/lifestyle"` |
| Use Template buttons | Use template | `data-action="use-template"`, `data-template="morning/fitness/study/work/mindfulness/evening/weekly-review/language"` |

---

## 11. `today.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `today` | Date | Current viewing date |
| `prev_day` | Date | Previous day date |
| `next_day` | Date | Next day date |
| `is_today` | Boolean | Is viewing today |
| `completed_count` | Number | Completed tasks |
| `pending_count` | Number | Pending tasks |
| `missed_count` | Number | Missed tasks |
| `total_count` | Number | Total tasks |
| `progress` | Number | Progress percentage |
| `task_groups` | List | Tasks grouped by tracker |
| `day_note` | String | Note for the day |

### Task Group Properties
| Property | Type | Description |
|----------|------|-------------|
| `tracker.id` | Number | Tracker ID |
| `tracker.name` | String | Tracker name |
| `completed` | Number | Completed in group |
| `total` | Number | Total in group |
| `tasks` | List | Task objects |

### Task Properties
| Property | Type | Description |
|----------|------|-------------|
| `id` | Number | Task ID |
| `status` | String | DONE/PENDING/MISSED |
| `description` | String | Task description |
| `category` | String | Task category |

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Navigation arrows | Navigate days | `data-nav` |
| Date picker toggle | Open picker | `id="date-picker-toggle"` |
| Go to Today button | Go to today | `data-nav` |
| Filter tabs | Filter tasks | `data-filter="all/pending/done/missed"` |
| Task toggle button | Toggle status | `data-action="toggle"` |
| Task edit button | Edit task | `data-action="edit"` |
| Group title links | Go to tracker | `data-nav` |
| Day note textarea | Input note | `id="day-note"` |
| Save Note button | Save note | `id="save-note"` |
| Date picker navigation | Change month | `id="prev-month"`, `id="next-month"` |

---

## 12. `tracker_detail.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `tracker` | Object | Tracker details |
| `tasks` | List | Task objects |
| `completed_count` | Number | Completed tasks |
| `task_count` | Number | Total tasks |
| `pending_count` | Number | Pending tasks |
| `progress` | Number | Progress percentage |
| `has_more_tasks` | Boolean | Has pagination |
| `next_page` | Number | Next page number |

### Tracker Properties
| Property | Type | Description |
|----------|------|-------------|
| `id` | Number | Tracker ID |
| `name` | String | Tracker name |
| `description` | String | Tracker description |

### Task Properties
| Property | Type | Description |
|----------|------|-------------|
| `id` | Number | Task ID |
| `status` | String | DONE/PENDING |
| `description` | String | Task description |
| `category` | String | Category (optional) |
| `weight` | Number | Task weight |
| `time_of_day` | String | Time of day |

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Settings button | Open edit modal | `data-action="open-modal"`, `data-modal-url="/modal/tracker/{id}/edit/"` |
| Add Task button | Open add modal | `data-action="open-modal"`, `data-modal="add-task"` |
| Select All checkbox | Select all tasks | `id="select-all"` |
| Filter tabs | Filter tasks | `data-filter="all/pending/done"` |
| Group dropdown | Group by | `data-group="none/category/time"` |
| Bulk action buttons | Bulk operations | `data-bulk-action="complete/skip/move/delete"` |
| Cancel selection button | Cancel bulk | `id="bulk-cancel"` |
| Drag handle | Reorder tasks | `.drag-handle` |
| Bulk select checkbox | Select task | `.bulk-select` |
| Task toggle button | Toggle status | `data-action="toggle"` |
| Task edit button | Edit task | `data-action="edit"` |
| Task context menu button | Open menu | `data-action="context-menu"` |
| Quick add input | Quick task input | `id="quick-task-input"` |
| Quick add button | Add task | `id="quick-add-btn"` |
| Load More button | Pagination | `id="load-more-tasks"` |
| Context menu actions | Task actions | `data-action="complete/skip/edit/duplicate/delete"` |
| Breadcrumb links | SPA navigation | `data-nav` |

---

## 13. `trackers_list.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `trackers` | List | Tracker objects |
| `has_more` | Boolean | Has pagination |
| `next_page` | Number | Next page number |
| `total_count` | Number | Total trackers |

### Tracker Properties
| Property | Type | Description |
|----------|------|-------------|
| `id` | Number | Tracker ID |
| `name` | String | Tracker name |
| `description` | String | Description |
| `status` | String | active/paused/completed |
| `progress` | Number | Progress percentage |
| `time_period` | String | daily/weekly/monthly |
| `task_count` | Number | Task count |
| `updated_at` | DateTime | Last update time |

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| New Tracker button | Open modal | `data-action="open-modal"`, `data-modal="add-tracker"` |
| View toggle buttons | Switch grid/list | `data-view="grid/list"` |
| Filter checkboxes | Filter by status/period | `name="filter-status/filter-period"` |
| Clear Filters button | Reset filters | `id="clear-filters"` |
| Sort dropdown items | Sort trackers | `data-sort="recent/name/progress/tasks"` |
| Search input | Search trackers | `id="tracker-search"` |
| Tracker card links | Go to tracker | `data-nav` |
| Context menu button | Open menu | `data-action="context-menu"` |
| Load More button | Pagination | `id="load-more"` |
| Context menu actions | Tracker actions | `data-action="edit/duplicate/archive/delete"` |
| Breadcrumb links | SPA navigation | `data-nav` |

---

## 14. `week.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `week_start` | Date | Week start date |
| `week_end` | Date | Week end date |
| `prev_week` | Date | Previous week date |
| `next_week` | Date | Next week date |
| `week_number` | Number | Week number |
| `is_current_week` | Boolean | Is current week |
| `week_stats` | Object | Weekly statistics |
| `days` | List | Day objects |
| `today` | Date | Today's date |

### Week Stats Properties
| Property | Type | Description |
|----------|------|-------------|
| `completed` | Number | Tasks completed |
| `completion_rate` | Number | Completion percentage |
| `best_day` | String | Best performing day |
| `streak` | Number | Current streak |

### Day Properties
| Property | Type | Description |
|----------|------|-------------|
| `date` | Date | The day's date |
| `is_today` | Boolean | Is today |
| `progress` | Number | Progress percentage |
| `completed` | Number | Completed tasks |
| `total` | Number | Total tasks |
| `tasks` | List | Task objects |
| `morning_rate` | Number | Morning completion rate |
| `morning_completed` | Number | Morning completed |
| `morning_total` | Number | Morning total |
| `afternoon_rate` | Number | Afternoon completion rate |
| `afternoon_completed` | Number | Afternoon completed |
| `afternoon_total` | Number | Afternoon total |
| `evening_rate` | Number | Evening completion rate |
| `evening_completed` | Number | Evening completed |
| `evening_total` | Number | Evening total |

### Task Properties (within day)
| Property | Type | Description |
|----------|------|-------------|
| `id` | Number | Task ID |
| `status` | String | DONE/PENDING |
| `description` | String | Task description |

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Navigation arrows | Navigate weeks | `data-nav` |
| Week picker toggle | Open picker | `id="week-picker-toggle"` |
| Current Week button | Go to current | `data-nav` |
| Week task items | Show tooltip | `title="{{ task.description }}"` |
| "View Day" links | Go to day view | `data-nav` |
| "+X more" links | Go to day view | `data-nav` |

---

## Summary: Common Patterns

### Navigation Pattern
All panels use `data-nav` attribute for SPA-style navigation without full page reload.

### Modal Pattern
Modal triggers use:
- `data-action="open-modal"` - Identifies modal trigger
- `data-modal="modal-name"` - Modal identifier
- `data-modal-url="/path/"` - Optional URL for modal content

### Context Menu Pattern
Context menus use:
- `data-action="context-menu"` - Opens context menu
- Individual actions use `data-action="edit/delete/duplicate/etc."`

### Filter/Sort Pattern
- Filter tabs use `data-filter="value"`
- Sort options use `data-sort="value"`
- View toggles use `data-view="value"`

### Task Interaction Pattern
- Toggle status: `data-action="toggle"`
- Edit: `data-action="edit"`
- Task ID stored in `data-task-id`
- Status stored in `data-status`

---

# Settings Templates

## 15. `settings/general.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `user.first_name` | String | User's first name |
| `user.last_name` | String | User's last name |
| `user.email` | String | User's email |
| `user.avatar_url` | String | Avatar URL (optional) |

### Data Accessing
- Form inputs pre-filled with `{{ user.first_name }}`, `{{ user.last_name }}`, `{{ user.email }}`
- Avatar image uses default fallback: `/static/core/images/default-avatar.svg`
- Includes inline `_sidebar.html` for settings navigation

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Upload Photo button | Trigger file input | `id="upload-avatar"` |
| Remove Avatar button | Remove avatar | `id="remove-avatar"` |
| Avatar file input | File upload | `id="avatar-input"` |
| First/Last name inputs | Text input | `name="first_name"`, `name="last_name"` |
| Email input | Email input | `name="email"` |
| Timezone select | Select timezone | `name="timezone"` |
| Date Format select | Select format | `name="date_format"` |
| Week Start select | Select start day | `name="week_start"` |
| Save Changes button | Form submit | `type="submit"` |
| Settings nav links | SPA navigation | `data-nav` |

---

## 16. `settings/preferences.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `themes` | List | Available theme objects |
| `current_theme` | String | Current theme ID |

### Theme Object Properties
| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Theme identifier |
| `name` | String | Display name |
| `bg` | String | Background color |
| `primary` | String | Primary color |

### Data Accessing
- Theme grid iterates over `themes` list
- Radio button checked based on `theme.id == current_theme`

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Theme radio buttons | Select theme | `name="theme"`, `value="{{ theme.id }}"` |
| Completion Sound toggle | Toggle setting | `name="sound_complete"` |
| Notification Sound toggle | Toggle setting | `name="sound_notify"` |
| Volume slider | Adjust volume | `name="sound_volume"` |
| Push Notifications toggle | Enable push | `name="push_enabled"`, `id="push-toggle"` |
| Daily Reminders toggle | Toggle reminder | `name="daily_reminder"` |
| Weekly Summary toggle | Toggle summary | `name="weekly_summary"` |
| Compact Mode toggle | Toggle layout | `name="compact_mode"` |
| Animations toggle | Toggle animations | `name="animations"` |
| Save Preferences button | Form submit | `type="submit"` |

---

## 17. `settings/keyboard.html`

### Data Needed
- **No backend data required** (static keyboard shortcut reference)

### Data Accessing
- Static list of keyboard shortcuts organized by category

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Enable Shortcuts toggle | Toggle shortcuts | `name="keyboard_enabled"` |
| Settings nav links | SPA navigation | `data-nav` |

### Shortcut Categories Displayed
- **Navigation**: G+D (Dashboard), G+T (Today), G+L (Trackers), G+S (Settings)
- **Actions**: N (New Tracker), A (Quick Add Task), / or ⌘K (Search), Space (Toggle Task)
- **Selection**: ⌘A (Select All), Esc (Deselect), ↑/↓ (Move)
- **Interface**: ? (Show Shortcuts), [ (Toggle Sidebar), Esc (Close Modal)

---

## 18. `settings/data.html`

### Data Needed
- **No backend data required** (static data management page)

### Data Accessing
- Static content for export/import options

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Export JSON button | Export data | `data-export="json"` |
| Export CSV button | Export data | `data-export="csv"` |
| Import drop zone | File drop area | `id="import-zone"` |
| Browse button | Trigger file input | `.btn-link` |
| Import file input | File upload | `id="import-input"` |
| Clear Data button | Clear all data | `data-action="clear-data"` |
| Delete Account button | Delete account | `data-action="delete-account"` |
| Settings nav links | SPA navigation | `data-nav` |

---

## 19. `settings/about.html`

### Data Needed
- **No backend data required** (static about page)

### Data Accessing
- Static version info, changelog, credits, and links

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Help Center link | SPA navigation | `data-nav` |
| Contact Support link | Email | `href="mailto:support@trackerpro.app"` |
| Privacy Policy link | SPA navigation | `data-nav` |
| Terms of Service link | SPA navigation | `data-nav` |

---

## 20. `settings/_sidebar.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `active` | String | Current active tab (general/preferences/keyboard/data/about) |

### Data Accessing
- Conditionally adds `active` class based on `{% if active == 'section' %}`

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| General link | Navigate | `data-nav`, `href="/settings/"` |
| Preferences link | Navigate | `data-nav`, `href="/settings/preferences/"` |
| Keyboard link | Navigate | `data-nav`, `href="/settings/keyboard/"` |
| Data link | Navigate | `data-nav`, `href="/settings/data/"` |
| About link | Navigate | `data-nav`, `href="/settings/about/"` |

---

# Partials Templates

## 21. `partials/onboarding.html`

### Data Needed
- **No backend data required** (static onboarding flow)

### Data Accessing
- Static 4-step onboarding wizard with hardcoded content

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Progress dots | Show step | `data-step="1/2/3/4"` |
| Skip button | Skip onboarding | `id="skip-onboarding"` |
| Back button | Previous step | `id="prev-step"` |
| Next button | Next step/Finish | `id="next-step"` |

---

## 22. `partials/insight_banner.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `insight` | Object | Insight to display |
| `insight.type` | String | success/warning/info |
| `insight.label` | String | Banner label (default: "Insight") |
| `insight.message` | String | Banner message |

### Data Accessing
- Only renders if `{% if insight %}` is truthy
- Icon changes based on `insight.type`

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Dismiss button | Close banner | `.insight-banner-dismiss` |

---

## 23. `partials/goal_progress.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `progress` | Number | Progress percentage (0-100) |
| `offset` | Number | SVG stroke-dashoffset (default: 264) |

### Data Accessing
- SVG circle progress ring with CSS variable `--progress`
- Shows celebration emoji when `progress >= 100`

### Interactive Elements
- **No interactive elements** (display-only component)

---

## 24. `partials/empty_trackers.html`

### Data Needed
- **No backend data required** (static empty state)

### Data Accessing
- Static empty state with illustration and suggestions

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Create Tracker button | Open modal | `data-action="open-modal"`, `data-modal="add-tracker"` |
| Morning Routine chip | Use template | `data-template="morning-routine"` |
| Fitness chip | Use template | `data-template="fitness"` |
| Learning chip | Use template | `data-template="learning"` |

---

## 25. `partials/empty_tasks.html`

### Data Needed
- **No backend data required** (static empty state)

### Data Accessing
- Static "All caught up" message

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Add Task button | Quick add task | `data-action="quick-add"` |

---

## 26. `partials/empty_search.html`

### Data Needed
- **No backend data required** (static empty state)

### Data Accessing
- Static "No results found" message

### Interactive Elements
- **No interactive elements** (display-only component)

---

## 27. `partials/chart_pie.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `chart_id` | String | Unique chart canvas ID |

### Data Accessing
- Canvas element for Chart.js pie chart
- Legend container with ID `{{ chart_id }}-legend`

### Interactive Elements
- **Chart initialized via JavaScript** (Canvas element `id="{{ chart_id }}"`)

---

## 28. `partials/chart_line.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `chart_id` | String | Unique chart canvas ID |
| `multi` | Boolean | Multi-dataset chart flag |

### Data Accessing
- Canvas for Chart.js line chart
- Optional `data-multi="true"` attribute
- Tooltip container for hover data

### Interactive Elements
- **Chart initialized via JavaScript** (Canvas element `id="{{ chart_id }}"`)
- Tooltip element: `id="{{ chart_id }}-tooltip"`

---

## 29. `partials/chart_heatmap.html`

### Data Needed
- **Data loaded via JavaScript** (no Django context variables)

### Data Accessing
- Static grid structure with day/month labels
- Heatmap cells generated by JavaScript

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Heatmap grid | JS-generated cells | `id="heatmap-grid"` |
| Legend cells | Color scale | `data-level="0/1/2/3/4"` |
| Tooltip | Cell hover | `id="heatmap-tooltip"` |

---

## 30. `partials/chart_bar.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `chart_id` | String | Unique chart canvas ID |

### Data Accessing
- Canvas element for Chart.js bar chart

### Interactive Elements
- **Chart initialized via JavaScript** (Canvas element `id="{{ chart_id }}"`)

---

# Modals Templates

## 31. `modals/add_tracker.html`

### Data Needed
- **No backend data required** (form modal)

### Data Accessing
- Static form with template options

### Form Fields
| Field | Type | Name | Description |
|-------|------|------|-------------|
| Name | text | `name` | Tracker name (required, max 100) |
| Description | textarea | `description` | Tracker description |
| Time Period | select | `time_period` | daily/weekly/monthly/custom |
| Template | radio | `template` | blank/productivity/wellbeing/fitness/study |

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Close button | Close modal | `data-action="close-modal"` |
| Cancel button | Close modal | `data-action="close-modal"` |
| Create Tracker button | Submit form | `type="submit"`, `id="create-tracker-btn"` |
| Form | AJAX submit | `data-ajax`, `action="/api/trackers/create/"` |

---

## 32. `modals/add_task.html`

### Data Needed
- **No backend data required** (form modal)
- `tracker_id` passed via hidden input (set by JS)

### Form Fields
| Field | Type | Name | Description |
|-------|------|------|-------------|
| Tracker ID | hidden | `tracker_id` | Parent tracker |
| Description | text | `description` | Task description (required, max 200) |
| Category | text + datalist | `category` | Category with suggestions |
| Weight | radio | `weight` | 1 (Low) / 2 (Medium) / 3 (High) / 5 (Critical) |
| Recurring | checkbox | `is_recurring` | Repeat daily |
| Time of Day | select | `time_of_day` | Any/Morning/Afternoon/Evening/Night |
| Goal ID | select | `goal_id` | Link to goal (populated via JS) |

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Close button | Close modal | `data-action="close-modal"` |
| Cancel button | Close modal | `data-action="close-modal"` |
| Add Task button | Submit form | `type="submit"`, `id="create-task-btn"` |
| Form | AJAX submit | `data-ajax` |

### JavaScript Events
- Extensive debug logging for form state
- Field change logging for all inputs
- Form submit handler with FormData logging

---

## 33. `modals/add_goal.html`

### Data Needed
- **No backend data required** (form modal)

### Form Fields
| Field | Type | Name | Description |
|-------|------|------|-------------|
| Title | text | `title` | Goal title (required, max 100) |
| Description | textarea | `description` | Goal description |
| Target Date | date | `target_date` | Target completion date (required) |
| Goal Type | select | `goal_type` | habit/achievement/project |

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Close button | Close modal | `data-action="close-modal"` |
| Cancel button | Close modal | `data-action="close-modal"` |
| Set Goal button | Submit form | `type="submit"`, `id="create-goal-btn"` |
| Form | AJAX submit | `data-ajax` |

---

## 34. `modals/bulk_edit.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `trackers` | List | List of trackers for move dropdown |
| (JS) `window.bulkEditTaskIds` | Array | Selected task IDs |

### Form Fields
| Field | Type | Name | Description |
|-------|------|------|-------------|
| Status | select | `status` | PENDING/DONE/SKIPPED |
| Category | text | `category` | New category |
| Move to Tracker | select | `tracker_id` | Target tracker |
| Weight | number | `weight` | New weight (1-10) |
| Time of Day | select | `time_of_day` | morning/afternoon/evening/anytime |
| Task IDs | hidden | `task_ids` | Comma-separated IDs |

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Close button | Close modal | `data-action="close-modal"` |
| Cancel button | Close modal | `data-action="close-modal"` |
| Apply Changes button | Bulk update | `id="bulk-save-btn"` |

### JavaScript Events
- Fetches to `/api/tasks/bulk-edit/`
- Uses `App.showToast()` for feedback
- Reloads panel on success

---

## 35. `modals/confirm_delete.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| (JS) `window.deleteConfig.url` | String | DELETE API endpoint |
| (JS) `window.deleteConfig.onSuccess` | Function | Success callback |

### Data Accessing
- Static confirmation message
- URL and callback passed via JavaScript

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Close button | Close modal | `data-action="close-modal"` |
| Cancel button | Close modal | `data-action="close-modal"` |
| Delete button | Confirm delete | `id="confirm-delete-btn"` |

### JavaScript Events
- DELETE request to `window.deleteConfig.url`
- Shows toast on success/error
- Calls `onSuccess` callback or redirects

---

## 36. `modals/export_data.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `tracker_id` | String | Tracker to export |

### Form Fields
| Field | Type | Name | Description |
|-------|------|------|-------------|
| Format | radio | `format` | csv/json/pdf |
| Start Date | date | `start_date` | Export from date |
| End Date | date | `end_date` | Export to date |
| Include Tasks | checkbox | `include_tasks` | Include tasks |
| Include Notes | checkbox | `include_notes` | Include notes |
| Include Stats | checkbox | `include_stats` | Include statistics |

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Close button | Close modal | `data-action="close-modal"` |
| Quick range buttons | Set date range | `data-range="7/30/all"` |
| Cancel button | Close modal | `data-action="close-modal"` |
| Download Export button | Trigger download | `id="export-btn"` |

### JavaScript Events
- Quick range buttons set form dates
- Downloads via redirect to `/api/tracker/${trackerId}/export/?${params}`

---

## 37. `modals/image_preview.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `image_url` | String | Image URL to preview |
| `image_title` | String | Image title (default: "Image") |

### Data Accessing
- Image displayed in container with zoom controls

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Download link | Download image | `href="{{ image_url }}"`, `download` |
| Close button | Close modal | `data-action="close-modal"` |
| Zoom Out button | Decrease zoom | `id="zoom-out"` |
| Zoom In button | Increase zoom | `id="zoom-in"` |
| Reset button | Reset zoom | `id="zoom-reset"` |
| Zoom level display | Show percentage | `id="zoom-level"` |

### JavaScript Events
- Zoom buttons adjust image scale (0.25-3x)
- Mouse wheel zoom on image
- Displays zoom percentage

---

## 38. `modals/keyboard_shortcuts.html`

### Data Needed
- **No backend data required** (static shortcut reference)

### Data Accessing
- Static list organized by category

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Close button | Close modal | `data-action="close-modal"` |
| Got it! button | Close modal | `data-action="close-modal"` |

---

## 39. `modals/share_tracker.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `tracker_id` | String | Tracker ID to share |

### Form Fields
| Field | Type | Name | Description |
|-------|------|------|-------------|
| Email | email | `email` | Recipient email |
| Permission | select | `permission` | view/edit |

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Close button | Close modal | `data-action="close-modal"` |
| Share URL input | Display/copy | `id="share-url"` |
| Copy Link button | Copy to clipboard | `id="copy-link"` |
| Send Invitation button | Submit email form | Form submit |
| Done button | Close modal | `data-action="close-modal"` |

### JavaScript Events
- Fetches share URL from `/api/tracker/${trackerId}/share/`
- Copy button uses `navigator.clipboard.writeText()`
- Shows "Copied!" confirmation

---

# Components Templates

## 40. `components/_toast.html`

### Data Needed
- **Template cloned by JavaScript** (no Django context)

### Data Accessing
- Template element cloned for each notification
- Icon templates for success/error/warning/info

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Toast close button | Dismiss toast | `data-action="close-toast"` |
| Toast progress bar | Auto-dismiss timer | `.toast-progress` |

### Template IDs
- `toast-template` - Main toast structure
- `toast-icon-success` - Green checkmark
- `toast-icon-error` - Red X
- `toast-icon-warning` - Yellow triangle
- `toast-icon-info` - Blue info circle

---

## 41. `components/_sidebar.html`

### Data Needed
- **No backend data required** (static navigation)

### Data Accessing
- Static navigation structure
- Theme options in sidebar footer

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Dashboard link | Navigate | `data-nav`, `data-panel="dashboard"` |
| My Trackers link | Navigate | `data-nav`, `data-panel="trackers"` |
| New Tracker button | Open modal | `data-action="open-modal"`, `data-modal="add-tracker"` |
| Goals link | Navigate | `data-nav`, `data-panel="goals"` |
| Analytics link | Navigate | `data-nav`, `data-panel="analytics"` |
| Insights link | Navigate | `data-nav`, `data-panel="insights"` |
| Templates link | Navigate | `data-nav`, `data-panel="templates"` |
| Settings link | Navigate | `data-nav`, `data-panel="settings"` |
| Help link | Navigate | `data-nav`, `data-panel="help"` |
| Theme switcher select | Quick theme change | `id="theme-switcher-sidebar"` |
| Sidebar overlay | Close sidebar (mobile) | `data-action="close-sidebar"` |

---

## 42. `components/_modal.html`

### Data Needed
- **Base template for dynamic content** (no Django context)

### Data Accessing
- Structure template with placeholder content
- Modal body populated dynamically

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Close button | Close modal | `data-action="close-modal"` |
| Cancel button | Close modal | `data-action="close-modal"` |
| Confirm button | Confirm action | `id="modal-confirm"` |

### Element IDs for JS
- `modal-title` - Title text
- `modal-body` - Content container
- `modal-footer` - Footer with buttons
- `modal-confirm` - Primary action button

---

## 43. `components/_loading.html`

### Data Needed
- **No backend data required** (static loading states)

### Data Accessing
- Skeleton loading placeholders for common UI patterns

### Interactive Elements
- **No interactive elements** (display-only component)

### Templates/Elements
| Element | Purpose |
|---------|---------|
| `.loading-state` | Main loading container |
| `.loading-header` | Header skeleton |
| `.loading-stats` | Stats grid skeleton |
| `.loading-content` | List item skeletons |
| `#btn-loading-template` | Button loading state template |
| `#content-loading-overlay` | Full content overlay |

---

## 44. `components/_header.html`

### Data Needed
| Variable | Type | Description |
|----------|------|-------------|
| `user.is_authenticated` | Boolean | Auth status |
| `user.email` | String | User email (for avatar initial) |

### Data Accessing
- User avatar shows first letter of email: `{{ user.email|slice:":1"|upper }}`
- User menu only shown if authenticated

### Interactive Elements
| Element | Action | Data Attribute |
|---------|--------|----------------|
| Sidebar toggle | Toggle sidebar | `id="sidebar-toggle"` |
| Brand link | Go to dashboard | `data-nav` |
| Global search input | Search | `id="global-search"` |
| Shortcuts button | Show shortcuts | `id="shortcuts-btn"` |
| Notifications button | Toggle dropdown | `id="notifications-btn"` |
| Notification badge | Show count | `id="notification-count"` |
| Mark all read button | Clear notifications | `id="mark-all-read"` |
| Theme dropdown items | Change theme | `data-theme="theme-name"` |
| View All Themes link | Open modal | `data-action="open-modal"`, `data-modal="theme-gallery"` |
| Settings link (user menu) | Navigate | `data-nav` |
| Help link (user menu) | Navigate | `data-nav` |
| Logout button | Logout | `data-action="logout"` |

### Dropdown IDs
- `notifications-dropdown` - Notifications panel container
- `theme-dropdown` - Theme selection dropdown
- `user-dropdown` - User account menu

---

# Summary: Template Categories Overview

## Templates by Category

| Category | Count | Files |
|----------|-------|-------|
| Panels | 14 | analytics, dashboard, error_404, error_500, goals, help, insights, month, offline, templates, today, tracker_detail, trackers_list, week |
| Settings | 6 | general, preferences, keyboard, data, about, _sidebar |
| Partials | 10 | onboarding, insight_banner, goal_progress, empty_trackers, empty_tasks, empty_search, chart_pie, chart_line, chart_heatmap, chart_bar |
| Modals | 9 | add_tracker, add_task, add_goal, bulk_edit, confirm_delete, export_data, image_preview, keyboard_shortcuts, share_tracker |
| Components | 5 | _toast, _sidebar, _modal, _loading, _header |

## Common Data Patterns by Template Type

### Panels
- Receive full context data from Django views
- Complex nested objects (stats, lists, pagination)
- Date navigation patterns (prev/next)

### Settings
- User profile data (`user` object)
- Preferences stored in user settings
- Simple form submissions

### Partials
- Single-purpose display components
- Minimal data requirements (1-3 variables)
- Often included via `{% include %}`

### Modals
- Form-based with AJAX submission
- Tracker/task IDs passed via context or JavaScript
- Confirmation dialogs with callbacks

### Components
- Layout and UI infrastructure
- User authentication state
- Navigation and theme handling
