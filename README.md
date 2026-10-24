# Student Management (Odoo 19 CE)

A custom Odoo 19 Community Edition module for running a school (Class 1 to 12). It covers students, teachers, classes and divisions, subjects, marks and report cards, weekly timetables, lecture logs and a school library. Each role (student, teacher, librarian, principal, admin) only sees what it should.

![Student Management home](docs/screenshots/home.png)
<!-- Screenshot: Student Management app home / students list -->

## Features

**Students**
- Roll number is generated automatically (`s/0001`, `s/0002`...)
- Age is computed from the date of birth
- Class dropdown only shows classes that fit the student's age
- Admission age check: the student must be between class + 5 and class + 7 years old on March 31
- Division strength check (default max of 40 students)
- Marks lines are filled automatically from the subjects of the selected class or division
- Overall percentage, grade and pass or fail result are computed from the marks
- A student with marks recorded cannot be deleted
- Changes to email, address and class are logged in the chatter

![Student form](docs/screenshots/student-form.png)
<!-- Screenshot: Student form with marks tab -->

**Grading**

| Percentage | Grade |
|------------|-------|
| 90 and above | O (Outstanding) |
| 80 to 89 | A+ |
| 70 to 79 | A |
| 60 to 69 | B+ |
| 50 to 59 | B |
| 40 to 49 | C |
| 30 to 39 | D (fail) |
| Below 30 | F (fail) |

![Report card](docs/screenshots/report-card.png)
<!-- Screenshot: Printed report card PDF -->

**Classes and divisions**
- Classes 1 to 12 with divisions A to D (classes 11 and 12 only get A, B and C)
- Streams for classes 11 and 12: A is Science, B is Commerce, C is Humanities
- Each division has a class teacher and a class representative
- Subject assignments per division, with a teacher picked from those who teach that subject

![Class form](docs/screenshots/class-form.png)
<!-- Screenshot: Class form with divisions and subject assignments -->

**Teachers**
- Employee ID is generated automatically (`TCH/2026/0001`)
- Post is either Teacher or Class Teacher (a class teacher must be assigned to a division)
- A library contact is created for every teacher and kept in sync with their name, email and phone
- Shows the teacher's students, classes and subject assignments

![Teacher form](docs/screenshots/teacher-form.png)
<!-- Screenshot: Teacher form -->

**Timetables**
- One timetable per division per day (Monday to Saturday)
- Slot types: Lecture, Short Break, Lunch Break, Sport and Free Period
- Rules enforced: at least 6 lectures, max 3 breaks, 1 lunch break, 1 sport period, and everything between 07:00 and 14:00
- Picking a subject fills in the assigned teacher automatically
- Students see their division's timetable and teachers see their own schedule

![Timetable form](docs/screenshots/timetable.png)
<!-- Screenshot: Timetable with slots -->

**Lecture logs**
- Teachers log the topics covered for each slot and date
- One log per slot per day and no logs for future dates

![Lecture log](docs/screenshots/lecture-log.png)
<!-- Screenshot: Lecture log form or list -->

**Library**
- Books are tagged by subject, class level and stream, with total, issued and available copies
- Students can issue books for their own class or the next class only
- Teachers can issue any book
- Issue wizard shows an eligibility message before confirming (default due date is 14 days)
- A daily cron marks late books as overdue
- Students can request library membership, which creates a to-do for the librarian to approve

![Library books](docs/screenshots/library-books.png)
<!-- Screenshot: Library books list -->

![Issue wizard](docs/screenshots/issue-wizard.png)
<!-- Screenshot: Book issue wizard with eligibility message -->

![Membership request](docs/screenshots/membership-request.png)
<!-- Screenshot: Membership request and librarian activity -->

## Demo data

The module loads this data on install so you can try it right away:
- 23 subjects (English, Hindi, Mathematics, Physics, Accountancy and more)
- Classes 1 to 12 with their divisions and subjects
- 76 library books across the class levels

## Access rights

| Group | What they can do |
|-------|------------------|
| Student | See their own profile, marks, class, timetable, lecture logs and book issues |
| Teacher | See students in their own divisions, their own schedule and logs, and manage their own book issues |
| Librarian | Full access to library books and issues, read access to students and teachers |
| Principal | Includes Teacher. Full access to all students, classes and teachers |
| School Administrator | Includes Principal and Librarian. Full access to everything including subjects |

Record rules match the logged in user to a student or teacher record by email, so the user's email must match the one on the record.

## Scheduled actions

| Name | Runs | What it does |
|------|------|--------------|
| Library: Mark Overdue Issues | Daily | Marks issued books past their due date as overdue |

## Dependencies

`base`, `mail`, `calendar`, `account`

## Installation

1. Copy the `student_management` folder into your Odoo addons path.
2. Restart the Odoo server.
3. Turn on developer mode and go to Apps, then click Update Apps List.
4. Search for "Student Management" and click Install.
5. Assign the Student, Teacher, Librarian, Principal or School Administrator group to your users.

Or from the command line:

```bash
./odoo-bin -c odoo.conf -d your_db -i student_management
```

To upgrade after changes:

```bash
./odoo-bin -c odoo.conf -d your_db -u student_management
```

## Heads up

This module defines its own `library.book` and `library.issue` models. If you also use a separate library module that defines the same model names, the two will clash, so install only one of them in the same database.

## Module structure

```
student_management/
├── data/          # sequences, cron, subjects, classes, books
├── models/        # student, teacher, class, subject, timetable, library
├── report/        # student report card PDF
├── security/      # groups, access rights, record rules
├── views/         # backend views and menus
└── wizard/        # book issue wizard
```

## Models

| Model | Purpose |
|-------|---------|
| `student.student` | Student profile, class, division, marks and result |
| `student.mark` | Marks for one subject of one student |
| `student.subject` | Subject with code and max marks |
| `school.teacher` | Teacher profile and library contact |
| `school.class` | Class (grade 1 to 12) |
| `school.class.division` | Division of a class with strength and class teacher |
| `school.class.subject` | Subject and teacher assignment for a division |
| `school.timetable` | Timetable for one division on one day |
| `school.timetable.slot` | One slot in a timetable |
| `school.timetable.log` | Topics covered in a slot on a date |
| `library.book` | Library book with copy counts |
| `library.issue` | Book issued to a student or teacher |
| `library.book.issue.wizard` | Wizard to issue a book with an eligibility check |

## Author

Vivaan Patange

## License

MIT
