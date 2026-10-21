{
    'name': 'Sewa Rumah Management & WA Notification',
    'version': '1.0',
    'summary': 'Modul Pemantauan Sewa Rumah dan Otomatisasi Pengingat WA',
    'category': 'Real Estate',
    'author': 'Adit Custom Odoo',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/rental_contract_view.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}