from odoo import api, fields, models


class NewModule(models.Model):
    _inherit = 'hr.payslip'

    source_document_id = fields.Many2one(comodel_name="hr.termination", string="Source Document", readonly=True)
