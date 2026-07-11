from odoo import models, fields, api
from odoo.exceptions import ValidationError


class TimetableLog(models.Model):
    _name = 'school.timetable.log'
    _description = 'Lecture Log'
    _order = 'date desc, slot_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    slot_id = fields.Many2one(
        'school.timetable.slot', string='Slot',
        required=True, ondelete='cascade'
    )

    subject_id = fields.Many2one(
        'student.subject', related='slot_id.subject_id',
        store=True, string='Subject'
    )
    teacher_id = fields.Many2one(
        'school.teacher', related='slot_id.teacher_id',
        store=True, string='Teacher'
    )
    class_id = fields.Many2one(
        'school.class', related='slot_id.class_id',
        store=True, string='Class'
    )
    division_id = fields.Many2one(
        'school.class.division', related='slot_id.division_id',
        store=True, string='Division'
    )
    day = fields.Selection(
        related='slot_id.day', store=True, string='Day'
    )

    date = fields.Date('Date', required=True, default=fields.Date.today)
    topics_covered = fields.Text('Topics Covered')
    remarks = fields.Text('Remarks')

    is_past = fields.Boolean('Is Past Date', compute='_compute_is_past')
    display_name = fields.Char(compute='_compute_display_name')

    _unique_slot_date = models.Constraint(
        'UNIQUE(slot_id, date)',
        'A log entry for this slot and date already exists.'
    )

    @api.depends('date')
    def _compute_is_past(self):
        today = fields.Date.today()
        for rec in self:
            rec.is_past = bool(rec.date) and rec.date <= today

    @api.depends('slot_id', 'date')
    def _compute_display_name(self):
        for rec in self:
            slot = rec.slot_id.display_name or ''
            date = rec.date.strftime('%d %b %Y') if rec.date else ''
            rec.display_name = f"{slot} — {date}" if slot or date else ''

    @api.constrains('date')
    def _check_date(self):
        for rec in self:
            if rec.date and rec.date > fields.Date.today():
                raise ValidationError("Cannot log topics for a future date.")
