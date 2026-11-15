"""Role-based access control definitions. Seeded into the roles/permissions tables
and enforced in backend endpoints (never only by hiding buttons in the UI)."""

ALL_PERMISSIONS: dict[str, str] = {
    "portal.customer": "Use the overseas customer portal",
    "portal.provider": "Use the provider portal",
    "enquiry.manage": "View and update public enquiries",
    "customer.read_all": "Read all customer/family records",
    "customer.write": "Edit customer/family records",
    "consent.record": "Record parent consent and activate authorisations",
    "provider.read": "Read provider directory",
    "provider.manage": "Onboard/edit providers",
    "provider.verify": "Review provider documents and verify providers",
    "catalogue.manage": "Manage services, areas, pricing and packages",
    "request.read_all": "Read all service requests",
    "request.manage": "Review requests, quote, transition status",
    "assignment.manage": "Assign providers",
    "approval_exception.grant": "Grant a documented approval exception",
    "evidence.review": "View evidence uploaded for any request",
    "incident.manage": "Manage incidents and complaints",
    "billing.manage": "Create invoices, record payments",
    "refund.approve": "Approve refunds",
    "payout.approve": "Approve provider payouts",
    "reports.view": "View operational and financial reports",
    "audit.view": "View the audit trail",
    "staff.manage": "Create and manage staff users",
}

SUPPORT_PERMISSIONS = {
    "enquiry.manage", "customer.read_all", "customer.write", "consent.record", "provider.read",
    "request.read_all", "request.manage", "assignment.manage", "evidence.review",
    "incident.manage", "billing.manage", "reports.view",
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "customer": {"portal.customer"},
    "provider": {"portal.provider"},
    "support": SUPPORT_PERMISSIONS,
    "admin": set(ALL_PERMISSIONS) - {"portal.customer", "portal.provider"},
}

STAFF_ROLES = {"support", "admin"}
