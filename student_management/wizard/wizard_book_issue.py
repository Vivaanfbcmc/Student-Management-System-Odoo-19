from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta


class BookIssueWizard(models.TransientModel):
    _name = 'library.book.issue.wizard'
    _description = 'Book Issue Wizard'

    partner_id = fields.Many2one('res.partner', 'Member', required=True,
                                  domain="[('is_library_member', '=', True)]")
    member_type = fields.Selection(related='partner_id.member_type', string='Member Type', readonly=True)

    book_id = fields.Many2one('library.book', 'Book', required=True,
                               domain="[('available_copies', '>', 0)]")
    book_grade = fields.Selection(related='book_id.grade', readonly=True, string='Class Level')
    book_subject = fields.Many2one(related='book_id.subject_id', readonly=True, string='Subject')
    available_copies = fields.Integer(related='book_id.available_copies', readonly=True)

    issue_date = fields.Date('Issue Date', required=True, default=fields.Date.today)
    due_date = fields.Date('Due Date', required=True,
                            default=lambda self: fields.Date.today() + timedelta(days=14))

    student_class = fields.Char('Student Class', compute='_compute_student_info')
    eligibility_message = fields.Char('Eligibility', compute='_compute_student_info')
    is_eligible = fields.Boolean(compute='_compute_student_info')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Auto-fill partner from logged-in user email
        partner = self.env['res.partner'].search([
            ('email', '=', self.env.user.email),
            ('is_library_member', '=', True),
        ], limit=1)
        if partner:
            res['partner_id'] = partner.id
        # Pre-fill book from context
        if self.env.context.get('default_book_id'):
            res['book_id'] = self.env.context['default_book_id']
        return res

    @api.depends('partner_id', 'book_id')
    def _compute_student_info(self):
        for rec in self:
            if not rec.partner_id:
                rec.student_class = ''
                rec.eligibility_message = ''
                rec.is_eligible = False
                continue

            if rec.partner_id.member_type == 'teacher':
                rec.student_class = 'Teacher'
                rec.eligibility_message = 'Teachers can issue any book.'
                rec.is_eligible = True
                continue

            student = self.env['student.student'].search(
                [('partner_id', '=', rec.partner_id.id)], limit=1
            )
            if not student or not student.class_id:
                rec.student_class = 'No class assigned'
                rec.eligibility_message = 'Student has no class assigned.'
                rec.is_eligible = False
                continue

            rec.student_class = student.class_id.display_name

            if not rec.book_id:
                rec.eligibility_message = 'Select a book to check eligibility.'
                rec.is_eligible = False
                continue

            current = int(student.class_id.grade)
            book_g = int(rec.book_id.grade)

            if current <= book_g <= current + 1:
                rec.eligibility_message = f'Eligible — Class {current} student can issue Class {book_g} book.'
                rec.is_eligible = True
            else:
                rec.eligibility_message = (
                    f'Not eligible — Class {current} student can only issue '
                    f'Class {current} or Class {current + 1} books.'
                )
                rec.is_eligible = False

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if not self.env.context.get('default_book_id'):
            self.book_id = False
        if not self.partner_id:
            return {'domain': {'book_id': [('available_copies', '>', 0)]}}
        if self.partner_id.member_type == 'teacher':
            return {'domain': {'book_id': [('available_copies', '>', 0)]}}
        student = self.env['student.student'].search(
            [('partner_id', '=', self.partner_id.id)], limit=1
        )
        if student and student.class_id:
            current = int(student.class_id.grade)
            allowed = [str(current), str(current + 1)]
            return {
                'domain': {
                    'book_id': [
                        ('available_copies', '>', 0),
                        ('grade', 'in', allowed),
                    ]
                }
            }
        return {'domain': {'book_id': [('available_copies', '>', 0)]}}

    @api.constrains('issue_date', 'due_date')
    def _check_dates(self):
        for rec in self:
            if rec.due_date and rec.issue_date and rec.due_date <= rec.issue_date:
                raise ValidationError("Due date must be after the issue date.")

    def action_confirm_issue(self):
        self.ensure_one()
        if not self.is_eligible:
            raise ValidationError(self.eligibility_message)
        if self.book_id.available_copies <= 0:
            raise ValidationError(f"No copies of '{self.book_id.name}' are currently available.")
        student = self.env['student.student'].search(
            [('partner_id', '=', self.partner_id.id)], limit=1
        )
        self.env['library.issue'].sudo().create({
            'partner_id': self.partner_id.id,
            'book_id': self.book_id.id,
            'issue_date': self.issue_date,
            'due_date': self.due_date,
            'state': 'issued',
            'student_id': student.id if student else False,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Book Issued!',
                'message': f'"{self.book_id.name}" has been issued successfully. Due date: {self.due_date}',
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}