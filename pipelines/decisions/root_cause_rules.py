"""
Root Cause Rules: Maps ticket text to root cause classes.
Rules-first approach (keyword matching) before ML.
"""

from domain.enums import RootCauseClass
from domain.policies import ROOT_CAUSE_CLASSES


def classify_root_cause(
    title: str, description: str = "", request_type: str = ""
) -> tuple[RootCauseClass, float]:
    """
    Classify a ticket into a root cause class using keyword matching.
    Returns (class, confidence) where confidence is 0.0–1.0.
    """
    text = f"{title} {description} {request_type}".lower()

    scores: dict[RootCauseClass, float] = {}

    for cause_class, keywords in ROOT_CAUSE_CLASSES.items():
        if cause_class == RootCauseClass.UNKNOWN:
            continue
        score = sum(1 for kw in keywords if kw.lower() in text)
        if score > 0:
            scores[RootCauseClass(cause_class)] = min(score / len(keywords), 1.0)

    if not scores:
        return RootCauseClass.UNKNOWN, 0.0

    best_class = max(scores, key=lambda k: scores[k])
    return best_class, scores[best_class]


def classify_severity_from_keywords(title: str, description: str = "") -> float:
    """
    Adjust severity score based on outage keywords in text.
    Returns an additive bonus (0–30) to be added to base severity.
    """
    text = f"{title} {description}".lower()

    outage_keywords = [
        "outage",
        "down",
        "production",
        "critical",
        "emergency",
        "全体",
        "全部",
        "every user",
        "all users",
        "entire",
        "no one can",
        "nobody can",
        "complete failure",
    ]

    bonus = 0.0
    for kw in outage_keywords:
        if kw in text:
            bonus += 15.0

    infra_keywords = [
        "server",
        "network",
        "vpn",
        "domain",
        "active directory",
        "erp",
        "epicor",
        "sap",
        "mes",
        "plc",
    ]
    for kw in infra_keywords:
        if kw in text:
            bonus += 10.0

    return min(bonus, 30.0)


def suggest_runbook(root_cause: RootCauseClass) -> str | None:
    """Return runbook ID for a given root cause class."""
    runbooks = {
        RootCauseClass.SHARED_MAILBOX_FORWARDING: "RUN-001-mailbox-forwarding",
        RootCauseClass.EMAIL_MESSAGING: "RUN-002-outlook-mbox",
        RootCauseClass.FILE_SHARE_PERMISSIONS: "RUN-003-ntfs-permissions",
        RootCauseClass.ACCESS_IDENTITY: "RUN-004-identity-unlock",
        RootCauseClass.PRINTER_SCANNER: "RUN-005-printer-driver",
        RootCauseClass.NETWORK_CONNECTIVITY: "RUN-006-vpn-reconnect",
        RootCauseClass.ERP_APPLICATION: "RUN-007-erp-restart",
        RootCauseClass.INFRASTRUCTURE_SERVICE: "RUN-008-server-health",
        RootCauseClass.SECURITY_SPAM_BLOCK: "RUN-009-spam-release",
    }
    return runbooks.get(root_cause)
