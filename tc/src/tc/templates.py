"""Task template definitions for Texas real estate transaction coordination.

Ported from TC Tracker web app's task-templates.ts (61 templates).
Each template defines a task that may be auto-generated when a transaction is created.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from .models import Transaction


@dataclass
class TaskTemplate:
    id: str
    title: str
    description: str
    phase: str
    group_id: str
    due_date_offset: int          # calendar days from reference date
    due_date_reference: str       # "effective" | "closing" | "option_end"
    sort_order: int = 0
    is_conditional: bool = False
    condition: Optional[Callable[[Transaction], bool]] = None
    depends_on: list[str] = field(default_factory=list)


# --- Condition functions ---

def _is_financed(tx: Transaction) -> bool:
    return tx.is_financed is True

def _has_hoa(tx: Transaction) -> bool:
    return tx.has_hoa is True

def _has_mud(tx: Transaction) -> bool:
    return tx.has_mud is True

def _is_pre_1978(tx: Transaction) -> bool:
    return tx.is_pre_1978 is True

def _not_seller_disclosure_exempt(tx: Transaction) -> bool:
    return tx.is_seller_disclosure_exempt is not True


# --- Group definitions ---

TASK_GROUPS = {
    "file_setup":       {"name": "File Setup",               "description": "Save contract, enter dates, confirm contacts", "sort": 1},
    "earnest_money":    {"name": "Earnest Money",             "description": "EM instructions, delivery, and receipt", "sort": 2},
    "disclosures":      {"name": "Disclosures & Documents",   "description": "All TAR/HAR document requests and verifications", "sort": 3},
    "financing":        {"name": "Financing",                 "description": "Lender contact, appraisal, clear-to-close", "sort": 4},
    "title_survey":     {"name": "Title & Survey",            "description": "Title commitment, survey, T-47 affidavit", "sort": 5},
    "inspections":      {"name": "Inspections",               "description": "Schedule and confirm property inspections", "sort": 6},
    "option_deadlines": {"name": "Option Period Deadlines",   "description": "Option period tracking and amendments", "sort": 7},
    "closing_prep":     {"name": "Closing Prep",              "description": "Scheduling, settlement statement, walkthrough", "sort": 8},
    "closing":          {"name": "Closing Day",               "description": "Signing, funding, and final documents", "sort": 9},
    "post_closing":     {"name": "Post-Closing",              "description": "Recording, MLS update, and file archive", "sort": 10},
}


# =====================================================================
#  ALL 61 TASK TEMPLATES
# =====================================================================

TASK_TEMPLATES: list[TaskTemplate] = [

    # ===== DAY 0 - SAME DAY (9 templates) =====

    TaskTemplate(
        id="day_0_save_contract",
        title="Save fully executed contract to transaction file",
        description="Save the fully executed contract and all addenda to the transaction file for reference.",
        phase="day_0", group_id="file_setup",
        due_date_offset=0, due_date_reference="effective",
        sort_order=1,
    ),
    TaskTemplate(
        id="day_0_confirm_contacts",
        title="Confirm all contacts",
        description="Confirm contacts: buyer agent, listing agent, title/escrow, lender (if financed), and all parties.",
        phase="day_0", group_id="file_setup",
        due_date_offset=0, due_date_reference="effective",
        sort_order=2,
    ),
    TaskTemplate(
        id="day_0_enter_key_dates",
        title="Enter all key dates into tracker",
        description="Enter option end, earnest money due, closing, and financing/appraisal dates into your tracker.",
        phase="day_0", group_id="file_setup",
        due_date_offset=0, due_date_reference="effective",
        sort_order=3,
    ),
    TaskTemplate(
        id="day_0_send_to_title",
        title="Send executed contract to title company",
        description="Send the executed contract to title/escrow to open the title file.",
        phase="day_0", group_id="file_setup",
        due_date_offset=0, due_date_reference="effective",
        sort_order=4,
    ),
    TaskTemplate(
        id="day_0_confirm_title_received",
        title="Confirm title company received contract",
        description="Confirm that title/escrow has received the contract and is opening the file.",
        phase="day_0", group_id="file_setup",
        due_date_offset=0, due_date_reference="effective",
        sort_order=5,
    ),
    TaskTemplate(
        id="day_0_identify_financing",
        title="Document: Transaction is financed",
        description="This transaction involves third-party financing. Ensure lender contact and financing addendum are on file.",
        phase="day_0", group_id="file_setup",
        due_date_offset=0, due_date_reference="effective",
        sort_order=6,
        is_conditional=True, condition=_is_financed,
    ),
    TaskTemplate(
        id="day_0_identify_hoa",
        title="Document: Property has HOA",
        description="This property is subject to a Homeowners Association. Ensure HOA addendum (TAR-1922) is on file.",
        phase="day_0", group_id="file_setup",
        due_date_offset=0, due_date_reference="effective",
        sort_order=7,
        is_conditional=True, condition=_has_hoa,
    ),
    TaskTemplate(
        id="day_0_identify_mud",
        title="Document: Property is in a MUD",
        description="This property is in a Municipal Utility District. Ensure MUD disclosure (HAR-400) is on file.",
        phase="day_0", group_id="file_setup",
        due_date_offset=0, due_date_reference="effective",
        sort_order=8,
        is_conditional=True, condition=_has_mud,
    ),
    TaskTemplate(
        id="day_0_identify_pre1978",
        title="Document: Property built before 1978",
        description="This property was built before 1978. Ensure Lead-Based Paint disclosure (TAR-1906) is on file.",
        phase="day_0", group_id="file_setup",
        due_date_offset=0, due_date_reference="effective",
        sort_order=9,
        is_conditional=True, condition=_is_pre_1978,
    ),

    # ===== DAY 1 - WITHIN 24 HOURS (10 templates) =====

    TaskTemplate(
        id="day_1_em_instructions",
        title="Send earnest money delivery instructions",
        description="Send earnest money delivery instructions reminder to buyer agent/buyer.",
        phase="day_1", group_id="earnest_money",
        due_date_offset=1, due_date_reference="effective",
        sort_order=10,
    ),
    TaskTemplate(
        id="day_1_confirm_em_delivery",
        title="Confirm earnest money delivery plan",
        description="Ask buyer agent to confirm when and where earnest money will be delivered.",
        phase="day_1", group_id="earnest_money",
        due_date_offset=1, due_date_reference="effective",
        sort_order=11,
        depends_on=["day_1_em_instructions"],
    ),
    TaskTemplate(
        id="day_1_confirm_lender_info",
        title="Confirm lender contact information",
        description="Confirm lender name and loan officer contact information.",
        phase="day_1", group_id="financing",
        due_date_offset=1, due_date_reference="effective",
        sort_order=12,
        is_conditional=True, condition=_is_financed,
    ),
    TaskTemplate(
        id="day_1_lender_has_contract",
        title="Confirm lender has contract",
        description="Confirm lender has received the contract and has started the file.",
        phase="day_1", group_id="financing",
        due_date_offset=1, due_date_reference="effective",
        sort_order=13,
        is_conditional=True, condition=_is_financed,
    ),
    TaskTemplate(
        id="day_1_appraisal_status",
        title="Check appraisal order status",
        description="Confirm appraisal order status (ordered / pending / not yet).",
        phase="day_1", group_id="financing",
        due_date_offset=1, due_date_reference="effective",
        sort_order=14,
        is_conditional=True, condition=_is_financed,
    ),
    TaskTemplate(
        id="day_1_tar1901",
        title="Request TAR-1901 Third Party Financing Addendum",
        description="Request TAR-1901 Third Party Financing Addendum from agent if not already on file.",
        phase="day_1", group_id="disclosures",
        due_date_offset=1, due_date_reference="effective",
        sort_order=15,
        is_conditional=True, condition=_is_financed,
    ),
    TaskTemplate(
        id="day_1_tar1922_hoa",
        title="Request TAR-1922 HOA Addendum",
        description="Request TAR-1922 HOA Addendum from agent (notarized if required).",
        phase="day_1", group_id="disclosures",
        due_date_offset=1, due_date_reference="effective",
        sort_order=16,
        is_conditional=True, condition=_has_hoa,
    ),
    TaskTemplate(
        id="day_1_har400_mud",
        title="Request HAR-400 MUD Disclosure",
        description="Request HAR-400 MUD Disclosure from agent.",
        phase="day_1", group_id="disclosures",
        due_date_offset=1, due_date_reference="effective",
        sort_order=17,
        is_conditional=True, condition=_has_mud,
    ),
    TaskTemplate(
        id="day_1_tar1406_disclosure",
        title="Request TAR-1406 Seller's Disclosure",
        description="Request TAR-1406 Seller's Disclosure from listing agent.",
        phase="day_1", group_id="disclosures",
        due_date_offset=1, due_date_reference="effective",
        sort_order=18,
        is_conditional=True, condition=_not_seller_disclosure_exempt,
    ),
    TaskTemplate(
        id="day_1_tar1906_lead",
        title="Request TAR-1906 Lead-Based Paint Disclosure",
        description="Request TAR-1906 Lead-Based Paint Disclosure for pre-1978 property.",
        phase="day_1", group_id="disclosures",
        due_date_offset=1, due_date_reference="effective",
        sort_order=19,
        is_conditional=True, condition=_is_pre_1978,
    ),

    # ===== DAY 2 - 48 HOURS (2 templates) =====

    TaskTemplate(
        id="day_2_em_followup",
        title="Follow up on earnest money receipt",
        description="If no confirmation yet, follow up with buyer agent for earnest money receipt confirmation. If still unclear, prepare to contact title/escrow by end of business day.",
        phase="day_2", group_id="earnest_money",
        due_date_offset=2, due_date_reference="effective",
        sort_order=20,
        depends_on=["day_1_confirm_em_delivery"],
    ),
    TaskTemplate(
        id="day_2_doc_followup",
        title="Follow up on missing documents",
        description="Follow up for any still-missing executed addenda/disclosures requested on Day 1.",
        phase="day_2", group_id="disclosures",
        due_date_offset=2, due_date_reference="effective",
        sort_order=21,
    ),

    # ===== DAY 3 - EARNEST MONEY DEADLINE (3 templates) =====

    TaskTemplate(
        id="day_3_confirm_em_received",
        title="Confirm earnest money received by title",
        description="Obtain confirmation from title/escrow that earnest money is received (receipt/email).",
        phase="day_3", group_id="earnest_money",
        due_date_offset=3, due_date_reference="effective",
        sort_order=22,
        depends_on=["day_2_em_followup"],
    ),
    TaskTemplate(
        id="day_3_save_em_receipt",
        title="Save earnest money receipt",
        description="Save proof of earnest money receipt in transaction file.",
        phase="day_3", group_id="earnest_money",
        due_date_offset=3, due_date_reference="effective",
        sort_order=23,
        depends_on=["day_3_confirm_em_received"],
    ),
    TaskTemplate(
        id="day_3_escalate_if_needed",
        title="Escalate if earnest money not received",
        description="If earnest money not received, notify agent(s) and document escalation steps.",
        phase="day_3", group_id="earnest_money",
        due_date_offset=3, due_date_reference="effective",
        sort_order=24,
    ),

    # ===== OPTION PERIOD (8 templates) =====

    TaskTemplate(
        id="option_schedule_inspection",
        title="Schedule inspection(s)",
        description="Schedule property inspection(s). Must be completed before option period ends.",
        phase="option_period", group_id="inspections",
        due_date_offset=3, due_date_reference="effective",
        sort_order=25,
    ),
    TaskTemplate(
        id="option_confirm_inspection",
        title="Confirm inspection(s) completed",
        description="Confirm that all scheduled inspections have been completed.",
        phase="option_period", group_id="inspections",
        due_date_offset=-2, due_date_reference="option_end",
        sort_order=26,
        depends_on=["option_schedule_inspection"],
    ),
    TaskTemplate(
        id="option_track_repairs",
        title="Track repair requests and amendments",
        description="Track repair requests, amendments, and credits. Collect executed documents.",
        phase="option_period", group_id="inspections",
        due_date_offset=-1, due_date_reference="option_end",
        sort_order=27,
    ),
    TaskTemplate(
        id="option_survey_status",
        title="Determine survey status",
        description="Determine if seller has existing survey (obtain copy, verify usability) or if new survey is required.",
        phase="option_period", group_id="title_survey",
        due_date_offset=5, due_date_reference="effective",
        sort_order=28,
    ),
    TaskTemplate(
        id="option_t47_affidavit",
        title="Obtain T-47 affidavit",
        description="Obtain T-47 affidavit. Confirm completed and notarized if required.",
        phase="option_period", group_id="title_survey",
        due_date_offset=-3, due_date_reference="option_end",
        sort_order=29,
    ),
    TaskTemplate(
        id="option_deliver_survey",
        title="Deliver survey and T-47 to title and lender",
        description="Deliver survey and T-47 to title company and lender (if financed).",
        phase="option_period", group_id="title_survey",
        due_date_offset=-2, due_date_reference="option_end",
        sort_order=30,
        depends_on=["option_survey_status", "option_t47_affidavit"],
    ),
    TaskTemplate(
        id="option_request_title_commitment",
        title="Request title commitment",
        description="Request Title Commitment from title company.",
        phase="option_period", group_id="title_survey",
        due_date_offset=5, due_date_reference="effective",
        sort_order=31,
    ),
    TaskTemplate(
        id="option_save_title_commitment",
        title="Save and distribute title commitment",
        description="Save title commitment to file and send to agent(s) as needed. Track any title issue follow-ups.",
        phase="option_period", group_id="title_survey",
        due_date_offset=7, due_date_reference="effective",
        sort_order=32,
        depends_on=["option_request_title_commitment"],
    ),

    # ===== OPTION DEADLINE - 2-5 DAYS BEFORE OPTION ENDS (3 templates) =====

    TaskTemplate(
        id="option_confirm_inspection_scheduled",
        title="Confirm inspection is scheduled/completed",
        description="Option deadline protection: Confirm inspection is scheduled or already completed.",
        phase="option_deadline", group_id="option_deadlines",
        due_date_offset=-5, due_date_reference="option_end",
        sort_order=33,
        depends_on=["option_schedule_inspection"],
    ),
    TaskTemplate(
        id="option_confirm_amendments",
        title="Confirm amendments are executed",
        description="Confirm any negotiated amendments are drafted and executed before option end.",
        phase="option_deadline", group_id="option_deadlines",
        due_date_offset=-2, due_date_reference="option_end",
        sort_order=34,
    ),
    TaskTemplate(
        id="option_remind_deadline",
        title="Remind agents of option deadline",
        description="Remind agent(s) of option deadline and any required actions.",
        phase="option_deadline", group_id="option_deadlines",
        due_date_offset=-2, due_date_reference="option_end",
        sort_order=35,
    ),

    # ===== POST-OPTION (2 templates) =====

    TaskTemplate(
        id="post_option_confirm_status",
        title="Confirm past option status",
        description="Confirm file status is 'past option' with no further option actions pending.",
        phase="post_option", group_id="option_deadlines",
        due_date_offset=1, due_date_reference="option_end",
        sort_order=36,
    ),
    TaskTemplate(
        id="post_option_closing_scheduling",
        title="Confirm closing scheduling underway",
        description="Confirm closing scheduling is underway - don't wait until closing week.",
        phase="post_option", group_id="option_deadlines",
        due_date_offset=1, due_date_reference="option_end",
        sort_order=37,
    ),

    # ===== FINANCING / APPRAISAL WINDOW (4 templates) =====

    TaskTemplate(
        id="financing_appraisal_ordered",
        title="Confirm appraisal is ordered",
        description="Confirm the appraisal has been ordered by the lender.",
        phase="financing", group_id="financing",
        due_date_offset=7, due_date_reference="effective",
        sort_order=38,
        is_conditional=True, condition=_is_financed,
    ),
    TaskTemplate(
        id="financing_track_appraisal",
        title="Track appraisal appointment",
        description="Track appraisal appointment window/date (often drive-by).",
        phase="financing", group_id="financing",
        due_date_offset=10, due_date_reference="effective",
        sort_order=39,
        is_conditional=True, condition=_is_financed,
    ),
    TaskTemplate(
        id="financing_notify_seller",
        title="Notify seller of appraisal timing",
        description="Notify seller of appraisal timing if property access is needed.",
        phase="financing", group_id="financing",
        due_date_offset=10, due_date_reference="effective",
        sort_order=40,
        is_conditional=True, condition=_is_financed,
    ),
    TaskTemplate(
        id="financing_appraisal_completed",
        title="Confirm appraisal completed",
        description="Confirm the appraisal has been completed and received by lender.",
        phase="financing", group_id="financing",
        due_date_offset=14, due_date_reference="effective",
        sort_order=41,
        is_conditional=True, condition=_is_financed,
    ),

    # ===== PRE-CLOSING - 10-14 DAYS BEFORE CLOSING (3 templates) =====

    TaskTemplate(
        id="pre_closing_schedule",
        title="Schedule closing appointment",
        description="Schedule closing appointment with title company (date/time/location).",
        phase="pre_closing", group_id="closing_prep",
        due_date_offset=-14, due_date_reference="closing",
        sort_order=42,
    ),
    TaskTemplate(
        id="pre_closing_confirm_attendees",
        title="Confirm who is attending closing",
        description="Confirm who is attending / signing (in person / remote / mail-away if applicable).",
        phase="pre_closing", group_id="closing_prep",
        due_date_offset=-10, due_date_reference="closing",
        sort_order=43,
    ),
    TaskTemplate(
        id="pre_closing_underwriting",
        title="Confirm lender on track for clear-to-close",
        description="Confirm lender is on track for underwriting and clear-to-close.",
        phase="pre_closing", group_id="financing",
        due_date_offset=-10, due_date_reference="closing",
        sort_order=44,
        is_conditional=True, condition=_is_financed,
    ),

    # ===== SETTLEMENT - 3+ DAYS BEFORE CLOSING (5 templates) =====

    TaskTemplate(
        id="settlement_request_cd",
        title="Request settlement statement / closing disclosure",
        description="Request and receive Settlement Statement / CD / HUD from title company.",
        phase="settlement", group_id="closing_prep",
        due_date_offset=-5, due_date_reference="closing",
        sort_order=45,
    ),
    TaskTemplate(
        id="settlement_review_cd",
        title="Review settlement statement for issues",
        description="Review settlement statement for obvious issues (names, fees, credits, prorations).",
        phase="settlement", group_id="closing_prep",
        due_date_offset=-3, due_date_reference="closing",
        sort_order=46,
        depends_on=["settlement_request_cd"],
    ),
    TaskTemplate(
        id="settlement_distribute_cd",
        title="Send settlement statement to parties",
        description="Send settlement statement to agent(s)/parties as required and log delivery.",
        phase="settlement", group_id="closing_prep",
        due_date_offset=-3, due_date_reference="closing",
        sort_order=47,
        depends_on=["settlement_request_cd", "settlement_review_cd"],
    ),
    TaskTemplate(
        id="settlement_funding_plan",
        title="Confirm funding method",
        description="Confirm funding method and any wire instructions procedures.",
        phase="settlement", group_id="closing_prep",
        due_date_offset=-3, due_date_reference="closing",
        sort_order=48,
    ),
    TaskTemplate(
        id="settlement_disbursement",
        title="Confirm disbursement expectations",
        description="Confirm any disbursement checks/wires expectations with title.",
        phase="settlement", group_id="closing_prep",
        due_date_offset=-3, due_date_reference="closing",
        sort_order=49,
    ),

    # ===== CLOSING WEEK (4 templates) =====

    TaskTemplate(
        id="closing_week_ctc",
        title="Confirm lender clear-to-close",
        description="Confirm lender has issued clear-to-close.",
        phase="closing_week", group_id="financing",
        due_date_offset=-5, due_date_reference="closing",
        sort_order=50,
        is_conditional=True, condition=_is_financed,
    ),
    TaskTemplate(
        id="closing_week_walkthrough",
        title="Confirm final walk-through scheduled",
        description="Confirm final walk-through scheduling with buyer.",
        phase="closing_week", group_id="closing_prep",
        due_date_offset=-2, due_date_reference="closing",
        sort_order=51,
    ),
    TaskTemplate(
        id="closing_week_docs_complete",
        title="Confirm all documents executed",
        description="Confirm all documents are fully executed and filed.",
        phase="closing_week", group_id="closing_prep",
        due_date_offset=-1, due_date_reference="closing",
        sort_order=52,
    ),
    TaskTemplate(
        id="closing_week_appointment",
        title="Confirm closing appointment details",
        description="Confirm closing appointment details with all parties.",
        phase="closing_week", group_id="closing_prep",
        due_date_offset=-1, due_date_reference="closing",
        sort_order=53,
    ),

    # ===== CLOSING DAY (3 templates) =====

    TaskTemplate(
        id="closing_day_signing",
        title="Confirm signing completed",
        description="Confirm all parties have completed signing.",
        phase="closing_day", group_id="closing",
        due_date_offset=0, due_date_reference="closing",
        sort_order=54,
    ),
    TaskTemplate(
        id="closing_day_funding",
        title="Confirm funding status",
        description="Confirm funding status with title (funded / pending).",
        phase="closing_day", group_id="closing",
        due_date_offset=0, due_date_reference="closing",
        sort_order=55,
        depends_on=["closing_day_signing"],
    ),
    TaskTemplate(
        id="closing_day_save_docs",
        title="Save final signed documents",
        description="Save final signed documents to file as received.",
        phase="closing_day", group_id="closing",
        due_date_offset=0, due_date_reference="closing",
        sort_order=56,
        depends_on=["closing_day_signing"],
    ),

    # ===== POST-CLOSING (5 templates) =====

    TaskTemplate(
        id="post_closing_funded",
        title="Confirm transaction funded and recorded",
        description="Confirm transaction has funded and is recorded (when applicable).",
        phase="post_closing", group_id="post_closing",
        due_date_offset=1, due_date_reference="closing",
        sort_order=57,
        depends_on=["closing_day_funding"],
    ),
    TaskTemplate(
        id="post_closing_final_package",
        title="Obtain final closing package",
        description="Obtain final closing package and final settlement statement from title.",
        phase="post_closing", group_id="post_closing",
        due_date_offset=1, due_date_reference="closing",
        sort_order=58,
        depends_on=["closing_day_save_docs"],
    ),
    TaskTemplate(
        id="post_closing_mls",
        title="Update MLS status to Closed",
        description="Update MLS status to Closed (coordinate with agent).",
        phase="post_closing", group_id="post_closing",
        due_date_offset=1, due_date_reference="closing",
        sort_order=59,
    ),
    TaskTemplate(
        id="post_closing_mls_printout",
        title="Save MLS printout showing Closed",
        description="Save MLS printout showing Closed status.",
        phase="post_closing", group_id="post_closing",
        due_date_offset=2, due_date_reference="closing",
        sort_order=60,
        depends_on=["post_closing_mls"],
    ),
    TaskTemplate(
        id="post_closing_archive",
        title="Archive complete file",
        description="Archive complete file including: executed contract + all addenda/amendments, earnest money receipt, title commitment, survey + T-47, inspection docs, settlement statement, and disbursement confirmations.",
        phase="post_closing", group_id="post_closing",
        due_date_offset=3, due_date_reference="closing",
        sort_order=61,
        depends_on=["post_closing_funded", "post_closing_final_package", "post_closing_mls_printout"],
    ),
]
