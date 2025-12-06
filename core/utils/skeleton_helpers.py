"""
Skeleton Screen Generator

Provides skeleton structure for panels to enable instant loading states.
Returns skeleton configuration that frontend can render immediately
while actual data loads in the background.
"""
from typing import Dict


def generate_panel_skeleton(panel_type: str, item_count: int = 5) -> Dict:
    """
    Generate skeleton structure for instant loading.
    
    Args:
        panel_type: Type of panel ('dashboard', 'today', 'week', 'trackers', 'list')
        item_count: Estimated number of items to show
    
    Returns:
        Skeleton structure dict for frontend rendering
    """
    skeletons = {
        'dashboard': {
            'type': 'dashboard',
            'sections': [
                {
                    'type': 'stats_grid',
                    'columns': 4,
                    'items': [
                        {'type': 'stat_card', 'has_icon': True, 'has_value': True}
                        for _ in range(4)
                    ]
                },
                {
                    'type': 'task_list',
                    'items': [
                        {
                            'type': 'task_item',
                            'has_checkbox': True,
                            'has_text': True,
                            'has_badge': True
                        }
                        for _ in range(min(item_count, 8))
                    ]
                },
                {
                    'type': 'tracker_grid',
                    'columns': 2,
                    'items': [
                        {'type': 'tracker_card', 'has_progress': True}
                        for _ in range(4)
                    ]
                }
            ]
        },
        
        'today': {
            'type': 'today',
            'sections': [
                {
                    'type': 'header',
                    'has_date': True,
                    'has_progress_ring': True
                },
                {
                    'type': 'task_groups',
                    'groups': [
                        {
                            'type': 'task_group',
                            'has_header': True,
                            'task_count': min(item_count // 2, 5)
                        }
                        for _ in range(2)
                    ]
                }
            ]
        },
        
        'week': {
            'type': 'week',
            'sections': [
                {
                    'type': 'header',
                    'has_date_range': True,
                    'has_stats': True
                },
                {
                    'type': 'day_columns',
                    'columns': 7,
                    'items_per_column': 3
                }
            ]
        },
        
        'trackers': {
            'type': 'grid',
            'columns': 2,
            'items': [
                {
                    'type': 'tracker_card',
                    'has_image': False,
                    'has_title': True,
                    'has_stats': True,
                    'has_progress': True
                }
                for _ in range(min(item_count, 6))
            ]
        },
        
        'tracker_detail': {
            'type': 'tracker_detail',
            'sections': [
                {
                    'type': 'header',
                    'has_title': True,
                    'has_progress_bar': True,
                    'has_stats_row': True
                },
                {
                    'type': 'task_list',
                    'items': [
                        {'type': 'task_item', 'has_checkbox': True, 'has_text': True}
                        for _ in range(min(item_count, 10))
                    ]
                }
            ]
        },
        
        'analytics': {
            'type': 'analytics',
            'sections': [
                {
                    'type': 'stats_grid',
                    'columns': 4,
                    'items': [{'type': 'stat_card'} for _ in range(4)]
                },
                {
                    'type': 'chart',
                    'chart_type': 'bar'
                },
                {
                    'type': 'chart',
                    'chart_type': 'heatmap'
                }
            ]
        },
        
        'list': {
            'type': 'list',
            'items': [
                {
                    'type': 'list_item',
                    'has_avatar': True,
                    'has_title': True,
                    'has_subtitle': True,
                    'has_action': True
                }
                for _ in range(min(item_count, 10))
            ]
        }
    }
    
    return skeletons.get(panel_type, skeletons['list'])


def generate_modal_skeleton(modal_type: str) -> Dict:
    """
    Generate skeleton for modal content.
    
    Args:
        modal_type: Type of modal ('add-task', 'edit-task', 'add-tracker', etc.)
    
    Returns:
        Skeleton structure dict for modal
    """
    skeletons = {
        'add-task': {
            'type': 'form',
            'fields': [
                {'type': 'text_input', 'label': True},
                {'type': 'select', 'label': True},
                {'type': 'slider', 'label': True}
            ],
            'actions': 2
        },
        
        'edit-task': {
            'type': 'form',
            'fields': [
                {'type': 'text_input', 'label': True},
                {'type': 'textarea', 'label': True},
                {'type': 'select', 'label': True},
                {'type': 'checkbox', 'label': True}
            ],
            'actions': 2
        },
        
        'add-tracker': {
            'type': 'form',
            'fields': [
                {'type': 'text_input', 'label': True},
                {'type': 'textarea', 'label': True},
                {'type': 'radio_group', 'label': True, 'options': 3}
            ],
            'actions': 2
        },
        
        'quick-add': {
            'type': 'form',
            'fields': [
                {'type': 'text_input', 'label': False, 'placeholder': True}
            ],
            'actions': 1
        }
    }
    
    return skeletons.get(modal_type, {'type': 'generic_form', 'fields': 3})


# iOS Modal presentation configuration
MODAL_PRESENTATION_CONFIG = {
    'add-task': {
        'presentation': 'sheet',
        'detents': ['medium', 'large'],
        'grabber_visible': True,
        'corner_radius': 12
    },
    'edit-task': {
        'presentation': 'sheet',
        'detents': ['large'],
        'keyboard_avoidance': True,
        'grabber_visible': True
    },
    'add-tracker': {
        'presentation': 'fullscreen',
        'dismissable': True
    },
    'quick-add': {
        'presentation': 'sheet',
        'detents': ['medium'],
        'interactive_dismiss_disabled': False,
        'grabber_visible': True
    }
}


def get_modal_config(modal_name: str) -> Dict:
    """
    Get iOS modal presentation configuration.
    
    Args:
        modal_name: Name of the modal
    
    Returns:
        Presentation configuration dict
    """
    default_config = {
        'presentation': 'sheet',
        'detents': ['large'],
        'grabber_visible': True,
        'corner_radius': 10
    }
    
    return MODAL_PRESENTATION_CONFIG.get(modal_name, default_config)
