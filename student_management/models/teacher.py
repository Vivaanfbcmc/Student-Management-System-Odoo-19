from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Teacher(models.Model):
    _name = 'school.teacher'
    _description = 'Teacher'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    #Basic Info
    name = fields.Char('Full Name', required=True, tracking=True)
    email = fields.Char('Email')
    phone = fields.Char('Phone')
    date_of_birth = fields.Date('Date of Birth')
    age = fields.Integer('Age', compute='_compute_age', store=True)
    photo = fields.Binary('Photo', attachment=True)
    active = fields.Boolean('Active', default=True)
    employee_id = fields.Char('Employee ID', copy=False, default='New', readonly=True)

    #System User Link
    user_id = fields.Many2one('res.users', 'System User', ondelete='set null', help='Link this teacher to an Odoo user account for login-based access control.')

    #Job Info 
    joining_date = fields.Date('Joining Date')
    post = fields.Selection([('teacher', 'Teacher'),('class_teacher', 'Class Teacher'),], 'Post', default='teacher', required=True)

    subject_ids = fields.Many2many('student.subject', 'teacher_subject_rel', 'teacher_id', 'subject_id', 'Subjects')

    # One2many back-ref — classes where this teacher is class teacher
    class_ids = fields.One2many('school.class.division', 'class_teacher_id', 'Classes')
    class_subject_ids = fields.One2many('school.class.subject', 'teacher_id', 'Class Assignments')

    # Computed — all students across all assigned classes
    student_ids = fields.Many2many('student.student', compute='_compute_student_ids', string='Students')
    student_count = fields.Integer('Total Students', compute='_compute_student_ids')
    class_count   = fields.Integer('Number of Classes', compute='_compute_class_count')

    #Library
    partner_id = fields.Many2one('res.partner', 'Library Contact', ondelete='set null', readonly=True)
    is_library_member = fields.Boolean(related='partner_id.is_library_member', readonly=True, string='Library Member')

    #Constraints 
    _unique_employee_id = models.Constraint('UNIQUE(employee_id)', 'Employee ID must be unique.')

    # Compute Methods
    @api.depends('date_of_birth')
    def _compute_age(self):
        today = fields.Date.today()
        for rec in self:
            rec.age = (today - rec.date_of_birth).days // 365 if rec.date_of_birth else 0

    @api.depends('class_ids')
    def _compute_class_count(self):
        for rec in self:
            rec.class_count = len(rec.class_ids)

    @api.depends('class_ids.student_ids')
    def _compute_student_ids(self):
        for rec in self:
            students = rec.class_ids.mapped('student_ids')
            rec.student_ids = students
            rec.student_count = len(students)

    # ORM Overrides
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('employee_id', 'New') == 'New':
                vals['employee_id'] = (self.env['ir.sequence'].next_by_code('school.teacher') or 'New')
        records = super().create(vals_list)
        for rec in records:
            rec._create_library_partner()
        return records

    def _create_library_partner(self):
        if not self.partner_id:
            partner = self.env['res.partner'].create({
                'name':              self.name,
                'email':             self.email,
                'phone':             self.phone,
                'is_library_member': True,
                'member_type':       'teacher',
            })
            self.partner_id = partner

    def write(self, vals):
        result = super().write(vals)
        for rec in self:
            if rec.partner_id:
                sync = {}
                if 'name'  in vals: sync['name']  = rec.name
                if 'email' in vals: sync['email']  = rec.email
                if 'phone' in vals: sync['phone']  = rec.phone
                if sync:
                    rec.partner_id.write(sync)
        return result

    # Constraints 
    @api.constrains('email')
    def _check_email(self):
        for rec in self:
            if rec.email and '@' not in rec.email:
                raise ValidationError(f"'{rec.email}' is not a valid email address.")

    @api.constrains('post', 'class_ids')
    def _check_post(self):
        for rec in self:
            if rec.post == 'class_teacher' and not rec.class_ids:
                raise ValidationError(
                    f"{rec.name} is set as Class Teacher but is not assigned to any class."
                )