# -*- encoding: utf-8 -*-

{
    'name': "HR End Of Service",
    'version': '1.0',
    'category': 'Hr',
    'description': """Add termination screen that allow employee to apply for end of service application 
        that has many stage for approving by multiple management and if it approved it will make auto EOS payslip.
     """,
    'author': "Ahmed Elsayed Eldamhogy",
    "depends": ['base', 'hr', 'hr_payroll', 'account', 'hr_contract_update'],
    "data": [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/termination_view.xml',
        'views/hr_contract_views.xml',
        'views/eos_reason_view.xml',
        'views/hr_payslip_view.xml',
        'views/eos_fields_rule_code.xml',
        'data/hr_termination_sequence.xml',
        'data/paid_termination_status_cron_job.xml',
        'data/data_eos_field_rule_code.xml',
        'data/eos_reasons.xml',
        'data/hr_salary_rules.xml',
        'report/termination_report.xml'
    ],
    "installable": True,
}
