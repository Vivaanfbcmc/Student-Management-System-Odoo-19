from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Timetable(models.Model):
    _name = 'school.timetable'
    _description = 'Class Timetable'
    _order = 'class_id, division_id, day'
    _rec_name = 'display_name'

    class_id = fields.Many2one('school.class', string='Class', required=True, ondelete='cascade')
    division_id = fields.Many2one(
        'school.class.division', string='Division',
        required=True, ondelete='cascade',
        domain="[('class_id', '=', class_id)]"
    )
    day = fields.Selection([
        ('1_monday',    'Monday'),
        ('2_tuesday',   'Tuesday'),
        ('3_wednesday', 'Wednesday'),
        ('4_thursday',  'Thursday'),
        ('5_friday',    'Friday'),
        ('6_saturday',  'Saturday'),
    ], string='Day', required=True)

    slot_ids = fields.One2many('school.timetable.slot', 'timetable_id', 'Slots')
    display_name = fields.Char(compute='_compute_display_name', store=True)
    slot_count = fields.Integer(compute='_compute_slot_count')

    _unique_timetable = models.Constraint(
        'UNIQUE(division_id, day)',
        'A timetable for this division and day already exists.'
    )


    @api.depends('class_id', 'division_id', 'day')
    def _compute_display_name(self):
        for rec in self:
            parts = []
            if rec.class_id:
                parts.append(rec.class_id.display_name)
            if rec.division_id:
                parts.append(rec.division_id.display_name)
            if rec.day:
                parts.append(rec.day.capitalize())
            rec.display_name = ' - '.join(parts) if parts else ''

    @api.depends('slot_ids')
    def _compute_slot_count(self):
        for rec in self:
            rec.slot_count = len(rec.slot_ids)

    @api.onchange('class_id')
    def _onchange_class_id(self):
        self.division_id = False

    @api.constrains('slot_ids')
    def _check_slots(self):
        for rec in self:
            slots = rec.slot_ids
            lectures = slots.filtered(lambda s: s.slot_type == 'lecture')
            breaks   = slots.filtered(lambda s: s.slot_type in ('short_break', 'lunch_break'))
            lunch    = slots.filtered(lambda s: s.slot_type == 'lunch_break')
            sport    = slots.filtered(lambda s: s.slot_type == 'sport')

            if len(lectures) < 6:
                raise ValidationError(
                    f"{rec.display_name}: Minimum 6 lecture slots required (currently {len(lectures)})."
                )
            if len(breaks) > 3:
                raise ValidationError(
                    f"{rec.display_name}: Maximum 3 break slots allowed (currently {len(breaks)})."
                )
            if len(lunch) > 1:
                raise ValidationError(
                    f"{rec.display_name}: Only 1 lunch break allowed."
                )
            if len(sport) > 1:
                raise ValidationError(
                    f"{rec.display_name}: Maximum 1 sport period allowed."
                )
            for slot in slots:
                if slot.time_start < 7.0 or slot.time_end > 14.0:
                    raise ValidationError(
                        f"{rec.display_name}: All slots must be within 07:00–14:00."
                    )
                if slot.time_start >= slot.time_end:
                    raise ValidationError(
                        f"{rec.display_name}: Slot start time must be before end time."
                    )


class TimetableSlot(models.Model):
    _name = 'school.timetable.slot'
    _description = 'Timetable Slot'
    _order = 'day_order, time_start'
    timetable_id = fields.Many2one(
        'school.timetable', string='Timetable',
        required=True, ondelete='cascade'
    )

    class_id = fields.Many2one(
        'school.class', related='timetable_id.class_id',
        store=True, string='Class'
    )
    division_id = fields.Many2one(
        'school.class.division', related='timetable_id.division_id',
        store=True, string='Division'
    )
    day = fields.Selection([
        ('1_monday',    'Monday'),
        ('2_tuesday',   'Tuesday'),
        ('3_wednesday', 'Wednesday'),
        ('4_thursday',  'Thursday'),
        ('5_friday',    'Friday'),
        ('6_saturday',  'Saturday'),
    ], string='Day', required=True)

    slot_number = fields.Integer('Slot #', required=True)
    time_start  = fields.Float('Start Time', required=True, default=7.0)
    time_end    = fields.Float('End Time',   required=True, default=7.75)

    time_start_display = fields.Char('Start', compute='_compute_time_display')
    time_end_display   = fields.Char('End',   compute='_compute_time_display')

    slot_type = fields.Selection([
        ('lecture',     'Lecture'),
        ('short_break', 'Short Break'),
        ('lunch_break', 'Lunch Break'),
        ('sport',       'Sport'),
        ('free',        'Free Period'),
    ], string='Type', required=True, default='lecture')

    subject_id = fields.Many2one(
        'student.subject', 'Subject',
        domain="[('active', '=', True)]"
    )
    teacher_id = fields.Many2one(
        'school.teacher', 'Teacher',
        domain="[('active', '=', True)]"
    )

    display_name = fields.Char(compute='_compute_display_name')
    log_ids = fields.One2many('school.timetable.log', 'slot_id', 'Lecture Logs')

    _unique_slot = models.Constraint(
        'UNIQUE(timetable_id, slot_number)',
        'This slot number already exists in the timetable.'
    )


    day = fields.Selection(
        related='timetable_id.day', store=True, string='Day'
    )
    day_order = fields.Integer('Day Order', compute='_compute_day_order', store=True)

    @api.depends('day')
    def _compute_day_order(self):
        order = {'monday': 1, 'tuesday': 2, 'wednesday': 3,
                'thursday': 4, 'friday': 5, 'saturday': 6}
        for rec in self:
            rec.day_order = order.get(rec.day, 0)

    @api.depends('time_start', 'time_end')
    def _compute_time_display(self):
        for rec in self:
            rec.time_start_display = self._float_to_time(rec.time_start)
            rec.time_end_display   = self._float_to_time(rec.time_end)

    @staticmethod
    def _float_to_time(value):
        h = int(value)
        m = round((value - h) * 60)
        return f"{h:02d}:{m:02d}"

    @api.depends('slot_number', 'slot_type', 'subject_id', 'class_id', 'division_id')
    def _compute_display_name(self):
        type_labels = dict(self._fields['slot_type'].selection)
        for rec in self:
            prefix = f"Slot {rec.slot_number}"
            if rec.slot_type == 'lecture':
                name = rec.subject_id.name if rec.subject_id else '—'
            else:
                name = type_labels.get(rec.slot_type, rec.slot_type)
            rec.display_name = f"{prefix} - {name}"

    @api.onchange('slot_type')
    def _onchange_slot_type(self):
        if self.slot_type in ('short_break', 'lunch_break', 'free'):
            self.subject_id = False
            self.teacher_id = False
        elif self.slot_type == 'sport':
            self.subject_id = False

    @api.onchange('subject_id')
    def _onchange_subject_id(self):
        if self.subject_id and self.timetable_id.division_id:
            assignment = self.env['school.class.subject'].search([
                ('class_id', '=', self.timetable_id.class_id.id),
                ('division_id', '=', self.timetable_id.division_id.id),
                ('subject_id', '=', self.subject_id.id),
            ], limit=1)
            if assignment and assignment.teacher_id:
                self.teacher_id = assignment.teacher_id

    @api.constrains('slot_type', 'subject_id')
    def _check_slot_content(self):
        for rec in self:
            if rec.slot_type == 'lecture' and not rec.subject_id:
                raise ValidationError("Lecture slot must have a subject assigned.")
            if rec.slot_type in ('short_break', 'lunch_break', 'free') and rec.subject_id:
                raise ValidationError("Break/free slots cannot have a subject.")
            if rec.slot_type == 'sport' and rec.subject_id:
                raise ValidationError("Sport slot should not have a subject assigned.")

    @api.constrains('time_start', 'time_end')
    def _check_times(self):
        for rec in self:
            if rec.time_start >= rec.time_end:
                raise ValidationError("Start time must be before end time.")
            if rec.time_start < 7.0 or rec.time_end > 14.0:
                raise ValidationError("Slot must be within 07:00–14:00.")

    def action_log_today(self):
        self.ensure_one()
        today = fields.Date.today()
        existing = self.env['school.timetable.log'].search([
            ('slot_id', '=', self.id),
            ('date', '=', today),
        ], limit=1)
        if existing:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'school.timetable.log',
                'res_id': existing.id,
                'view_mode': 'form',
                'target': 'new',
            }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'school.timetable.log',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_slot_id': self.id,
                'default_date': str(today),
            },
        }