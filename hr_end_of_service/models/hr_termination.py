from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
import calendar


class HrTermination(models.Model):
    _name = 'hr.termination'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'termination_code'

    # domain for employee_id field based on user group
    def get_employee_id_domain(self):
        if self.user_has_groups('hr_end_of_service.termination_manager_group'):
            employees = self.env['hr.employee'].search([('contract_id', '!=', False)]).ids
            return [('id', 'in', employees)]
        else:
            return [('id', 'in', self.env.user.employee_ids.ids), ('contract_id', '!=', False)]

    termination_code = fields.Char('Termination NO', readonly=True, default='Termination')
    application_date = fields.Date('Application Date', required=True, default=fields.Date.today(), readonly=True,
                                   states={'draft': [('readonly', False)]}, )
    state = fields.Selection([('draft', 'Draft'),
                              ('submit', 'submitted'),
                              ('department_approve', 'Department Approve'),
                              ('hr_approve', 'HR Approve'),
                              ('finance_approve', 'Finance Approve'),
                              ('paid', 'Paid'),
                              ('cancel', 'Cancelled')],
                             string="Status", readonly=True, default='draft', track_visibility='onchange', select=True)
    # Employee information
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee', required=True, readonly=True,
                                  domain=get_employee_id_domain, track_visibility='onchange',
                                  states={'draft': [('readonly', False)]})
    employee_code = fields.Char(string='Employee Code', related='employee_id.barcode')
    contract_id = fields.Many2one('hr.contract', 'Contract', related='employee_id.contract_id',
                                  track_visibility='onchange', required=True)
    company_id = fields.Many2one('res.company', 'Company', track_visibility='onchange',
                                 related='employee_id.company_id')
    department_id = fields.Many2one('hr.department', 'Department', related='employee_id.department_id',
                                    track_visibility='onchange')
    job_id = fields.Many2one('hr.job', 'Job Position', related='employee_id.job_id', track_visibility='onchange')
    hiring_date = fields.Date('Hiring Date', readonly=True, track_visibility='onchange', required=True,
                              related='employee_id.first_contract_date')
    last_working_date = fields.Date('Last Working Date', store=True, required=True, default=fields.Date.today(),
                                    states={'draft': [('readonly', False)]}, track_visibility='onchange')
    eos_reason = fields.Many2one(comodel_name="eos.reason", string="EOS Reason", required=True)
    eos_reason_note = fields.Text(string="EOS Reason Note", related='eos_reason.note')
    service_duration = fields.Char(string="Service Duration", compute='_compute_service_duration')
    show_recompute_button = fields.Boolean(default=False)

    # calculation field
    currency_id = fields.Many2one('res.currency', string='Currency')
    last_total_salary = fields.Monetary(string="Last Total Salary", readonly=True)
    leave_balance_days = fields.Float(string="Leave Balance Days", readonly=True,
                                      related='employee_id.contract_id.leave_balance_days')
    eos_amount = fields.Float(string="EOS Amount", readonly=True)
    leave_amount = fields.Float(string="Leave Amount", readonly=True)
    travel_ticket = fields.Float(string="Travel Ticket", readonly=True,
                                 related='employee_id.contract_id.travel_ticket_amount')
    # loan_balance_amount = fields.Float(string="Loan Balance Amount", readonly=True)
    total_deserved = fields.Float(string="Total Deserved", compute='_compute_total_deserve')
    termination_payslip_id = fields.Many2one('hr.payslip', string='Termination Payslip')
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    approved_by = fields.Many2one('res.users', 'Approved By')
    approved_date = fields.Date('Approved Date')
    note = fields.Text(string="Note", )

    @api.model
    def create(self, vals):
        # Check if employee has already a termination apply
        termination_count = self.search_count([('employee_id', '=', vals['employee_id']), ('state', '!=', 'cancel')])
        if termination_count > 0:
            raise ValidationError(_("Employee can not have more than one termination application"))

        termination_code = self.env['ir.sequence'].get('hr.termination.code')
        vals['termination_code'] = termination_code
        return super(HrTermination, self).create(vals)

    def button_submit(self):
        # Update value of eos field in employee contract with True
        emp_contract = self.employee_id.contract_id
        emp_contract.write(
            {'became_eos': True, 'eos_reason': self.eos_reason.name, 'eos_code': self.eos_reason.code,
             'date_end': self.last_working_date})

        self.state = 'submit'

    def button_department_approve(self):
        # Update End Date in contract
        emp_contract = self.employee_id.contract_id
        emp_contract.write({'eos_reason': self.eos_reason.name, 'eos_code': self.eos_reason.code,
                            'date_end': self.last_working_date})

        today = fields.Date.today()
        date_from = today.replace(day=1)
        last_date_of_month = calendar.monthrange(today.year, today.month)[1]
        date_to = today.replace(day=last_date_of_month)
        # Create termination payslip
        termination_payslip = self.env['hr.payslip'].create({
            'name': 'Termination Payslip %s - %s' % (self.termination_code, self.employee_id.display_name),
            'source_document_id': self.id,
            'employee_id': self.employee_id.id,
            'date_from': date_from,
            'date_to': date_to,
            'contract_id': self.employee_id.contract_id.id,
            'struct_id': self.employee_id.contract_id.structure_type_id.default_struct_id.id,
        })
        termination_payslip.action_refresh_from_work_entries()
        termination_payslip.compute_sheet()

        # Update termination_payslip_id with created payslip id
        self.write({'termination_payslip_id': termination_payslip})

        # Update eos fields values form created payslip
        # last_total_salary
        net = termination_payslip.line_ids.filtered(lambda l: l.code == 'NET').mapped('total')
        eosb_category = sum(
            termination_payslip.line_ids.filtered(lambda l: l.category_id.code == 'EOSB').mapped('total'))
        if net and eosb_category:
            self.last_total_salary = net[0] - eosb_category
        elif net:
            self.last_total_salary = net[0]

        # eos_amount
        eos_amount = termination_payslip.line_ids.filtered(lambda l: l.code == 'EOSB').mapped('total')
        if eos_amount:
            self.eos_amount = eos_amount[0]

        # leave_amount
        leave_amount = termination_payslip.line_ids.filtered(lambda l: l.code == 'ALBA').mapped('total')
        if leave_amount:
            self.leave_amount = leave_amount[0]

        # # loan_balance_amount
        # loan_balance_amount = termination_payslip.line_ids.filtered(lambda l: l.code == 'IN_DED').mapped('total')
        # if loan_balance_amount:
        #     self.loan_balance_amount = abs(loan_balance_amount[0])

        self.state = 'department_approve'

    def button_hr_approve(self):
        # ensure making recompute before move to the next state
        if self.show_recompute_button:
            raise ValidationError(_("Click recompute before moving to next state because there is some data updated"))

        self.state = 'hr_approve'

    def button_finance_approve(self):
        # ensure making recompute before move to the next state
        if self.show_recompute_button:
            raise ValidationError(_("Click recompute before moving to next state because there is some data updated"))

        # confirm payslip and post journal entry
        self.termination_payslip_id.action_payslip_done()
        self.termination_payslip_id.move_id.action_post()

        # Archive Employee
        self.employee_id.action_archive()

        self.state = 'finance_approve'

    def reset_to_draft(self):
        if self.termination_payslip_id:
            self.termination_payslip_id.action_payslip_cancel()
        self.state = 'draft'

    def button_cancel(self):
        if self.state in ('finance_approve', 'paid'):
            raise ValidationError(_("You can not cancel a termination that has confirmed payslip with posted entry"))
        else:
            # back eos to false
            emp_contract = self.employee_id.contract_id
            emp_contract.write(
                {'became_eos': False, 'eos_reason': False, 'eos_code': False, 'date_end': False, 'state': 'open'})
            # updated termination payslip to rejected status
            if self.termination_payslip_id:
                self.termination_payslip_id.write({'state': 'cancel'})
            self.state = 'cancel'

    # compute total deserved
    @api.depends('last_total_salary', 'eos_amount', 'leave_amount', 'travel_ticket',)
    def _compute_total_deserve(self):
        for rec in self:
            total = sum(
                [rec.last_total_salary, rec.eos_amount, rec.leave_amount, rec.travel_ticket])
            if total:
                rec.total_deserved = total
            else:
                rec.total_deserved = 0

    # Compute service duration based on last working date hiring date
    @api.depends('last_working_date', 'hiring_date')
    def _compute_service_duration(self):
        start_date = self.hiring_date
        end_date = self.last_working_date
        if start_date and end_date > start_date:
            service_duration = relativedelta(end_date, start_date)
            duration_years = service_duration.years
            duration_months = service_duration.months
            duration_days = service_duration.days
            service_duration_value = ' %d year  %d month  %d day ' % (duration_years, duration_months, duration_days)
            self.service_duration = service_duration_value
        elif start_date and start_date > end_date:
            raise ValidationError(_("Start date must be less than last working date"))
        else:
            self.service_duration = ' 0 year 0 month 0 day '

    @api.onchange('last_working_date', 'eos_reason')
    def onchange_show_recompute(self):
        if self.state in ('department_approve', 'hr_approve'):
            self.show_recompute_button = True

    # Button to update eos reason and end date in contract onchange
    # and recompute payslip and update termination fields that read from payslip
    def recompute_and_update_if_change(self):
        if self.state not in ('draft', 'cancel'):
            updated_fields = {}
            # To update eos reason and end date in contract
            emp_contract = self.employee_id.contract_id
            emp_contract.write({'eos_reason': self.eos_reason.name, 'eos_code': self.eos_reason.code, 'date_end': self.last_working_date})

            if self.termination_payslip_id:
                # Recompute payslip
                self.termination_payslip_id.action_refresh_from_work_entries()
                self.termination_payslip_id.compute_sheet()
                self.termination_payslip_id.write({'source_document_id': self.id})

                # Recompute Payslip and assign calculation fields from payslip lines

                # last_total_salary
                net = self.termination_payslip_id.line_ids.filtered(lambda l: l.code == 'NET').mapped('total')
                eosb_category = sum(
                    self.termination_payslip_id.line_ids.filtered(lambda l: l.category_id.code == 'EOSB').mapped(
                        'total'))
                if net and eosb_category:
                    last_total_salary = net[0] - eosb_category
                elif net:
                    last_total_salary = net[0]
                else:
                    last_total_salary = 0
                updated_fields['last_total_salary'] = last_total_salary

                # eos_amount
                eos_amount = self.termination_payslip_id.line_ids.filtered(lambda l: l.code == 'EOSB').mapped('total')
                if eos_amount:
                    eos_amount = eos_amount[0]
                else:
                    eos_amount = 0
                updated_fields['eos_amount'] = eos_amount

                # leave_amount
                leave_amount = self.termination_payslip_id.line_ids.filtered(lambda l: l.code == 'ALBA').mapped('total')
                if leave_amount:
                    leave_amount = leave_amount[0]
                else:
                    leave_amount = 0
                updated_fields['leave_amount'] = leave_amount

                # loan_balance_amount
                # loan_balance_amount = self.termination_payslip_id.line_ids.filtered(
                #     lambda l: l.code == 'IN_DED').mapped('total')
                # if loan_balance_amount:
                #     loan_balance_amount = abs(loan_balance_amount[0])
                # else:
                #     loan_balance_amount = 0
                # updated_fields['loan_balance_amount'] = loan_balance_amount

            #  Update current record fields with new values after recomputed
            self.write(updated_fields)

            # Update show_recompute_button field to be false to make button show if changes happen
            self.show_recompute_button = False

    # Action for smart button of related termination payslip
    def open_termination_payslip(self):
        return {
            'name': 'Termination Payslip',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.payslip',
            'domain': [('id', '=', self.termination_payslip_id.id)],
            'type': 'ir.actions.act_window',
        }

    # Cron job to update termination status to be paid if related payslip status became paid
    def update_paid_status(self):
        for rec in self:
            if rec.termination_payslip_id.state == 'paid':
                rec.write({'state': 'paid'})


class EOSReasons(models.Model):
    _name = 'eos.reason'
    _rec_name = 'name'
    _description = 'To link with eos reason field in hr.termination model.'

    name = fields.Char('EOS Reason')
    code = fields.Char('Code')
    note = fields.Text('Note')
