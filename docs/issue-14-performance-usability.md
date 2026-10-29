# Issue #14: Performance and Usability Test Report

**Date:** 2026-10-29
**Project:** Vehicle Parking System
**Test IDs:** TC-Perf-01, TC-UX-01

## 1. Test Environment

- Environment: Local development on macOS
- Application: Flask Vehicle Parking System
- Performance measurement: Flask test client using `time.perf_counter()`
- Performance test data: 200 parking slots
- Usability testing: Manual browser verification

## 2. TC-Perf-01 — Dashboard Response Time

**Requirement:** The dashboard must respond within 2 seconds when loaded
with 200 parking slots.

The automated test
`test_dashboard_performance_200_slots` was executed five times.

| Run | Measured response time | Result |
|---|---:|---|
| 1 | 0.0073 seconds | Pass |
| 2 | 0.0082 seconds | Pass |
| 3 | 0.0077 seconds | Pass |
| 4 | 0.0082 seconds | Pass |
| 5 | 0.0086 seconds | Pass |
| Average | 0.0080 seconds | Pass |

**Result: PASS.** All five runs were below the 2-second threshold.

**Measurement limitation:** Timings measure the Flask test-client request
on the local development environment. They do not include full browser
rendering, network latency, or production deployment overhead.

## 3. TC-UX-01 — Core Actions Within Three Clicks

**Requirement:** Booking, checkout, history, and admin add must each be
reachable within three clicks.

Manual browser checks were reported as passing for all four actions.

| Core action | Observed result | Status |
|---|---|---|
| Booking and check-in | Completed in 2 clicks | Pass |
| Checkout | Completed in 2 clicks | Pass |
| Booking history | Within 3 clicks | Pass |
| Admin add action | Within 3 clicks; page checked successfully | Pass |

## 4. Summary

- TC-Perf-01: PASS — five measured runs met the response-time requirement.
- TC-UX-01: PASS — all four core actions met the three-click criterion
  during manual verification.

The performance result applies to the local Flask test-client environment.
Additional browser-based and production-environment performance testing
may be needed to assess end-to-end user experience.
