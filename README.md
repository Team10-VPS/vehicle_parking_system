# Vehicle Parking System (VPS) - Team 10

![CI](../../actions/workflows/ci.yml/badge.svg)

A Flask + SQLite web app for booking parking slots, check-in/check-out, booking
history and admin slot management. Built for the Software Engineering Mini Project.

## Team
| Name | Contribution |
|---|---|
| Swapna | QA Lead, test plan |
| Shreya R D | Test engineer, repo and organization setup, CI/CD pipeline |
| Himani Nune | _fill in_ |
| Atharv Sameer Sawarkar | _fill in_ |

## Features
- Registration (duplicate email check), login, logout, hashed passwords
- Parking slot dashboard grouped by floor
- Book a slot (new or existing vehicle), automatic check-in time
- Customer check-out (owner/admin only), booking history
- Admin: add/remove slots, view active bookings, force check-out

## Setup
```bash
python -m venv venv
venv\Scripts\activate        # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python seed.py               # demo admin, customer and 30 slots
python run.py                # open http://127.0.0.1:5000
```
Demo logins: `admin@vps.com / admin123`, `user@vps.com / user123`

## Run tests
```bash
pytest -v
```
Tests live in `tests/`: `test_models.py` (unit), the other three files are integration tests.
Each test's docstring names the Test Plan case ID (e.g. TC-Reg-01).

## CI/CD
GitHub Actions (`.github/workflows/ci.yml`) installs dependencies, checks the app builds
and runs all tests on every push and pull request.

## Structure
```
app/models.py      database models
app/routes/        auth, slots, bookings, admin blueprints
app/templates/     HTML templates
tests/             unit + integration tests
docs/              test cases and RTM
```

## Branching
`main` is always green. Work on `feature/<name>` branches and merge via pull request.
