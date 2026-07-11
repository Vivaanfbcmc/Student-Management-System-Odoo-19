from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date


class StudentMark(models.Model):
    _name = 'student.mark'
    _description = 'Student Mark'
    _order = 'subject_id'

    student_id = fields.Many2one('student.student', 'Student', ondelete='cascade', index=True)
    subject_id = fields.Many2one('student.subject', 'Subject', required=True, ondelete='restrict')
    marks_obtained = fields.Integer('Marks Obtained', default=0)
    max_marks = fields.Integer('Max Marks', related='subject_id.max_marks', store=True)
    percentage = fields.Float('Percentage (%)', compute='_compute_percentage', store=True)

    available_subject_ids = fields.Many2many('student.subject', compute='_compute_available_subjects')

    _unique_student_subject = models.Constraint('UNIQUE(student_id, subject_id)', 'A mark entry for this subject already exists for the student.')

    @api.depends('student_id.mark_ids.subject_id')
    def _compute_available_subjects(self):
        Subject = self.env['student.subject']
        for rec in self:
            all_subjects  = Subject.search([('active', '=', True)])
            used_subjects = rec.student_id.mark_ids.mapped('subject_id')
            if rec.subject_id:
                used_subjects = used_subjects - rec.subject_id
            rec.available_subject_ids = all_subjects - used_subjects

    @api.depends('marks_obtained', 'max_marks')
    def _compute_percentage(self):
        for rec in self:
            rec.percentage = (
                (rec.marks_obtained / rec.max_marks) * 100.0
                if rec.max_marks else 0.0
            )

    @api.constrains('marks_obtained', 'max_marks')
    def _check_marks(self):
        for rec in self:
            if rec.marks_obtained < 0:
                raise ValidationError("Marks obtained cannot be negative.")
            if rec.max_marks and rec.marks_obtained > rec.max_marks:
                raise ValidationError(
                    f"Marks obtained ({rec.marks_obtained}) cannot exceed "
                    f"max marks ({rec.max_marks}) for '{rec.subject_id.name}'."
                )
    
class Student(models.Model):
    _name = 'student.student'
    _description = 'Student'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Full Name', tracking=True)
    email = fields.Char('Email')
    address = fields.Text('Address')
    date_of_birth = fields.Date('Date of Birth')
    age = fields.Integer('Age', compute='_compute_age', store=True)
    photo = fields.Binary('Photo', attachment=True)
    active = fields.Boolean('Active', default=True)
    roll_number = fields.Char('Roll Number', copy=False, default='New')
    partner_id = fields.Many2one('res.partner', 'Contact', ondelete='set null')
    membership_state = fields.Selection([('none', 'Not a Member'),('requested', 'Requested'),('member', 'Member'),], 'Membership Status', default='none', tracking=True)
    user_id = fields.Many2one('res.users', 'System User', ondelete='set null')
    issue_ids = fields.One2many('library.issue', 'student_id', 'Book Issues')

    # Relations 
    # class_id domain uses allowed_class_ids computed below
    class_id = fields.Many2one('school.class', 'Class', ondelete='set null', tracking=True, domain="[('id', 'in', allowed_class_ids)]")

    division_id = fields.Many2one('school.class.division', 'Division', domain="[('class_id', '=', class_id)]", ondelete='set null', tracking=True,)

    # Computed — classes this student is eligible for based on age
    allowed_class_ids = fields.Many2many('school.class', compute='_compute_allowed_classes')

    class_teacher_id = fields.Many2one('school.teacher', 'Class Teacher', related='division_id.class_teacher_id')

    subject_ids = fields.Many2many('student.subject', 'student_subject_rel', 'student_id', 'subject_id', 'Enrolled Subjects')
    mark_ids = fields.One2many('student.mark', 'student_id', 'Subject Marks')

    # Academic Computed 
    total_percentage = fields.Float('Overall Percentage (%)', compute='_compute_grade_result', store=True)

    grade = fields.Selection([
        ('O',  'O  - Outstanding'),
        ('A+', 'A+ - Excellent'),
        ('A',  'A  - Very Good'),
        ('B+', 'B+ - Good'),
        ('B',  'B  - Above Avg'),
        ('C',  'C  - Average'),
        ('D',  'D  - Below Avg'),
        ('F',  'F  - Fail'),
    ], 'Grade', compute='_compute_grade_result', store=True, tracking=True)

    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], 'Result', compute='_compute_grade_result', store=True, tracking=True)

    subject_count = fields.Integer('Subject Count', compute='_compute_subject_count')

    _unique_roll_number = models.Constraint('UNIQUE(roll_number)', 'Roll number must be unique.')

    # Compute Methods 
    @api.onchange('class_id')
    def _onchange_class_id(self):
        self.division_id = False
        self.subject_ids = False
        self.mark_ids = [(5, 0, 0)]

    @api.onchange('division_id')
    def _onchange_division_id(self):
        if self.division_id:
            self._populate_marks()
        else:
            self.subject_ids = False
            self.mark_ids = [(5, 0, 0)]

    def _populate_marks(self):
    # 11-12: subjects from division; 1-10: subjects from class
        subjects = (self.division_id.subject_ids if self.division_id and self.division_id.subject_ids else self.class_id.subject_ids)
        self.subject_ids = subjects
        mark_lines = [(5, 0, 0)]
        for subject in subjects:
            mark_lines.append((0, 0, {'subject_id': subject.id, 'marks_obtained': 0,}))
        self.mark_ids = mark_lines

    @api.depends('date_of_birth')
    def _compute_age(self):
        today = fields.Date.today()
        for student in self:
            if student.date_of_birth:
                student.age = (today - student.date_of_birth).days // 365
            else:
                student.age = 0

    @api.depends('age')
    def _compute_allowed_classes(self):
        SchoolClass = self.env['school.class']
        for student in self:
            if not student.age:
                student.allowed_class_ids = SchoolClass.search([])
                continue

            lower = max(1, student.age - 6)
            upper = min(12, student.age - 5)

            # Build list of eligible grade strings
            eligible_grades = [str(g) for g in range(lower, upper + 1)]

            student.allowed_class_ids = SchoolClass.search([('grade', 'in', eligible_grades)])

    @api.depends('mark_ids.percentage')
    def _compute_grade_result(self):
        GRADE_BANDS = [
            (90, 'O'), (80, 'A+'), (70, 'A'), (60, 'B+'),
            (50, 'B'), (40, 'C'),  (30, 'D'),
        ]
        for student in self:
            marks = student.mark_ids
            avg = sum(marks.mapped('percentage')) / len(marks) if marks else 0.0
            student.total_percentage = avg
            student.grade = next((g for t, g in GRADE_BANDS if avg >= t), 'F')
            student.result = 'fail' if student.grade in ('D', 'F') else 'pass'

    @api.depends('subject_ids')
    def _compute_subject_count(self):
        for student in self:
            student.subject_count = len(student.subject_ids)


    # ORM Overrides 
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('roll_number', 'New') == 'New':
                vals['roll_number'] = (self.env['ir.sequence'].next_by_code('student.student') or 'New')
        return super().create(vals_list)

    def write(self, vals):
        result = super().write(vals)
        tracked_fields = ['email', 'address', 'class_id']
        changed = [f for f in tracked_fields if f in vals]
        if changed:
            for rec in self:
                rec.message_post(body=f"Updated: {', '.join(changed)}")
        return result

    def unlink(self):
        for rec in self:
            if rec.mark_ids:
                raise ValidationError("Cannot delete student with marks recorded.")
        return super().unlink()
    
    def action_request_membership(self):
        self.ensure_one()
        librarian_group = self.env.ref('student_management.group_librarian')
        self.env.cr.execute("""SELECT uid FROM res_groups_users_rel WHERE gid = %s LIMIT 1""", [librarian_group.id])
        row = self.env.cr.fetchone()
        if not row:
            raise ValidationError("No librarian found to send the request to.")
        librarian_user = self.env['res.users'].browse(row[0])
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=librarian_user.id,
            note=f"Library membership requested by {self.name}. Please review and approve.",
            summary="Library Membership Request",
        )
        self.membership_state = 'requested'

    def action_approve_membership(self):
        self.ensure_one()
        if not self.partner_id:
            partner = self.env['res.partner'].sudo().create({
                'name': self.name,
                'email': self.email,
                'is_library_member': True,
                'member_type': 'student',
                'student_id': self.id,
            })
            self.partner_id = partner
        else:
            self.partner_id.sudo().write({
                'is_library_member': True,
                'member_type': 'student',
            })
        self.membership_state = 'member'

    # Constraints 
    @api.constrains('email')
    def _check_email(self):
        for rec in self:
            if rec.email and '@' not in rec.email:
                raise ValidationError(f"'{rec.email}' is not a valid email address.")
            
    @api.constrains('division_id')
    def _check_division_strength(self):
        for rec in self:
            if not rec.division_id or not rec.division_id.strength:
                continue
            current_count = self.env['student.student'].search_count([
                ('division_id', '=', rec.division_id.id),
                ('id', '!=', rec.id),
            ])
            if current_count >= rec.division_id.strength:
                raise ValidationError(f"{rec.division_id.display_name} is full " f"(max {rec.division_id.strength} students). " f"Please change the division or class.")
    
    
    @api.constrains('date_of_birth', 'class_id')
    def _check_age_for_class(self):
        for rec in self:
            if not rec.date_of_birth or not rec.class_id:
                continue

            class_grade = int(rec.class_id.grade)
            min_age = class_grade + 5
            max_age = class_grade + 7

            today = date.today()
            cutoff = date(today.year, 3, 31)
            dob = rec.date_of_birth

            age_at_cutoff = (cutoff.year - dob.year - ((cutoff.month, cutoff.day) < (dob.month, dob.day)))

            if age_at_cutoff < min_age:
                raise ValidationError(f"{rec.name} must be at least {min_age} years old by March 31 " f"to be admitted to Class {class_grade}. " f"Current age at cutoff: {age_at_cutoff}.")
            if age_at_cutoff > max_age:
                raise ValidationError(f"{rec.name} is too old (age {age_at_cutoff} at cutoff) " f"for Class {class_grade}. Maximum age allowed is {max_age}.")
            