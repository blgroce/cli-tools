"""Constants and valid values for TC CLI."""

VALID_STATUSES = {"draft", "active", "under_option", "pending", "closed", "terminated"}
VALID_TYPES = {"buyer", "seller", "dual"}
VALID_TASK_STATUSES = {"pending", "in_progress", "completed", "skipped"}
VALID_PERSON_ROLES = {
    "buyer", "seller", "buyer_agent", "listing_agent",
    "lender_contact", "title_contact", "inspector", "appraiser", "other",
}
VALID_DOC_TYPES = {
    "contract", "addendum", "disclosure", "earnest_money",
    "title", "survey", "inspection", "closing", "other",
}
VALID_DOC_STATUSES = {"needed", "requested", "received", "reviewed", "filed"}
VALID_PHASES = {
    "day_0", "day_1", "day_2", "day_3",
    "option_period", "option_deadline", "post_option",
    "financing", "pre_closing", "settlement",
    "closing_week", "closing_day", "post_closing",
}

PHASE_DISPLAY_NAMES = {
    "day_0": "Day 0 - Same Day",
    "day_1": "Day 1 - Within 24 Hours",
    "day_2": "Day 2 - 48 Hours",
    "day_3": "Day 3 - Earnest Money Deadline",
    "option_period": "During Option Period",
    "option_deadline": "2-5 Days Before Option Ends",
    "post_option": "After Option Period",
    "financing": "Financing / Appraisal Window",
    "pre_closing": "10-14 Days Before Closing",
    "settlement": "3+ Days Before Closing",
    "closing_week": "Week of Closing",
    "closing_day": "Day of Closing",
    "post_closing": "Post-Closing",
}

PHASE_ORDER = {
    "day_0": 1, "day_1": 2, "day_2": 3, "day_3": 4,
    "option_period": 5, "option_deadline": 6, "post_option": 7,
    "financing": 8, "pre_closing": 9, "settlement": 10,
    "closing_week": 11, "closing_day": 12, "post_closing": 13,
}

VALID_TIMELINE_EVENTS = {
    "created", "updated", "status_changed", "person_added", "person_updated",
    "task_completed", "task_skipped", "task_added",
    "doc_added", "doc_updated", "note_added",
}
