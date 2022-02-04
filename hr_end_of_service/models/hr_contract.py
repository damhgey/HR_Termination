# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrContract(models.Model):
    _inherit = 'hr.contract'

    became_eos = fields.Boolean(string="Became End Of service", help='A field to make eos salary rule run if true')
    eos_reason = fields.Char(string="EOS Reason", help='A field that salary rule use if eos true')
    leave_balance_days = fields.Float(string="Leave Balance Days", compute='_compute_leave_balance_days')

    def _compute_leave_balance_days(self):
        leave_report = self.env['hr.leave.report']
        for rec in self:
            paid_timeoff_days = leave_report.search(
                [('employee_id', '=', rec.employee_id.id),
                 ('holiday_status_id.work_entry_type_id.code', '=', 'LEAVE120'),
                 ('state', '=', 'validate')]).mapped('number_of_days')
            leave_days = sum(paid_timeoff_days)
            if paid_timeoff_days:
                rec.leave_balance_days = leave_days
            else:
                rec.leave_balance_days = 0
