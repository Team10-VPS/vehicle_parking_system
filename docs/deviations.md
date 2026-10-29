# Deviations from the Submitted Documents

**Project:** Vehicle Parking System | **Team:** 10
**Compared against:** Software Requirements Specification v1.0 (SRS), Software Architecture and Design Specification v1.0 (SAD) and Software Test Plan v1.0.
Each item below is explained in the final demo. Status is as of the end of Sprint 2 work.

## 1. Implemented differently from the documents

| # | Ref | Document says | Implemented | Reason |
|---|---|---|---|---|
| 1 | SRS VPS-SR-002, TC-Sec-03 | A non-admin request to an admin route is redirected | Anonymous users are redirected to login; logged-in non-admins receive 403 Forbidden | SAD 4.3 specifies 403 for non-admins, and 403 is the correct response for an authenticated but unauthorised user. The SRS and SAD differ here; the tests assert 403 |
| 2 | SRS 3.1 | A single admin panel | Two admin pages: Admin Slots and Admin Bookings | Each page has one clear job |
| 3 | SRS VPS-NF-002, TC-UX-01 | Register, book and check out are each reachable within 3 clicks from the dashboard | Book takes 2 clicks; check-out takes 3 including the new confirmation prompt; Register is reached from the login page because the dashboard needs a login | Confirmation prompt added from SAD 4.5. TC-UX-01 is a manual check still to be recorded |
| 4 | SAD 3.3, 4.1 | Separate `services/` layer (AuthModule, SlotModule, BookingModule, AdminModule) | Business logic sits in the route files, with shared helpers in `app/utils.py` | Single-facility scale; models, routes and templates are still separated (VPS-NF-005) |
| 5 | SAD 4.1 | `app.py` and `models.py` at the root | `app/` package with a `create_app()` factory | The factory lets every test build an isolated app with an in-memory database |
| 6 | SAD 4.1 | Route files: auth, booking, admin | Route files: auth, slots, bookings, vehicles, admin | Slot viewing/booking and booking history are separate concerns |
| 7 | SAD 4.3 | Login failure returns 401; invalid registration 400; duplicate email 409 | Form is shown again with status 200 and a flash message | Friendlier for server-rendered forms; message text is as specified |
| 8 | SAD 4.3 | Admin duplicate slot and remove-occupied-slot return 409 | Flash message and redirect or re-render; a failed slot creation is rolled back and shows a safe message | Admin pages kept simple |
| 9 | SAD 4.3 | Successful booking redirects to `/dashboard` | Redirects to `/history` | Shows the new booking and its check-in time straight away |
| 10 | SAD 4.3 | `/logout` accepts GET and POST | GET only | Plain navigation link |
| 11 | SAD 4.3 | Check-out of a completed booking returns 409 | Check-out and force check-out of a completed booking return 409 with a plain-text body ("Booking is already completed.") | No styled error page yet |
| 12 | SAD 4.5 | Navigation: Dashboard, Book, History, Logout, Admin Panel | Dashboard, My Bookings, My Vehicles, Admin Slots, Admin Bookings, Logout; booking starts by clicking an available slot | A separate Book link is not needed |
| 13 | SAD 3.5 (ADR-003) | Signed session cookie | Same, and `SECRET_KEY` must come from the environment (development fallback in `run.py` and `seed.py`); cookies are HttpOnly and SameSite=Lax | Avoids a hard-coded production secret |
| 14 | SAD 4.2 | `Slot` and `Vehicle.vehicle_number` | Classes/fields named `ParkingSlot` and `Vehicle.plate` (forms still use `vehicle_number`) | Naming only |

## 2. Additions beyond the documents

- **My Vehicles page (`/vehicles`):** customers register vehicles before booking; the booking form can use a registered vehicle (`vehicle_id`) or create a new one. Booking with another customer's vehicle returns 403.
- **Booking form page (`GET /book/<slot_id>`):** the SAD defines only `POST /book`.
- **Stronger double-booking guard:** the slot is claimed with a conditional database update and an active-booking check, and a concurrency test covers it (SAD 3.7 only asks for a single transaction).
- **Customers only can book:** admins get 403 on `/book` (matches the "Customer" access in SAD 4.3).
- **Extra validation:** name and email length limits, all-space passwords rejected, plate must contain a letter or digit.
- **Confirmation prompts and logging for forced check-out:** forced check-outs are logged with the admin id (SAD 4.4).
- **`seed.py`:** creates a demo admin, a demo customer and 30 slots; the SRS expects slots to be configured manually by an admin (SRS 2.5), which is still possible.
- **Full traceability:** the RTM sheet maps all 27 requirements, not only the 10 rows listed in SRS section 8.

## 3. Not yet implemented

- **Slot `vehicle_type`** shown on the dashboard and accepted in the admin add-slot form (SRS VPS-F-005 and VPS-F-015, SAD 4.2 and 4.3), tracked in issue #21
- Confirmation prompt before slot removal (#21); check-out and force check-out already have one
- Text labels (Available / Occupied) on the dashboard, not colour only (SAD 4.5)
- Index on slot floor and slot number (SAD 3.7)
- CSRF tokens (SAD 3.9); only the SameSite cookie setting is in place
- Logging of bookings and slot add/remove (login, logout, check-out failures, forced check-outs and slot-creation failures are logged)
- Periodic slot/booking consistency check (SAD 4.4, SRS VPS-NF-003); consistency is covered by TC-Rel-01 tests only
- Styled error pages for 403, 404, 409 and 500

## 4. Test Plan, schedule and documents

| # | Ref | Document says | Actual | Reason |
|---|---|---|---|---|
| 1 | Test Plan 7, SAD 3.1 | Build and test 15 to 23 September 2026 | Sprint 1 ran 19 to 23 October 2026; Sprint 2 is due 30 October 2026 | Course schedule moved; plan dates to be revised |
| 2 | Test Plan 6 | Defect log or Jira | GitHub Issues and the Projects board | Same repository as the code |
| 3 | Test Plan 5 | Unit, integration, system and UAT levels | Unit and integration tests (pytest, run by GitHub Actions on every push and pull request); system, UAT and usability checks (TC-UX-01) are manual | Sprint split |
| 4 | TC-Perf-01 | Dashboard responds within 2 seconds for 200 slots | Measured server-side with the Flask test client, not full browser rendering | Automated check inside CI |
| 5 | Test Plan 3 | Listed test case IDs only | Extra tests (concurrency, rollback on failure, logging, `SECRET_KEY`, cookie settings, vehicle ownership) are mapped to the nearest ID | Features added during development |
| 6 | Test Plan 5.1 | HTTPS checked for production deployment | Not tested | Production deployment is out of scope |
| 7 | SRS 6 | Exit criteria: the RTM shows all listed test cases passed | All automated cases pass; TC-UX-01 (manual) is still to be recorded | Manual check pending |
| 8 | SRS 8 | RTM status codes N / P / A | RTM sheet uses Pass / Fail / Not Run, filled from the pytest results | Clearer for automated results |
| 9 | SRS, SAD, Test Plan | Version 1.0, Draft | Not revised to match the final implementation; this document records the differences | Time |
