# Jinja2 Template Documentation - Tracker Pro

> **Framework**: Django with Jinja2 Templates  
> **Architecture**: Single Page Application (SPA) with AJAX Panel Loading  
> **Date**: 2025-12-06

---

## Table of Contents

1. [Template Folder Structure](#template-folder-structure)
2. [Base Template](#base-template)
3. [Panel Templates](#panel-templates)
4. [Modal Templates](#modal-templates)
5. [Settings Templates](#settings-templates)
6. [Auth Templates](#auth-templates)
7. [Error Templates](#error-templates)
8. [Django URL Patterns vs AJAX](#django-url-patterns-vs-ajax)

---

## Template Folder Structure

```
core/templates/
├── base.html                    # Main SPA shell with sidebar and header
├── components/                  # Reusable components
│   ├── header.html             # Horizontal header (logo, notifications, theme, profile)
│   ├── sidebar.html            # Vertical navigation panel
│   └── notifications_dropdown.html  # Notifications dropdown
├── panels/                      # Panel fragments loaded via AJAX
│   ├── dashboard.html          # Dashboard with filters and stats
│   ├── today.html              # Today's tasks view
│   ├── trackers_list.html      # All trackers list
│   ├── tracker_detail.html     # Single tracker detail
│   ├── week.html               # Week calendar view
│   ├── month.html              # Month calendar view
│   ├── analytics.html          # Analytics dashboard
│   ├── goals.html              # Goals panel
│   ├── insights.html           # Behavioral insights
│   ├── templates.html          # Template library
│   ├── help.html               # Help center
│   └── settings/               # Settings sub-panels
│       ├── preferences.html    # User preferences
│       ├── account.html        # Account settings
│       ├── notifications.html  # Notification settings
│       └── appearance.html     # Theme and appearance
├── modals/                     # Modal content fragments
│   ├── add_task.html          # Add task form
│   ├── edit_task.html         # Edit task form
│   ├── add_tracker.html       # Create tracker wizard
│   ├── edit_tracker.html      # Edit tracker form
│   ├── add_goal.html          # Create goal form
│   ├── tracker_templates.html # Template selection
│   ├── theme_gallery.html     # Theme picker
│   ├── quick_add.html         # Quick add modal
│   └── confirm_delete.html    # Confirmation dialog
├── auth/                       # Authentication pages
│   ├── login.html             # Login page (email + Google OAuth)
│   ├── signup.html            # Signup page (email + Google OAuth)
│   └── forgot_password.html   # Password reset
└── errors/                     # Error panels
    ├── 404.html               # Not found
    └── 500.html               # Server error
```

---

## Base Template

### `base.html`

**Django URL**: `/` or `/app/`  
**View**: `views_spa.spa_shell`  
**Purpose**: Main SPA shell with sidebar navigation

#### Context Data

```python
{
    'trackers': QuerySet[TrackerDefinition],  # User's trackers for sidebar
    'user': User,                             # Current authenticated user
    'unread_notifications_count': int,        # Badge count for notifications
    'current_theme': str,                     # Active theme name
    'keyboard_shortcuts': List[dict],         # Available keyboard shortcuts
}
```

#### Required Variables

- `trackers` - List/QuerySet of TrackerDefinition objects
  - `tracker_id` - UUID
  - `name` - Tracker name
  - `time_period` - 'daily', 'weekly', or 'monthly'
  - `status` - 'active', 'paused', 'completed', 'archived'

- `user` - User object
  - `email` - User email
  - `username` - Username
  - `first_name` - First name (optional)
  - `profile_image` - Profile image URL (optional)

- `unread_notifications_count` - Number of unread notifications
- `current_theme` - Active theme: 'light', 'dark', 'auto'
- `keyboard_shortcuts` - List of available keyboard shortcuts

#### Layout Structure

```html
<body>
  <!-- Horizontal Header -->
  <header class="app-header">
    <div class="header-left">
      <img src="logo.svg" alt="Tracker Pro" class="app-logo">
      <span class="app-name">Tracker Pro</span>
    </div>
    <div class="header-right">
      <button class="header-btn" id="notifications-btn">
        <i class="icon-bell"></i>
        <span class="badge">{{ unread_notifications_count }}</span>
      </button>
      <button class="header-btn" id="theme-btn">
        <i class="icon-theme"></i>
      </button>
      <button class="header-btn profile-btn" id="profile-btn">
        <img src="{{ user.profile_image }}" alt="{{ user.username }}">
      </button>
    </div>
  </header>

  <div class="app-layout">
    <!-- Vertical Navigation Sidebar -->
    <aside class="sidebar" id="sidebar">
      <nav class="sidebar-nav">
        <a href="/" class="nav-item" data-panel="dashboard">
          <i class="icon-home"></i>
          <span>Dashboard</span>
          <kbd>D</kbd>
        </a>
        <a href="/today/" class="nav-item" data-panel="today">
          <i class="icon-today"></i>
          <span>Today</span>
          <kbd>T</kbd>
        </a>
        <!-- More nav items... -->
      </nav>
      
      <!-- Trackers Section -->
      <div class="sidebar-section">
        <h3>Trackers</h3>
        {% for tracker in trackers %}
          <a href="/tracker/{{ tracker.tracker_id }}/" class="tracker-item">
            {{ tracker.name }}
          </a>
        {% endfor %}
      </div>
    </aside>

    <!-- Main Content Area -->
    <main id="main-content" class="main-content">
      <!-- AJAX-loaded panels go here -->
    </main>
  </div>

  <!-- Profile Dropdown (hidden by default) -->
  <div class="dropdown" id="profile-dropdown">
    <a href="/settings/" class="dropdown-item">
      <i class="icon-settings"></i>
      Settings
    </a>
    <button class="dropdown-item" data-action="logout">
      <i class="icon-logout"></i>
      Logout
    </button>
  </div>

  <!-- Modal Container -->
  <div id="modal-container"></div>
</body>
```

#### Features

- **Horizontal Header**:
  - Logo and app name (top-left)
  - Notifications button with badge count
  - Theme switcher button
  - Profile button with dropdown (Settings, Logout)

- **Vertical Sidebar**:
  - Navigation links with icons and keyboard shortcuts
  - Collapsible trackers section
  - Mobile-responsive (collapsible)

- **Main Content**:
  - AJAX-loaded panel area
  - Global modal container
  - Navigation state management

#### Keyboard Shortcuts

Display keyboard shortcuts next to navigation items:
- `D` - Dashboard
- `T` - Today
- `W` - Week
- `M` - Month
- `A` - Analytics
- `G` - Goals
- `Ctrl+K` or `Cmd+K` - Global search
- `Ctrl+N` or `Cmd+N` - New tracker
- `?` - Show all shortcuts

---

## Panel Templates

All panels are loaded via AJAX into the `#main-content` area of `base.html`.

### `panels/dashboard.html`

**Django URL**: `/panels/dashboard/`  
**View**: `views_spa.panel_dashboard`  
**AJAX**: Yes - supports `?period=daily|weekly|monthly|all` filter  
**Skeleton Support**: Yes - supports `?skeleton=true`

#### Context Data

```python
{
    'time_of_day': str,                      # 'morning', 'afternoon', 'evening'
    'today': date,                           # Current date
    'stats': {
        'completed_today': int,              # Completed tasks count
        'pending_today': int,                # Pending tasks count
        'current_streak': int,               # Current streak days
        'active_trackers': int,              # Active trackers count
        'completion_rate': int,              # Completion percentage
    },
    'today_tasks': List[dict],               # List of task dicts (max 50)
    'active_trackers': List[dict],           # Active trackers with stats (max 6)
    'current_period': str,                   # Current filter: 'daily', 'weekly', 'monthly', 'all'
    'period_title': str,                     # Display title: "Today's Tasks", "This Week's Tasks"
    
    # UX Enhancements
    'filter_state': {                        # For SPA state management
        'current_period': str,
        'available_periods': List[str],
        'start_date': str,                   # ISO format
        'end_date': str,                     # ISO format
    },
    'quick_stats': {                         # For header badges
        'tasks_today': int,
        'completed_today': int,
        'streak_days': int,
        'completion_pct': int,
    },
    'smart_suggestions': List[dict],         # Top 3 smart suggestions from insights engine
    'insights_widget': {
        'enabled': bool,
        'suggestions': List[dict],
        'cta_text': str,
        'cta_link': str,
    },
}
```

#### Task Object Structure

```python
{
    'id': UUID,                              # task_instance_id
    'status': str,                           # 'TODO', 'IN_PROGRESS', 'DONE', 'SKIPPED', 'MISSED', 'BLOCKED'
    'description': str,
    'category': str,
    'tracker_name': str,
    'tracker_id': UUID,
    'weight': int,
    'created_at': datetime,
    
    # iOS UX enhancements
    'ios_context_menu': List[dict],          # Long-press menu options
}
```

#### Usage

- **Django URL Pattern**: Use for initial page load
- **AJAX**: Use for filter changes (`?period=weekly`) to avoid full page reload
- **Skeleton**: Request skeleton first (`?skeleton=true`) then load actual data

---

### `panels/today.html`

**Django URL**: `/panels/today/`  
**View**: `views_spa.panel_today`  
**AJAX**: Supports `?date=YYYY-MM-DD` parameter  
**Skeleton Support**: Yes

#### Context Data

```python
{
    'today': date,                           # Current/selected date
    'task_groups': List[dict],               # Tasks grouped by tracker
    'is_today': bool,                        # True if viewing current day
    'prev_day': date,                        # Previous day date
    'next_day': date,                        # Next day date
    'total_count': int,                      # Total tasks
    'completed_count': int,                  # Completed tasks
    'pending_count': int,                    # Pending tasks
    'missed_count': int,                     # Missed/skipped tasks
    'progress': int,                         # Completion percentage
    'day_note': str,                         # Day note text (from DayNote model)
    
    # iOS UX enhancements
    'ios_swipe_actions': dict,               # Swipe action configs per task
    'touch_targets': dict,                   # Touch target constants (44pt minimum)
}
```

#### Task Group Structure

```python
{
    'tracker': TrackerDefinition,            # Tracker object
    'tasks': List[dict],                     # Enhanced task objects
    'total': int,                            # Total tasks in group
    'completed': int,                        # Completed tasks in group
}
```

#### Enhanced Task Object (with iOS Actions)

```python
{
    'task_instance_id': UUID,
    'status': str,
    'description': str,
    'category': str,
    'time_of_day': str,                      # 'morning', 'afternoon', 'evening', 'anytime'
    'weight': int,
    
    # iOS swipe actions (44pt minimum per Apple HIG)
    'ios_swipe_actions': {
        'leading': [                         # Swipe right actions
            {
                'id': 'complete',
                'title': '✓',
                'style': 'normal',
                'backgroundColor': '#22c55e',
                'endpoint': str,             # API endpoint
                'haptic': 'success',
                'minWidth': 44,              # Points
            }
        ],
        'trailing': [                        # Swipe left actions
            {
                'id': 'skip',
                'title': 'Skip',
                'backgroundColor': '#f59e0b',
                'endpoint': str,
                'payload': dict,
                'minWidth': 60,
            },
            {
                'id': 'delete',
                'title': 'Delete',
                'style': 'destructive',
                'backgroundColor': '#ef4444',
                'confirmRequired': True,
                'endpoint': str,
                'minWidth': 70,
            }
        ]
    },
    
    # Long-press context menu
    'ios_context_menu': [
        {'title': 'Edit', 'icon': 'pencil', 'action': 'edit'},
        {'title': 'Add Note', 'icon': 'note.text', 'action': 'note'},
        {'title': 'Move to Tomorrow', 'icon': 'arrow.forward', 'action': 'reschedule'},
        {'title': 'Delete', 'icon': 'trash', 'destructive': True, 'action': 'delete'}
    ]
}
```

#### Usage

- **Django URL**: Initial load for current day
- **AJAX**: Date navigation (`?date=2025-12-05`)
- **JavaScript**: Implement swipe gestures using `ios_swipe_actions` data

---

### `panels/trackers_list.html`

**Django URL**: `/panels/trackers/`  
**View**: `views_spa.panel_trackers_list`  
**AJAX**: Supports `?page=N` pagination

#### Context Data

```python
{
    'trackers': List[dict],                  # Paginated active trackers (6 per page)
    'archived_trackers': List[dict],         # All archived trackers
    'total_count': int,                      # Total active trackers
    'has_more': bool,                        # More trackers available
    'next_page': int | None,                 # Next page number
    'page': int,                             # Current page
}
```

#### Tracker Object

```python
{
    'id': UUID,                              # tracker_id
    'tracker_id': UUID,                      # Same as id
    'name': str,
    'description': str,
    'time_period': str,                      # 'daily', 'weekly', 'monthly'
    'status': str,                           # 'active', 'paused', 'completed', 'archived'
    'progress': int,                         # Completion percentage
    'task_count': int,                       # Total tasks
    'completed_count': int,                  # Completed tasks
    'updated_at': datetime,
}
```

---

### `panels/tracker_detail.html`

**Django URL**: `/panels/tracker/<uuid:tracker_id>/`  
**View**: `views_spa.panel_tracker_detail`  
**AJAX**: Supports `?page=N&group=status|date|category`

#### Context Data

```python
{
    'tracker': TrackerDefinition,            # Tracker object
    'today_tasks': QuerySet[TaskInstance],   # Today's tasks (ordered by weight)
    'grouped_tasks': {                       # Tasks grouped by status
        'todo': List[TaskInstance],
        'done': List[TaskInstance],
        'skipped': List[TaskInstance],
    },
    'historical_tasks': Page,                # Paginated historical tasks (last 30 days)
    'page_obj': Paginator.Page,              # Django paginator object
    'stats': dict,                           # Quick summary from AnalyticsService
    'detailed_metrics': dict,                # 7-day detailed metrics
    'top_insight': dict | None,              # Top behavioral insight for tracker
    'time_distribution': {                   # Task distribution by time of day
        'morning': int,
        'afternoon': int,
        'evening': int,
    },
    'today': date,
    'group_by': str,                         # Current grouping: 'status', 'date', 'category'
    
    # Compatibility aliases
    'tasks': QuerySet[TaskInstance],         # Same as today_tasks
    'task_count': int,
    'completed_count': int,
    'pending_count': int,
    'skipped_count': int,
    'progress': int,                         # Percentage
    'has_more_tasks': bool,
    'next_page': int | None,
}
```

---

### `panels/week.html`

**Django URL**: `/panels/week/`  
**View**: `views_spa.panel_week`  
**AJAX**: Supports `?week=N` offset (0 = current week, -1 = last week, +1 = next week)

#### Context Data

```python
{
    'days': List[dict],                      # 7 days with full data
    'week': List[dict],                      # Alias for 'days'
    'week_stats': {
        'completed': int,                    # Total completed in week
        'total': int,                        # Total tasks in week
        'completion_rate': int,              # Percentage
        'best_day': str,                     # Day name: 'Monday', 'Tuesday', etc.
        'best_day_rate': int,                # Best day completion %
        'streak': int,                       # Current streak
        'morning_completion': int,           # Morning tasks completed
        'afternoon_completion': int,
        'evening_completion': int,
        'morning_total': int,
        'afternoon_total': int,
        'evening_total': int,
        'best_time': str | None,             # 'morning', 'afternoon', 'evening'
        'best_time_rate': int,               # Best time completion %
    },
    'week_start': date,                      # Monday of week
    'week_end': date,                        # Sunday of week
    'week_number': int,                      # ISO week number
    'is_current_week': bool,
    'prev_week': date,                       # Previous week Monday
    'next_week': date,                       # Next week Monday
    'today': date,
    'start_of_week': date,                   # Alias for week_start
}
```

#### Day Object Structure

```python
{
    'date': date,
    'is_today': bool,
    'is_future': bool,
    'tasks': List[dict],                     # All tasks for this day
    'completed': int,
    'total': int,
    'progress': int,                         # Percentage
    
    # Time of day breakdown
    'morning_completed': int,
    'morning_total': int,
    'morning_rate': int,                     # Percentage
    'afternoon_completed': int,
    'afternoon_total': int,
    'afternoon_rate': int,
    'evening_completed': int,
    'evening_total': int,
    'evening_rate': int,
}
```

---

### `panels/month.html`

**Django URL**: `/panels/month/`  
**View**: `views_spa.panel_month`  
**AJAX**: Supports `?month=YYYY-MM`

#### Context Data

```python
{
    'month_name': str,                       # 'December'
    'year': int,
    'month': int,                            # 1-12
    'calendar_weeks': List[List[dict]],      # Weeks containing day objects
    'month_stats': {
        'completed': int,
        'total': int,
        'completion_rate': int,
        'best_week': int,                    # Week number
        'best_week_rate': int,
        'productive_days': int,              # Days with >80% completion
        'total_days': int,
    },
    'prev_month': date,                      # First day of previous month
    'next_month': date,                      # First day of next month
    'current_month': date,                   # First day of this month
    'is_current_month': bool,
    'today': date,
    
    # Heatmap data for calendar coloring
    'heatmap_data': dict,                    # {date_str: completion_rate}
}
```

#### Calendar Day Object

```python
{
    'date': date | None,                     # None for padding days
    'day': int,                              # Day number 1-31
    'is_today': bool,
    'is_current_month': bool,
    'is_weekend': bool,
    'completion_rate': int,                  # 0-100
    'task_count': int,
    'completed_count': int,
    'has_tasks': bool,
}
```

---

### `panels/analytics.html`

**Django URL**: `/panels/analytics/`  
**View**: `views_spa.panel_analytics`  
**AJAX**: For chart data updates via `/api/chart-data/` and `/api/heatmap/`

#### Context Data

```python
{
    'overview_stats': {
        'total_tasks': int,
        'completion_rate': int,
        'current_streak': int,
        'longest_streak': int,
        'active_trackers': int,
        'total_time_tracked': int,           # Hours (if time tracking enabled)
    },
    'chart_config': {                        # Initial chart configuration
        'timeframe': str,                    # '7d', '30d', '90d', 'all'
        'available_charts': List[str],       # ['completion', 'streak', 'category', 'time']
    },
    'top_insights': List[dict],              # Top 5 behavioral insights
    'tracker_breakdown': List[dict],         # Per-tracker statistics
    'category_distribution': dict,           # Category-wise breakdown
}
```

#### Usage

- **Django URL**: Initial page load with overview
- **AJAX**: Chart data loaded dynamically via:
  - `/api/chart-data/?type=completion&range=30d`
  - `/api/heatmap/?year=2025&month=12`

---

### `panels/goals.html`

**Django URL**: `/panels/goals/`  
**View**: `views_spa.panel_goals`

#### Context Data

```python
{
    'active_goals': List[Goal],              # Active goals
    'completed_goals': List[Goal],           # Completed goals
    'goal_stats': {
        'total_active': int,
        'avg_progress': int,                 # Average progress percentage
        'on_track': int,                     # Goals on track count
        'at_risk': int,                      # Goals at risk count
    },
}
```

#### Goal Object

```python
{
    'goal_id': UUID,
    'title': str,
    'description': str,
    'target_value': int,
    'current_value': int,
    'progress': Decimal,                     # 0-100
    'status': str,                           # 'active', 'completed', 'failed'
    'deadline': date | None,
    'icon': str,                             # Emoji or icon name
    'created_at': datetime,
    'updated_at': datetime,
}
```

---

### `panels/insights.html`

**Django URL**: `/panels/insights/`  
**View**: `views_spa.panel_insights`

#### Context Data

```python
{
    'insights': List[dict],                  # All behavioral insights
    'productivity_score': int,               # 0-100
    'recommendations': List[dict],           # Actionable recommendations
    'patterns': {
        'best_day': str,
        'best_time': str,
        'peak_performance_hours': List[int],
        'consistency_score': int,
    },
}
```

---

### `panels/templates.html`

**Django URL**: `/panels/templates/`  
**View**: `views_spa.panel_templates`

#### Context Data

```python
{
    'templates': List[dict],                 # Available tracker templates
    'categories': List[str],                 # Template categories
    'user_templates': List[dict],            # User-created templates
}
```

---

### `panels/help.html`

**Django URL**: `/panels/help/`  
**View**: `views_spa.panel_help`

#### Context Data

```python
{
    'help_sections': List[dict],             # Help topics
    'keyboard_shortcuts': List[dict],        # Available shortcuts
    'faq': List[dict],                       # Frequently asked questions
}
```

---

### `panels/settings/preferences.html`

**Django URL**: `/panels/settings/` or `/panels/settings/preferences/`  
**View**: `views_spa.panel_settings`

#### Context Data

```python
{
    'preferences': UserPreferences,          # User preferences object
    'themes': List[dict],                    # Available themes
    'current_section': str,                  # 'preferences', 'account', 'notifications', 'appearance'
}
```

#### UserPreferences Fields

- `theme` - Current theme name
- `push_enabled` - Push notifications enabled (bool)
- `email_notifications` - Email notifications enabled (bool)
- `start_of_week` - Week start day (0-6, where 0=Monday)
- `default_view` - Default landing view ('dashboard', 'today', etc.)

---

## Modal Templates

Modals are loaded via AJAX to `/modals/<modal_name>/` endpoint.

### `modals/add_task.html`

**Endpoint**: `/modals/add-task/`  
**View**: `views_spa.modal_view`

#### Context Data

```python
{
    'trackers': List[TrackerDefinition],     # Available trackers
    'categories': List[str],                 # Task categories
    'time_options': List[str],               # ['morning', 'afternoon', 'evening', 'anytime']
}
```

---

### `modals/edit_task.html`

**Endpoint**: `/modals/edit-task/?task_id=<uuid>`  
**View**: `views_spa.modal_view`

#### Context Data

```python
{
    'task': TaskInstance,                    # Task to edit
    'template': TaskTemplate,                # Task template
    'tracker': TrackerDefinition,
    'categories': List[str],
    'time_options': List[str],
}
```

---

### `modals/add_tracker.html`

**Endpoint**: `/modals/add-tracker/`  
**View**: `views_spa.modal_view`

#### Context Data

```python
{
    'time_periods': List[dict],              # Available time periods
    'templates': List[dict],                 # Tracker templates
}
```

---

### `modals/theme_gallery.html`

**Endpoint**: `/modals/theme-gallery/`  
**View**: `views_spa.modal_view`

#### Context Data

```python
{
    'themes': List[dict],                    # All available themes
    'current_theme': str,                    # Current active theme
}
```

---

## Settings Templates

### `panels/settings/preferences.html`

See [Panel Templates](#panels-settings-preferences-html) section above.

---

## Auth Templates

Authentication templates are standalone pages (not loaded via AJAX).

### `auth/login.html`

**Django URL**: `/login/`  
**View**: `views_auth.login_page`

#### Context Data

```python
{
    'google_oauth_enabled': bool,            # Whether Google OAuth is configured
    'google_client_id': str,                 # Google OAuth client ID (if enabled)
}
```

#### Authentication Methods

1. **Email/Password Login**
   - Standard form submission via AJAX
   - **API**: `POST /api/auth/login/`
   - **Payload**: `{email, password, remember}`
   - **Response**: `{success, redirect, user}`

2. **Google OAuth Login**
   - One-tap sign-in with Google
   - **Library**: Google Identity Services
   - **Flow**: 
     1. User clicks "Sign in with Google"
     2. Google OAuth popup/redirect
     3. Callback to `/accounts/google/login/callback/`
     4. django-allauth handles authentication
     5. Redirect to dashboard

#### Template Structure

```html
<div class="auth-container">
  <h1>Sign In to Tracker Pro</h1>
  
  <!-- Google OAuth Button -->
  {% if google_oauth_enabled %}
  <div class="google-auth">
    <div id="g_id_onload"
         data-client_id="{{ google_client_id }}"
         data-callback="handleGoogleSignIn">
    </div>
    <div class="g_id_signin" data-type="standard"></div>
    <div class="divider">or</div>
  </div>
  {% endif %}
  
  <!-- Email/Password Form -->
  <form id="login-form" action="/api/auth/login/" method="post">
    <input type="email" name="email" placeholder="Email" required>
    <input type="password" name="password" placeholder="Password" required>
    <label>
      <input type="checkbox" name="remember"> Remember me
    </label>
    <button type="submit">Sign In</button>
  </form>
  
  <div class="auth-footer">
    <a href="/forgot-password/">Forgot password?</a>
    <a href="/signup/">Create account</a>
  </div>
</div>
```

---

### `auth/signup.html`

**Django URL**: `/signup/`  
**View**: `views_auth.signup_page`

#### Context Data

```python
{
    'google_oauth_enabled': bool,            # Whether Google OAuth is configured
    'google_client_id': str,                 # Google OAuth client ID (if enabled)
}
```

#### Authentication Methods

1. **Email/Password Signup**
   - **API**: `POST /api/auth/signup/`
   - **Payload**: `{email, password1, password2}`
   - **Response**: `{success, redirect, user}`

2. **Google OAuth Signup**
   - Same flow as login
   - Automatically creates account if email not registered
   - **Callback**: `/accounts/google/login/callback/`

#### Template Structure

```html
<div class="auth-container">
  <h1>Create Your Account</h1>
  
  <!-- Google OAuth Button -->
  {% if google_oauth_enabled %}
  <div class="google-auth">
    <div id="g_id_onload"
         data-client_id="{{ google_client_id }}"
         data-callback="handleGoogleSignUp">
    </div>
    <div class="g_id_signin" data-type="standard"></div>
    <div class="divider">or</div>
  </div>
  {% endif %}
  
  <!-- Email/Password Form -->
  <form id="signup-form" action="/api/auth/signup/" method="post">
    <input type="email" name="email" placeholder="Email" required>
    <input type="password" name="password1" placeholder="Password" required>
    <input type="password" name="password2" placeholder="Confirm Password" required>
    <button type="submit">Create Account</button>
  </form>
  
  <div class="auth-footer">
    <a href="/login/">Already have an account? Sign in</a>
  </div>
</div>
```

#### Google OAuth Setup Notes

**Backend Configuration** (via django-allauth):
```python
# settings.py
INSTALLED_APPS = [
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}
```

**Frontend** (Google Identity Services):
```html
<script src="https://accounts.google.com/gsi/client" async defer></script>
```

---

### `auth/forgot_password.html`

**Django URL**: `/forgot-password/`  
**View**: `views_auth.forgot_password`

#### Context Data

```python
{} # Uses django-allauth for password reset
```

---

## Error Templates

### `errors/404.html`

**Django URL**: `/panels/error/404/`  
**View**: `views_spa.panel_error_404`

#### Context Data

```python
{
    'requested_url': str,                    # URL that wasn't found
}
```

---

### `errors/500.html`

**Django URL**: `/panels/error/500/`  
**View**: `views_spa.panel_error_500`

#### Context Data

```python
{
    'error_id': str,                         # Error tracking ID
    'support_email': str,
}
```

---

## Django URL Patterns vs AJAX

### Use Django URL Patterns (Direct Navigation)

✅ **Initial page loads**
- Login/Signup pages
- Initial SPA shell (`/`)
- Deep links to specific trackers (`/tracker/<id>/`)

✅ **SEO-important pages**
- Public help/documentation pages
- Landing pages

✅ **Form submissions to different pages**
- Login → Dashboard
- Signup → Dashboard

### Use AJAX for Dynamic Updates

✅ **Panel switching** (within SPA)
- Dashboard → Today via sidebar click
- Tracker list → Tracker detail

✅ **Filters and pagination**
- Dashboard period filter (`?period=weekly`)
- Tracker list pagination (`?page=2`)
- Date navigation (`?date=2025-12-05`)

✅ **Live data that needs to stay fresh**
- Task status updates
- Real-time notifications
- Chart data updates

✅ **Modals**
- Add/Edit task modals
- Theme picker
- Confirmation dialogs

### Pattern Summary

```
Navigation Type           Method        Example
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Login page               Django URL     /login/
Initial app load         Django URL     / or /app/
Panel switch             AJAX          /panels/today/
Filter change            AJAX          /panels/dashboard/?period=weekly
Modal open               AJAX          /modals/add-task/
API call (toggle task)   AJAX (POST)   /api/task/<id>/toggle/
Navigation with state    AJAX          /panels/week/?week=-1
```

---

## UX Enhancements in Templates

### Skeleton Loading Support

Templates that support `?skeleton=true` parameter:
- `panels/dashboard.html`
- `panels/today.html`
- `panels/trackers_list.html`

**Usage in JavaScript**:
```javascript
// Load skeleton first for instant perceived loading
fetch('/panels/dashboard/?skeleton=true')
  .then(r => r.json())
  .then(skeleton => renderSkeleton(skeleton.structure))
  
// Then load actual data
fetch('/panels/dashboard/')
  .then(r => r.text())
  .then(html => replaceWithRealContent(html))
```

### iOS-Specific Enhancements

**Touch Targets**: All interactive elements should be minimum 44x44 pt (Apple HIG)

**Swipe Actions**: Available in `ios_swipe_actions` data for:
- Task lists in Today panel
- Task lists in Tracker detail
- Task lists in Dashboard

**Context Menus**: Long-press menu data in `ios_context_menu`

**Haptic Feedback**: Action metadata includes:
- `haptic: 'success'` - Task completion
- `haptic: 'light'` - Button taps
- `haptic: 'error'` - Deletion/errors
- `haptic: 'warning'` - Skip actions

### API Response Format (UXResponse)

All AJAX endpoints return enhanced responses:

```python
{
    'success': bool,
    'message': str,                          # User-friendly message
    'data': dict,                            # Actual data
    'feedback': {                            # Visual feedback metadata
        'type': 'success' | 'celebration' | 'error',
        'haptic': str,                       # Haptic feedback type
        'toast': bool,                       # Show toast notification
        'animation': str,                    # Animation name
    },
    'stats_delta': dict,                     # Changed stats for optimistic updates
    'undo': {                                # Undo support
        'enabled': bool,
        'timeout_ms': int,
        'undo_data': dict,
    }
}
```

---

## JavaScript Interaction Patterns

### Expected JavaScript Behaviors

#### Panel Loading
```javascript
// Load panel via AJAX without page refresh
function loadPanel(url) {
    // Show skeleton if supported
    fetch(url + '?skeleton=true').then(...)
    
    // Load actual content
    fetch(url)
        .then(r => r.text())
        .then(html => {
            document.getElementById('main-content').innerHTML = html
            history.pushState({}, '', url.replace('/panels', ''))
        })
}
```

#### Form Submissions
```javascript
// Submit forms via AJAX
form.addEventListener('submit', async (e) => {
    e.preventDefault()
    
    const response = await fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: {'X-CSRFToken': getCsrfToken()}
    })
    
    const result = await response.json()
    
    if (result.success) {
        showToast(result.message)
        if (result.feedback?.animation === 'confetti') {
            triggerCelebration()
        }
    }
})
```

#### Modal Interactions
```javascript
// Open modal
function openModal(modalName, params = {}) {
    const url = `/modals/${modalName}/?${new URLSearchParams(params)}`
    
    fetch(url)
        .then(r => r.json())
        .then(data => {
            // data.html contains modal content
            // data.modal contains iOS presentation metadata
            showModal(data.html, data.modal)
        })
}
```

#### Optimistic UI Updates
```javascript
// Toggle task with optimistic update
async function toggleTask(taskId) {
    // Optimistic update - change UI immediately
    updateTaskUI(taskId, 'DONE')
    
    const response = await fetch(`/api/task/${taskId}/toggle/`, {method: 'POST'})
    const result = await response.json()
    
    if (!result.success) {
        // Revert on failure
        revertTaskUI(taskId, result.data.old_status)
    } else {
        // Show celebration if all complete
        if (result.stats_delta?.all_complete) {
            showCelebration()
        }
    }
}
```

---

## Keyboard Shortcuts

Comprehensive keyboard shortcuts for enhanced productivity.

### Global Shortcuts

| Shortcut | Action | Context |
|----------|--------|----------|
| `Ctrl+K` / `Cmd+K` | Open global search | Anywhere |
| `Ctrl+N` / `Cmd+N` | New tracker | Anywhere |
| `Ctrl+T` / `Cmd+T` | Quick add task | Anywhere |
| `Ctrl+,` / `Cmd+,` | Open settings | Anywhere |
| `?` | Show all shortcuts | Anywhere |
| `Esc` | Close modal/dropdown | Modal open |

### Navigation Shortcuts

| Shortcut | Action | Panel |
|----------|--------|-------|
| `D` | Go to Dashboard | Any |
| `T` | Go to Today | Any |
| `W` | Go to Week | Any |
| `M` | Go to Month | Any |
| `A` | Go to Analytics | Any |
| `G` | Go to Goals | Any |
| `H` | Go to Help | Any |
| `S` | Go to Settings | Any |

### Task Actions

| Shortcut | Action | Context |
|----------|--------|----------|
| `Space` | Toggle task status | Task focused |
| `E` | Edit task | Task focused |
| `Delete` / `Backspace` | Delete task | Task focused |
| `N` | Add note | Task focused |
| `↑` / `↓` | Navigate tasks | Task list |
| `Enter` | Open task detail | Task focused |

### Filter Shortcuts (Dashboard)

| Shortcut | Action |
|----------|--------|
| `1` | Daily view |
| `2` | Weekly view |
| `3` | Monthly view |
| `4` | All view |

### Date Navigation

| Shortcut | Action | Context |
|----------|--------|----------|
| `←` | Previous day/week/month | Today/Week/Month panel |
| `→` | Next day/week/month | Today/Week/Month panel |
| `Ctrl+←` / `Cmd+←` | Jump to start | Calendar view |
| `Ctrl+→` / `Cmd+→` | Jump to end | Calendar view |
| `.` | Today | Date navigation |

### Implementation in Templates

#### Display Shortcuts in Sidebar

```html
<nav class="sidebar-nav">
  <a href="/" class="nav-item" data-panel="dashboard" data-shortcut="d">
    <i class="icon-home"></i>
    <span>Dashboard</span>
    <kbd>D</kbd>
  </a>
  <a href="/today/" class="nav-item" data-panel="today" data-shortcut="t">
    <i class="icon-today"></i>
    <span>Today</span>
    <kbd>T</kbd>
  </a>
  <!-- More items... -->
</nav>
```

#### Keyboard Shortcuts Modal

Triggered by pressing `?`:

```html
<div id="shortcuts-modal" class="modal">
  <div class="modal-content">
    <h2>Keyboard Shortcuts</h2>
    
    <section>
      <h3>Global</h3>
      <table>
        <tr>
          <td><kbd>Ctrl</kbd> + <kbd>K</kbd></td>
          <td>Open search</td>
        </tr>
        <!-- More shortcuts... -->
      </table>
    </section>
    
    <section>
      <h3>Navigation</h3>
      <!-- More shortcuts... -->
    </section>
  </div>
</div>
```

#### JavaScript Implementation

```javascript
// Global shortcut handler
document.addEventListener('keydown', (e) => {
  // Ignore if typing in input
  if (e.target.matches('input, textarea')) return
  
  const key = e.key.toLowerCase()
  const ctrl = e.ctrlKey || e.metaKey
  
  // Global shortcuts
  if (ctrl && key === 'k') {
    e.preventDefault()
    openGlobalSearch()
  } else if (ctrl && key === 'n') {
    e.preventDefault()
    openNewTrackerModal()
  }
  
  // Navigation shortcuts
  else if (key === 'd') loadPanel('dashboard')
  else if (key === 't') loadPanel('today')
  else if (key === 'w') loadPanel('week')
  
  // Show shortcuts modal
  else if (key === '?') {
    e.preventDefault()
    showShortcutsModal()
  }
})
```

#### Context Data for Shortcuts

Add to `base.html` context:

```python
'keyboard_shortcuts': [
    {'key': 'Ctrl+K', 'action': 'Open search', 'category': 'Global'},
    {'key': 'D', 'action': 'Dashboard', 'category': 'Navigation'},
    {'key': 'T', 'action': 'Today', 'category': 'Navigation'},
    # ... more shortcuts
]
```

---

## Additional Resources

- **Backend Views**: `core/views_spa.py`, `core/views_api.py`, `core/views_ios.py`
- **URL Configuration**: `core/urls.py`
- **Refactoring Guides**:
  - `docs/sonnetSuggestion.md` - Practical implementation patterns
  - `docs/OpusSuggestion.md` - Strategic UX optimization
  - `docs/FinalRefactoringGuide.md` - Complete refactoring guide

---

**Last Updated**: 2025-12-06  
**Maintained By**: Backend Team
