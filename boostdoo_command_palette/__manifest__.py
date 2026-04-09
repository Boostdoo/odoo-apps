# Copyright 2026 Boostdoo

{
    'name': 'Boostdoo Command Palette',
    'version': '18.0.1.0.1',
    'summary': 'Global keyboard-driven command palette for fast Odoo navigation',
    'description': """
Boostdoo Command Palette introduces a global command interface inside Odoo
inspired by modern productivity tools like VS Code, Raycast, and Spotlight.

Features:
- Global keyboard shortcut (Ctrl+K)
- Universal search across menus, records, and actions
- Command favorites per user
- Command history tracking
- Custom commands by administrators
- Fuzzy search with intelligent matching
- Context-aware suggestions
- Full security compliance (ACL, record rules, multi-company)
    """,
    'author': 'Boostdoo',
    'license': 'OPL-1',
    'category': 'Productivity',
    'depends': ['base', 'web'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_config_parameter.xml',
        'data/ir_cron.xml',
        'views/command_custom_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'boostdoo_command_palette/static/src/utils/fuzzy_search.js',
            'boostdoo_command_palette/static/src/services/boostdoo_cache_service.js',
            'boostdoo_command_palette/static/src/services/boostdoo_search_service.js',
            'boostdoo_command_palette/static/src/services/boostdoo_command_service.js',
            'boostdoo_command_palette/static/src/components/command_palette_extension.js',
            'boostdoo_command_palette/static/src/components/command_palette_extension.xml',
            'boostdoo_command_palette/static/src/css/command_palette.scss',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'price': 9.99,
    'currency': 'EUR',

}
