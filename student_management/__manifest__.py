{
    'name': 'Student Management',
    'version': '19.0.1.0.0',
    'summary': 'Student Management System',
    'description': 'Module for managing students and subjects',
    'author': 'Vivaan',
    'category': 'Education',

    'depends': ['base', 'mail', 'calendar'],

    'data': [
        
        'security/security.xml',
        'security/ir.model.access.csv',

        'data/sequence.xml',
        'data/cron.xml',
        'data/subject_data.xml',
        'data/class_data.xml',
        'data/book_data.xml',

        'wizard/wizard_book_issue_views.xml',

        'views/student_views.xml',
        'views/subject_views.xml',
        'views/teacher_views.xml',

        'views/class_views.xml',
        'views/timetable_views.xml',
        'views/timetable_log_views.xml',
        'views/library_views.xml',
        'views/menu_views.xml',

        'report/student_report.xml',
    ],

    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}