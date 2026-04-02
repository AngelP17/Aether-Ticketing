from dataclasses import dataclass


@dataclass(frozen=True)
class ScoringWeights:
    SEVERITY: float = 0.22
    URGENCY: float = 0.18
    BUSINESS_IMPACT: float = 0.20
    SLA_RISK: float = 0.14
    RECURRENCE: float = 0.10
    DEPENDENCY_CRITICALITY: float = 0.08
    ACTIONABILITY: float = 0.08
    UNCERTAINTY_PENALTY: float = 0.10


SCORING_WEIGHTS = ScoringWeights()


@dataclass(frozen=True)
class ClusteringThresholds:
    TEXT_SIMILARITY: float = 0.78
    TIME_WINDOW_HOURS: int = 24
    MIN_CONFIDENCE_TO_LINK: float = 0.60
    MIN_CONFIDENCE_TO_CREATE: float = 0.75


CLUSTERING_THRESHOLDS = ClusteringThresholds()


SEVERITY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "network_connectivity": (
        "network",
        "vpn",
        "connectivity",
        "internet",
        "wifi",
        "dns",
        "dhcp",
        "cannot connect",
        "connection failed",
        "network error",
        "no internet",
    ),
    "email_messaging": (
        "outlook",
        "email",
        "inbox",
        "microsoft 365",
        "exchange",
        "mailbox",
        "cannot send",
        "email not working",
        "outlook crash",
    ),
    "shared_mailbox_forwarding": (
        "shared mailbox",
        "mailbox forwarding",
        "delegate",
        "shared calendar",
        "cannot access shared",
        "forwarding rules",
    ),
    "access_identity": (
        "unlock",
        "locked out",
        "access",
        "permissions",
        "ntfs",
        "credential",
        "cant access",
        "permission denied",
        "access denied",
    ),
    "file_share_permissions": (
        "file share",
        "shared drive",
        "network drive",
        "share permissions",
        "cannot open",
        "missing permissions",
        "network location",
    ),
    "printer_scanner": (
        "printer",
        "print",
        "scanner",
        "copier",
        "printing error",
        "print queue",
        "cannot print",
        "printer offline",
    ),
    "erp_application": (
        "epicor",
        "sap",
        "oracle",
        "erp",
        "mrp",
        "enterprise system",
        "erp error",
        "system down",
        "application crash",
    ),
    "workstation_endpoint": (
        "laptop",
        "desktop",
        "workstation",
        "pc",
        "computer",
        "blue screen",
        "won't boot",
        "slow computer",
        "endpoint",
    ),
    "infrastructure_service": (
        "server",
        "datacenter",
        "domain",
        "active directory",
        "dns",
        "server down",
        "domain join",
        "ad error",
    ),
    "security_spam_block": (
        "spam",
        "phishing",
        "blocked",
        "security alert",
        "suspicious",
        "email blocked",
        "link blocked",
        "attachment blocked",
    ),
    "production_system_integration": (
        "plc",
        "scada",
        "mes",
        "integration",
        "api",
        "production system",
        "manufacturing",
        "ot system",
        "industrial",
    ),
}


ROOT_CAUSE_CLASSES = {
    "shared_mailbox_forwarding": [
        "shared mailbox",
        "mailbox forwarding",
        "delegate access",
        "forward to personal",
    ],
    "email_messaging": ["outlook", "email", "inbox", "microsoft 365"],
    "network_connectivity": ["vpn", "network", "connectivity", "wifi", "internet"],
    "access_identity": ["unlock", "locked", "access", "ntfs", "credential"],
    "file_share_permissions": ["file share", "shared drive", "network drive", "permissions"],
    "printer_scanner": ["printer", "print", "scanner", "copier"],
    "erp_application": ["epicor", "sap", "oracle", "erp"],
    "workstation_endpoint": ["laptop", "desktop", "workstation", "pc"],
    "infrastructure_service": ["server", "datacenter", "domain", "ad"],
    "security_spam_block": ["spam", "phishing", "blocked email"],
    "production_system_integration": ["plc", "scada", "mes", "integration api"],
    "unknown": [],
}


SLATargetHours: dict[str, float] = {
    "Critical": 4.0,
    "High": 8.0,
    "Medium": 24.0,
    "Low": 72.0,
}

PriorityRawToSeverity: dict[str, int] = {
    "Critical": 90,
    "High": 65,
    "Medium": 45,
    "Low": 20,
}
