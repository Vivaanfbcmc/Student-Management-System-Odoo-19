from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date


class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'
    _order = 'grade_int, subject_id'

    name = fields.Char('Book Name', required=True)
    author = fields.Char('Author')
    edition = fields.Char('Edition', required=True)
    publisher = fields.Char('Publisher')
    total_copies = fields.Integer('Total Copies', default=100)
    active = fields.Boolean('Active', default=True)
    description = fields.Text('Description')

    subject_id = fields.Many2one('student.subject', 'Subject', required=True, ondelete='restrict')

    grade = fields.Selection([
        ('1', 'Class 1'), ('2', 'Class 2'),  ('3', 'Class 3'),
        ('4', 'Class 4'),  ('5', 'Class 5'),  ('6', 'Class 6'),
        ('7', 'Class 7'),  ('8', 'Class 8'),  ('9', 'Class 9'),
        ('10', 'Class 10'), ('11', 'Class 11'), ('12', 'Class 12'),
    ], 'Class Level', required=True)

    stream = fields.Selection([
        ('all', 'All Streams'),
        ('science', 'Science'),
        ('commerce', 'Commerce'),
        ('humanities', 'Humanities'),
    ], 'Stream', default='all')

    grade_int = fields.Integer('Grade Int', compute='_compute_grade_int', store=True)
    issue_ids = fields.One2many('library.issue', 'book_id', 'Issues')
    issued_copies = fields.Integer('Issued Copies', compute='_compute_issued_copies', store=True)
    available_copies = fields.Integer('Available Copies', compute='_compute_issued_copies', store=True)

    @api.depends('grade')
    def _compute_grade_int(self):
        for rec in self:
            rec.grade_int = int(rec.grade) if rec.grade else 0

    @api.depends('issue_ids.state', 'total_copies')
    def _compute_issued_copies(self):
        for rec in self:
            issued = len(rec.issue_ids.filtered(lambda i: i.state == 'issued'))
            rec.issued_copies    = issued
            rec.available_copies = rec.total_copies - issued

    def action_issue_book(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Issue a Book',
            'res_model': 'library.book.issue.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_book_id': self.id},
        }

    @api.constrains('total_copies')
    def _check_copies(self):
        for rec in self:
            if rec.total_copies < 1:
                raise ValidationError("Total copies must be at least 1.")


class LibraryIssue(models.Model):
    _name = 'library.issue'
    _description = 'Library Issue'
    _order = 'issue_date desc'
    _inherit = ['mail.thread']

    partner_id = fields.Many2one('res.partner', 'Member', required=True, ondelete='restrict', domain="[('is_library_member', '=', True)]")
    member_type = fields.Selection(related='partner_id.member_type', string='Member Type', store=True)
    book_id = fields.Many2one('library.book', 'Book', required=True, ondelete='restrict')

    issue_date  = fields.Date('Issue Date', default=fields.Date.today, required=True)
    due_date    = fields.Date('Due Date', required=True)
    return_date = fields.Date('Return Date')

    student_id = fields.Many2one('student.student', 'Student', ondelete='set null')

    state = fields.Selection([('issued', 'Issued'), ('returned', 'Returned'), ('overdue', 'Overdue'),], 'Status', default='issued', tracking=True)

    is_overdue = fields.Boolean('Overdue', compute='_compute_overdue', store=True)

    def _cron_mark_overdue(self):
        today = fields.Date.today()
        overdue = self.search([
            ('state', '=', 'issued'),
            ('due_date', '<', today),
        ])
        overdue.write({'state': 'overdue'})

    @api.depends('due_date', 'state')
    def _compute_overdue(self):
        today = date.today()
        for rec in self:
            rec.is_overdue = (
                rec.state == 'issued' and
                bool(rec.due_date) and
                rec.due_date < today
            )

    def action_return_book(self):
        for rec in self:
            rec.state = 'returned'
            rec.return_date = fields.Date.today()

    @api.constrains('partner_id', 'book_id')
    def _check_book_issue_rules(self):
        for rec in self:
            if not rec.partner_id or not rec.book_id:
                continue

            book = rec.book_id
            partner = rec.partner_id

            if not partner.is_library_member:
                raise ValidationError(f"{partner.name} is not a library member.")

            issued = self.env['library.issue'].search_count([
                ('book_id', '=', book.id),
                ('state', '=', 'issued'),
                ('id', '!=', rec.id),
            ])
            if issued >= book.total_copies:
                raise ValidationError(f"No copies of '{book.name}' are currently available.")

            if partner.member_type == 'student':
                student = self.env['student.student'].search(
                    [('partner_id', '=', partner.id)], limit=1
                )
                if student and student.class_id:
                    current_grade = int(student.class_id.grade)
                    book_grade = int(book.grade)
                    if book_grade < current_grade or book_grade > current_grade + 1:
                        raise ValidationError(
                            f"{partner.name} is in Class {current_grade} and can only issue "
                            f"books for Class {current_grade} or Class {current_grade + 1}. "
                            f"This book is for Class {book_grade}."
                        )