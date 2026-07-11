from odoo import models, fields


class Subject(models.Model):
    _name = 'student.subject'
    _description = 'Subject'
    _order = 'name'

    name = fields.Char('Subject Name')
    code = fields.Char('Subject Code', size=10)
    max_marks = fields.Integer('Maximum Marks', default=100)
    description = fields.Text('Description')
    active = fields.Boolean('Active', default=True)
    
    teacher_ids = fields.Many2many("school.teacher", "Teachers")

    mark_ids = fields.One2many('student.mark', 'subject_id', 'Marks Recorded')

    _unique_name = models.Constraint('UNIQUE(name)', 'A subject with this name already exists.')
    _unique_code = models.Constraint('UNIQUE(code)', 'A subject with this code already exists.')
    _positive_marks = models.Constraint('CHECK(max_marks > 0)', 'Maximum marks must be greater than 0.')

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.name}" if rec.code else rec.name
        