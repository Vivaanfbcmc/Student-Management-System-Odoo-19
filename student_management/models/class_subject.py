from odoo import models, fields

class ClassSubject(models.Model):
    _name = 'school.class.subject'
    _description = 'Class Subject Assignment'
    _order = 'subject_id, division_id'

    class_id = fields.Many2one('school.class', required=True, ondelete='cascade')
    division_id = fields.Many2one('school.class.division', 'Division', ondelete='cascade', domain="[('class_id', '=', class_id)]")
    subject_id = fields.Many2one('student.subject', 'Subject', required=True, ondelete='restrict')
    teacher_id = fields.Many2one('school.teacher', 'Teacher', ondelete='set null', domain="[('subject_ids', 'in', [subject_id])]")

    _unique_class_subject = models.Constraint('UNIQUE(class_id, division_id, subject_id)','This subject is already assigned to this division.')