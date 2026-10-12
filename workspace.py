"""Fictional Mastercard Teams workspace for the Spot demo. Owner: Contributor 1.

Data only, no logic. All people, conversations and decisions are fictional.
Locations are "channel:<channel_id>" or "chat:<chat_id>". Proposal IDs match
the fixed seed data in CONTRACTS.md / seed.py.
"""

ORG_NAME = "Mastercard"

PROPOSAL_UAE_IDENTITY = "3f2b8c1e-7a4d-4e9b-9c2f-5d1a6b8e0c47"
PROPOSAL_UAE_GATEWAY = "a91d4f60-2c3b-4b7e-8f15-6e0c9d2b7a38"

SPOT_BOT = {
    "name": "spot", "display_name": "Spot", "title": "Requirements version control (app)",
    "team": None, "role": "Bot", "avatar_color": "#5B5FC7",
}

ALL_USERS = ["priya.raman", "marcus.chen", "elena.rossi", "daniel.okafor", "sofia.alvarez",
             "james.whitfield", "aisha.karimi", "tomas.novak", "hannah.brooks", "ravi.menon"]

# Users who only see some channels of a team they belong to.
CHANNEL_RESTRICTIONS = {
    "hannah.brooks": ["arp-general", "arp-onboarding"],
}

TEAMS = [
    {"id": "arp", "name": "Autonomous Region Program", "avatar_color": "#5B5FC7",
     "members": ALL_USERS,
     "channels": [
         {"id": "arp-general", "name": "General"},
         {"id": "arp-announcements", "name": "Announcements"},
         {"id": "arp-program-office", "name": "Program Office"},
         {"id": "arp-scope", "name": "Scope & Requirements"},
         {"id": "arp-cutover", "name": "Cutover Planning"},
         {"id": "arp-onboarding", "name": "Onboarding"},
     ]},
    {"id": "ops", "name": "Operations Automation", "avatar_color": "#0F6CBD",
     "members": ["priya.raman", "marcus.chen", "ravi.menon"],
     "channels": [
         {"id": "ops-general", "name": "General"},
         {"id": "ops-tfe", "name": "Terraform Enterprise"},
         {"id": "ops-config", "name": "Config Management (Chef & Ansible)"},
         {"id": "ops-platform-versions", "name": "Platform Versions"},
         {"id": "ops-intake", "name": "Intake Requests"},
     ]},
    {"id": "pay", "name": "Payments Platform", "avatar_color": "#0E700E",
     "members": ["elena.rossi", "daniel.okafor"],
     "channels": [
         {"id": "pay-general", "name": "General"},
         {"id": "pay-gateway", "name": "Gateway"},
         {"id": "pay-identity", "name": "Identity Service Integration"},
         {"id": "pay-release", "name": "Release Readiness"},
     ]},
    {"id": "infosec", "name": "Information Security", "avatar_color": "#4F6BED",
     "members": ["james.whitfield"],
     "channels": [
         {"id": "infosec-general", "name": "General"},
         {"id": "infosec-access", "name": "Access Reviews"},
         {"id": "infosec-residency", "name": "Data Residency"},
     ]},
    {"id": "net", "name": "Network Engineering", "avatar_color": "#038387",
     "members": ["tomas.novak"],
     "channels": [
         {"id": "net-general", "name": "General"},
         {"id": "net-connectivity", "name": "Region Connectivity"},
     ]},
    {"id": "legal", "name": "Compliance & Legal", "avatar_color": "#CA5010",
     "members": ["aisha.karimi"],
     "channels": [
         {"id": "legal-general", "name": "General"},
         {"id": "legal-regulatory", "name": "Regulatory Requirements"},
     ]},
]

CHATS = [
    {"id": "cutover-sync", "name": "Cutover sync (call recap)", "kind": "group",
     # Ops Automation was not on the call; Sofia adds Marcus and Priya the next day.
     "members": ["sofia.alvarez", "daniel.okafor", "tomas.novak", "marcus.chen", "priya.raman"]},
    {"id": "gateway-readiness", "name": "UAE gateway readiness", "kind": "group",
     "members": ["daniel.okafor", "marcus.chen", "ravi.menon", "tomas.novak", "elena.rossi"]},
    {"id": "program-leads", "name": "Program leads", "kind": "group",
     "members": ["sofia.alvarez", "priya.raman", "daniel.okafor", "aisha.karimi"]},
    {"id": "dm-sofia-priya", "name": None, "kind": "oneOnOne",
     "members": ["sofia.alvarez", "priya.raman"]},
    {"id": "dm-hannah-ravi", "name": None, "kind": "oneOnOne",
     "members": ["hannah.brooks", "ravi.menon"]},
]


def _m(message_id, location, author, timestamp, text, thread_parent_id=None,
       mentions_spot=False, proposal_id=None):
    return {"message_id": message_id, "location": location, "author": author,
            "timestamp": timestamp, "text": text, "thread_parent_id": thread_parent_id,
            "mentions_spot": mentions_spot, "proposal_id": proposal_id}


MESSAGES = [
    # Program kickoff
    _m("m01", "channel:arp-announcements", "sofia.alvarez", "2026-09-29T08:00:00Z",
       "Welcome to the Autonomous Region Program. First region is the UAE: in-region identity and "
       "payment gateway services go live in November. Scope docs live with each owning team. "
       "Questions go in Scope & Requirements."),
    _m("m02", "channel:arp-general", "tomas.novak", "2026-09-29T09:15:00Z",
       "Heads up: UAE region link tests are scheduled for next week. I'll post results in Region Connectivity."),

    # Scattered requirements
    _m("m03", "channel:infosec-residency", "james.whitfield", "2026-09-30T10:05:00Z",
       "Data residency requirement for the UAE region: identity verification data and its backups must "
       "stay in-region. No cross-region replication for PII tables, and logs are scrubbed before they leave the region."),
    _m("m04", "channel:infosec-residency", "ravi.menon", "2026-09-30T10:40:00Z",
       "Does that include Terraform state? Some resource tags carry merchant IDs.", thread_parent_id="m03"),
    _m("m05", "channel:infosec-residency", "james.whitfield", "2026-09-30T11:02:00Z",
       "Yes. Keep TF state for UAE workspaces in-region.", thread_parent_id="m03"),
    _m("m06", "channel:legal-regulatory", "aisha.karimi", "2026-10-01T08:30:00Z",
       "Regulatory note for the UAE launch: cardholder identity records must be retained in-country for "
       "five years, with an audit trail of who approved each scope change."),
    _m("m07", "channel:ops-platform-versions", "priya.raman", "2026-10-01T13:20:00Z",
       "FW: Minimum platform versions for new regions\n"
       "---------- Forwarded message ----------\n"
       "From: Platform Engineering\n"
       "Subject: Minimum platform versions for new regions\n\n"
       "All new-region workspaces must run Terraform 1.7 or later with AWS provider 5.x. "
       "Workspaces on 1.5 will not be approved for production.\n"
       "----------\n"
       "Who's tracking this for the UAE workspaces?"),
    _m("m08", "channel:ops-platform-versions", "marcus.chen", "2026-10-01T13:45:00Z",
       "Me. The UAE identity workspaces are on 1.5 today. Upgrade is on my list for next sprint.",
       thread_parent_id="m07"),
    _m("m09", "channel:ops-tfe", "marcus.chen", "2026-10-02T16:10:00Z",
       "TFE workspace uae-identity-prod is created. Plans run green on 1.5; bumping to 1.7 next sprint."),
    _m("m10", "channel:ops-general", "ravi.menon", "2026-10-02T17:00:00Z",
       "Reminder: cutover runbook review Thursday 10:00 GST."),
    _m("m11", "channel:pay-identity", "daniel.okafor", "2026-10-03T09:00:00Z",
       "Payments needs the identity service live before settlement can move. Our integration tests are "
       "pinned to the November 14 cutover."),
    _m("m12", "channel:legal-general", "aisha.karimi", "2026-10-03T11:30:00Z",
       "Reminder: every scope change for the UAE launch needs a named approver for the audit trail."),
    _m("m13", "channel:pay-gateway", "elena.rossi", "2026-10-05T10:15:00Z",
       "Question for Ops: is the UAE gateway plan still the one in the requirements doc? "
       "Release Readiness assumes it."),
    _m("m14", "channel:net-connectivity", "tomas.novak", "2026-10-06T15:00:00Z",
       "UAE link certification slipped to November 10. Raising it at the cutover sync."),
    _m("m15", "channel:infosec-access", "james.whitfield", "2026-10-07T09:00:00Z",
       "Quarterly access review for UAE workspaces is due October 20."),
    _m("m16", "chat:program-leads", "aisha.karimi", "2026-10-07T14:00:00Z",
       "For the audit trail: please don't treat call decisions as final until they're written down and approved."),
    _m("m17", "channel:arp-cutover", "priya.raman", "2026-10-08T12:00:00Z",
       "Ops cutover runbook v3 is posted. UAE identity service cutover: November 14."),
    _m("m18", "channel:pay-release", "daniel.okafor", "2026-10-08T16:30:00Z",
       "Release readiness review moved to October 14."),

    # The decision Ops Automation wasn't part of
    _m("m19", "chat:cutover-sync", "sofia.alvarez", "2026-10-09T15:10:00Z",
       "Thanks all. Recap of today's cutover sync below."),
    _m("m20", "chat:cutover-sync", "daniel.okafor", "2026-10-09T15:12:00Z",
       "Decision from the call: the UAE identity service cutover is moving two weeks, from November 14 "
       "to November 28. Network needs the time for link certification. Payments will re-pin our tests."),
    _m("m21", "chat:cutover-sync", "tomas.novak", "2026-10-09T15:14:00Z",
       "Confirmed from Network. Certification lands November 10."),
    _m("m22", "chat:cutover-sync", "sofia.alvarez", "2026-10-09T15:20:00Z",
       "Great. I'll let the wider program know."),

    # The angry ping
    _m("m23", "channel:arp-program-office", "sofia.alvarez", "2026-10-10T09:05:00Z",
       "Ops Automation, why aren't you ready for the new UAE identity cutover date? Payments moved to "
       "November 28 and your runbook still says November 14."),
    _m("m24", "channel:arp-program-office", "priya.raman", "2026-10-10T09:08:00Z",
       "This is the first we're hearing of a new date. Nobody from Ops was on that call. Where was it decided?",
       thread_parent_id="m23"),
    _m("m25", "channel:arp-program-office", "sofia.alvarez", "2026-10-10T09:10:00Z",
       "Yesterday's cutover sync. Adding you and Marcus to the recap chat now.", thread_parent_id="m23"),
    _m("m26", "chat:cutover-sync", "system", "2026-10-10T09:11:00Z",
       "Sofia Alvarez added Marcus Chen and Priya Raman to the chat and shared all chat history."),

    # Spot in action
    _m("m27", "chat:cutover-sync", "marcus.chen", "2026-10-10T09:20:00Z",
       "@Spot add", thread_parent_id="m20", mentions_spot=True),
    _m("m28", "chat:cutover-sync", "spot", "2026-10-10T09:20:05Z",
       "Proposal created: UAE identity service cutover moved two weeks. "
       "Routed to Payments (depends on Ops Automation).",
       thread_parent_id="m20", proposal_id=PROPOSAL_UAE_IDENTITY),
    _m("m29", "chat:dm-sofia-priya", "sofia.alvarez", "2026-10-10T09:30:00Z",
       "Sorry for the ping earlier. I should have looped Ops into the sync."),
    _m("m30", "chat:dm-sofia-priya", "priya.raman", "2026-10-10T09:34:00Z",
       "No worries. Marcus captured it in Spot, so it's on record once Payments approves."),

    # The unsigned proposal
    _m("m31", "chat:gateway-readiness", "tomas.novak", "2026-10-10T14:00:00Z",
       "If identity moves out, can the gateway go a week earlier? The link is ready for gateway traffic sooner."),
    _m("m32", "chat:gateway-readiness", "ravi.menon", "2026-10-10T14:04:00Z",
       "Works for Ops if Payments signs off."),
    _m("m33", "chat:gateway-readiness", "marcus.chen", "2026-10-10T14:07:00Z",
       "@Spot add Move UAE gateway cutover up one week", thread_parent_id="m31", mentions_spot=True),
    _m("m34", "chat:gateway-readiness", "spot", "2026-10-10T14:07:05Z",
       "Proposal created: Move UAE gateway cutover up one week. "
       "Routed to Payments (depends on Ops Automation).",
       thread_parent_id="m31", proposal_id=PROPOSAL_UAE_GATEWAY),
    _m("m35", "chat:gateway-readiness", "daniel.okafor", "2026-10-11T08:50:00Z",
       "Let's hold the gateway change until the identity cutover is settled."),

    # Onboarding confusion
    _m("m36", "channel:arp-onboarding", "hannah.brooks", "2026-10-11T10:00:00Z",
       "Hi everyone, I'm Hannah, the new project coordinator. Where is the project template, and who owns "
       "what for the UAE region?"),
    _m("m37", "channel:arp-onboarding", "ravi.menon", "2026-10-11T10:12:00Z",
       "Welcome! The template is in Files, but heads up: it's empty. Ownership is mostly in people's heads "
       "and spread across channels.", thread_parent_id="m36"),
    _m("m38", "channel:arp-onboarding", "sofia.alvarez", "2026-10-11T10:20:00Z",
       "We're piloting Spot to fix exactly this. Approved scope and its history live there.",
       thread_parent_id="m36"),
    _m("m39", "chat:dm-hannah-ravi", "hannah.brooks", "2026-10-11T10:30:00Z",
       "Thanks for the heads-up on the template. Who decides on the gateway date?"),
    _m("m40", "chat:dm-hannah-ravi", "ravi.menon", "2026-10-11T10:34:00Z",
       "Anything Payments depends on needs a Payments approver. That's Daniel."),
]
