# Passeu 
An automatic optimal weekly generation scheme

# Coding ideas
Tuple data dictionary, something like (worker, shift, day): (hours, shift)

## Employee
Should have info on what's going all in all shifts. I.e. each has a full schedule

Attributes:
  - level
  - contract_weekly_hours
  - training_sessions
  - requests

Methods:
  - set_weekly_hours: based on days off from input data

## Constraints
Applied by day:
  - target total hours
  - target persons per shift
  - target person's level per shift

By shift:
  - training: hard constraint for x person to be with Y

### Other OR-Tools Refs

https://github.com/YooTimmy/restaurant_scheduler/blob/main/restaurant_scheduler.py
