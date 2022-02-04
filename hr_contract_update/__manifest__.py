# -*- coding: utf-8 -*-
{
    'name': "Hr Contract Update",
    'description': """
        Adding some fields and customization in contract
     """,
    'author': "Ahmed Elsayed Eldamhogy",
    'category': 'Hr',
    'version': '1.0',
    'depends': ['hr_contract', 'account'],
    'data': [
        'views/hr_contract_views.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
