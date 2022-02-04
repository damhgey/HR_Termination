# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrContract(models.Model):
    _inherit = 'hr.contract'

    # Monthly allowances
    housing_allowance = fields.Float('Housing', digits='Payroll')
    transportation_allowance = fields.Float('Transportation', digits='Payroll')
    mobile_allowance = fields.Float('Mobile', digits='Payroll')
    food_allowance = fields.Float('Food', digits='Payroll')
    fixed_overtime_allowance = fields.Float('Fixed Overtime', digits='Payroll')
    other_allowance = fields.Float('Other', digits='Payroll')

    total_salary = fields.Monetary('Total Salary', compute='_compute_total_salary', store=True)
    travel_ticket_amount = fields.Float('Travel Ticket Amount', digits='Payroll', store=True)
    analytic_tag_ids = fields.Many2many(comodel_name="account.analytic.tag", string="Analytic Tag")

    def _compute_total_salary(self):
        total_salary = 0
        for rec in self:
            total_salary = sum([rec.wage, rec.housing_allowance, rec.transportation_allowance, rec.mobile_allowance,
                                rec.food_allowance, rec.fixed_overtime_allowance, rec.other_allowance])
            rec.total_salary = total_salary
