---
name: booking-management
description: Create, cancel, and check bookings with mandatory user confirmation before sensitive actions.
---

# Skill: booking-management

## When to use
- User asks to book a flight/hotel, cancel a booking, or check booking status.

## Required inputs
- For booking: `booking_type` (flight|hotel), `item_id`, `user_name`
- For hotels: `check_in`, `check_out`, `rooms`
- For cancel/status: `booking_id`

## Steps — create
1. Restate the selected option and total price.
2. Ask explicitly: "Do you confirm this booking?"
3. Only after clear confirmation, call `create_booking`.
4. Return `booking_id` and status.

## Steps — cancel / status
1. For cancel: get confirmation, then `cancel_booking`.
2. For status: `get_booking` or `list_bookings`.

## Tools
- `create_booking`
- `cancel_booking`
- `get_booking`
- `list_bookings`

## Errors
- Never create/cancel without user confirmation.
- If item_id is invalid, reuse ids from the latest search results.
