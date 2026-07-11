from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SchoolClassDivision(models.Model):
    _name = 'school.class.division'
    _description = 'Class Division'
    _order = 'class_id, name'
    _rec_name = 'name'

    name = fields.Selection([
        ('A', 'Division A'),
        ('B', 'Division B'),
        ('C', 'Division C'),
        ('D', 'Division D'),
    ], 'Division', required=True)

    class_id = fields.Many2one('school.class', 'Class', required=True, ondelete='cascade')
    strength = fields.Integer('Max Strength', default=40)
    student_ids = fields.One2many('student.student', 'division_id', 'Students')
    student_count = fields.Integer('Enrolled', compute='_compute_student_count', store=True)
    display_name = fields.Char('Name', compute='_compute_display_name', store=True)

    stream = fields.Selection([
        ('science', 'Science'),
        ('commerce', 'Commerce'),
        ('humanities', 'Humanities'),
    ], 'Stream', compute='_compute_stream', store=True, readonly=False)

    subject_ids = fields.Many2many('student.subject', 'division_subject_rel', 'division_id', 'subject_id', 'Subjects')

    class_teacher_id = fields.Many2one('school.teacher', 'Class Teacher', domain="[('class_subject_ids.division_id', '=', id)]")
    class_representative_id = fields.Many2one('student.student', 'Class Representative', domain="[('division_id', '=', id)]")

    @api.depends('name', 'class_id.grade')
    def _compute_stream(self):
        stream_map = {'A': 'science', 'B': 'commerce', 'C': 'humanities'}
        for rec in self:
            if rec.class_id and rec.class_id.grade in ('11', '12'):
                rec.stream = stream_map.get(rec.name, False)
            else:
                rec.stream = False

    _unique_division = models.Constraint('UNIQUE(class_id, name)', 'This division already exists for the class.')

    @api.depends('student_ids')
    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.student_ids)

    @api.depends('name')
    def _compute_display_name(self):
        labels = dict(self._fields['name'].selection)
        for rec in self:
            rec.display_name = labels.get(rec.name, '')

    @api.constrains('class_id', 'name')
    def _check_division_allowed(self):
        for rec in self:
            if rec.class_id.grade in ('11', '12') and rec.name == 'D':
                raise ValidationError("Classes 11 and 12 cannot have Division D.")

    @api.constrains('student_ids', 'strength')
    def _check_strength(self):
        for rec in self:
            if rec.strength and len(rec.student_ids) > rec.strength:
                raise ValidationError(f"{rec.display_name} is full (max {rec.strength} students). " f"Please change the division or class.")


class SchoolClass(models.Model):
    _name = 'school.class'
    _description = 'School Class'
    _order = 'grade_int'
    _rec_name = 'display_name'

    grade = fields.Selection([
        ('1', 'Class 1'),  ('2', 'Class 2'),  ('3', 'Class 3'),
        ('4', 'Class 4'),  ('5', 'Class 5'),  ('6', 'Class 6'),
        ('7', 'Class 7'),  ('8', 'Class 8'),  ('9', 'Class 9'),
        ('10', 'Class 10'), ('11', 'Class 11'), ('12', 'Class 12'),
    ], 'Grade', required=True)

    academic_year = fields.Char('Academic Year', default='2025-26')
    grade_int = fields.Integer('Grade Int', compute='_compute_grade_int', store=True)
    display_name = fields.Char('Name', compute='_compute_display_name', store=True)

    subject_ids = fields.Many2many('student.subject', 'class_subject_rel', 'class_id', 'subject_id', 'Subjects')

    class_subject_ids = fields.One2many('school.class.subject', 'class_id', 'Subject Assignments')
    division_ids = fields.One2many('school.class.division', 'class_id', 'Divisions')
    student_ids = fields.One2many('student.student', 'class_id', 'Students')
    timetable_ids = fields.One2many('school.timetable', 'class_id', 'Timetables')
    student_count = fields.Integer('Total Students', compute='_compute_student_count')

    _unique_grade = models.Constraint('UNIQUE(grade)', 'A class record for this grade already exists.')

    @api.depends('grade')
    def _compute_grade_int(self):
        for rec in self:
            rec.grade_int = int(rec.grade) if rec.grade else 0

    @api.depends('grade')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"Class {rec.grade}" if rec.grade else ''

    @api.depends('student_ids')
    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.student_ids)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._sync_subjects()
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'subject_ids' in vals or 'division_ids' in vals:
            self._sync_subjects()
        return result

    def _sync_subjects(self):
        for rec in self:
            if rec.subject_ids:
                for division in rec.division_ids:
                    existing = self.env['school.class.subject'].search([
                        ('class_id', '=', rec.id),
                        ('division_id', '=', division.id),
                    ]).mapped('subject_id')
                    for subject in rec.subject_ids:
                        if subject not in existing:
                            self.env['school.class.subject'].create({
                                'class_id': rec.id,
                                'division_id': division.id,
                                'subject_id': subject.id,
                            })
            for division in rec.division_ids:
                if division.subject_ids:
                    existing = self.env['school.class.subject'].search([
                        ('class_id', '=', rec.id),
                        ('division_id', '=', division.id),
                    ]).mapped('subject_id')
                    for subject in division.subject_ids:
                        if subject not in existing:
                            self.env['school.class.subject'].create({
                                'class_id': rec.id,
                                'division_id': division.id,
                                'subject_id': subject.id,
                            })