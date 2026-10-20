---
name: booking-management
description: Create, cancel, and check bookings with mandatory confirmation before sensitive actions.
---

# Skill: booking-management

## Owner
`booking-agent` only.

## When to use
- Task asks to book a flight/hotel, cancel a booking, or check booking status.

## Required inputs
- For booking: `booking_type` (flight|hotel), `item_id`, `user_name`
- For hotels: `check_in`, `check_out`, `rooms`
- For cancel/status: `booking_id` (or user_name for list)

## Steps — create
1. Restate the selected option and total price if available in the task.
2. Call `create_booking` only when the task clearly includes user confirmation.
3. Return `booking_id` and status.

## Steps — cancel / status
1. For cancel: call `cancel_booking` only with clear confirmation in the task.
2. For status: `get_booking` or `list_bookings`.

## Tools
- `create_booking`
- `cancel_booking`
- `get_booking`
- `list_bookings`

## Errors
- If confirmation is missing, do not call create/cancel; report that confirmation is required.
- If item_id/booking_id is invalid, say so; do not invent replacements.
