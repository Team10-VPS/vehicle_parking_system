# Deviations from the Submitted Documents (Sprint 1)

**Project:** Vehicle Parking System | **Team:** 10
**Compared against:** Software Architecture and Design Specification v1.0 (SAD) and Software Test Plan v1.0.
Each item below is explained in the final demo.

## 1. Implemented differently from the documents

| # | Ref | Document says | Implemented | Reason |
|---|---|---|---|---|
| 1 | SAD 3.3, 4.1 | Separate `services/` layer (AuthModule, SlotModule, BookingModule, AdminModule) | Business logic sits in the route files, with shared helpers in `app/utils.py` | Single-facility scale; models, routes and templates are still separated (VPS-NF-005) |
| 2 | SAD 4.1 | `app.py` and `models.py` at the root | `app/` package with a `create_app()` factory | The factory lets every test build an isolated app with an in-memory database |
| 3 | SAD 4.1 | Route files: auth, booking, admin | Route files: auth, slots, bookings, vehicles, admin | Slot viewing/booking and booking history are separate concerns |
| 4 | SAD 4.3 | Login failure returns 401; invalid registration 400; duplicate email 409 | Form is shown again with status 200 and a flash message | Friendlier for server-rendered forms; message text is as specified |
| 5 | SAD 4.3 | Admin duplicate slot, remove occupied slot and already-completed force checkout return 409 | Flash message and redirect or re-render | Admin pages kept simple; to be aligned in Sprint 2 (#11, #12) |
| 6 | SAD 4.3 | Successful booking redirects to `/dashboard` | Redirects to `/history` | Shows the new booking and its check-in time straight away |
| 7 | SAD 4.3 | `/logout` accepts GET and POST | GET only | Plain navigation link |
| 8 | SAD 4.3 | Check-out of a completed booking returns 409 | Returns 409 with a plain-text body ("Booking is already completed.") | No styled error page yet |
| 9 | SAD 4.5 | Navigation: Dashboard, Book, History, Logout, Admin Panel | Dashboard, My Bookings, My Vehicles, Admin Slots, Admin Bookings, Logout; booking starts by clicking an available slot | A separate Book link is not needed |
| 10 | SAD 3.5 (ADR-003) | Signed session cookie | Same, and `SECRET_KEY` must come from the environment (development fallback in `run.py` and `seed.py`); cookies are HttpOnly and SameSite=Lax | Avoids a hard-coded production secret |
| 11 | SAD 4.2 | `Slot` and `Vehicle.vehicle_number` | Classes/fields named `ParkingSlot` and `Vehicle.plate` (forms still use `vehicle_number`) | Naming only |

## 2. Additions beyond the documents

- **My Vehicles page (`/vehicles`):** customers register vehicles before booking; the booking form can use a registered vehicle (`vehicle_id`) or create a new one. Booking with another customer's vehicle returns 403.
- **Booking form page (`GET /book/<slot_id>`):** the SAD defines only `POST /book`.
- **Stronger double-booking guard:** the slot is claimed with a conditional database update and an active-booking check, and a concurrency test covers it (SAD 3.7 only asks for a single transaction).
- **Customers only can book:** admins get 403 on `/book` (matches the "Customer" access in SAD 4.3).
- **Extra validation:** name and email length limits, all-space passwords rejected, plate must contain a letter or digit.

## 3. Not yet implemented (planned for Sprint 2)

- `vehicle_type` on slots and in the admin add-slot form (SAD 4.2, 4.3)
- Force-checkout route `/admin/checkout/{id}` (currently `/admin/bookings/<id>/force-checkout`)
- Confirmation prompt before slot removal (check-out already has one)
- Text labels (Available / Occupied) on the dashboard, not colour only (SAD 4.5)
- Index on slot floor and slot number (SAD 3.7)
- CSRF tokens (SAD 3.9); only the SameSite cookie setting is in place
- Logging of bookings, forced check-outs and slot add/remove (login, logout and check-out failures are logged)
- Periodic slot/booking consistency check (SAD 4.4); consistency is covered by TC-Rel-01 tests only
- Styled error pages for 403, 404, 409 and 500

## 4. Test Plan and schedule

| # | Ref | Document says | Actual | Reason |
|---|---|---|---|---|
| 1 | Test Plan 7, SAD 3.1 | Build and test 15 to 23 September 2026 | Sprint 1 ran 19 to 23 October 2026 | Course schedule moved; plan dates to be revised |
| 2 | Test Plan 6 | Defect log or Jira | GitHub Issues and the Projects board | Same repository as the code |
| 3 | Test Plan 5 | Unit, integration, system and UAT levels | Sprint 1 covered unit and integration tests (pytest, run by GitHub Actions on every push and pull request); system, UAT and usability checks (TC-UX-01) follow in Sprint 2 | Sprint split |
| 4 | TC-Perf-01 | Dashboard responds within 2 seconds for 200 slots | Measured server-side with the Flask test client, not full browser rendering | Automated check inside CI |
| 5 | Test Plan 3 | Listed test case IDs only | Extra tests (concurrency, rollback on failure, logging, `SECRET_KEY`, cookie settings, vehicle ownership) are mapped to the nearest ID | Features added during development |
