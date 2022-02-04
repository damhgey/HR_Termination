from odoo import api, fields, models


class EOSFieldRuleCode(models.Model):
    _name = 'eos.field.rule.code'
    _rec_name = 'field_name'

    field_name = fields.Char('Field Name')
    rule_code = fields.Char('Rule Code')
