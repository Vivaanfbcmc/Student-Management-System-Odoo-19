from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'
    is_library_member = fields.Boolean('Library Member', default=False)
    member_type = fields.Selection([
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    ], 'Member Type')
    
    student_id = fields.Many2one('student.student', 'Student Record')
    issue_ids = fields.One2many('library.issue', 'partner_id', 'Book Issues')