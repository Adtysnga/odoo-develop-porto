{
    'name': 'Rental House Management',
    'version': '1.0',
    'summary': 'Manajemen Sewa Rumah, Pembukuan, & WhatsApp Gateway Notification',
    'category': 'Real Estate',
    'author': 'Aditya Syahputra Sinaga',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'data/rental_sequence.xml',
        'views/rental_contract_view.xml',
        'views/rental_report_template.xml',
    ],
    'installable': True,
    'application': True,
}