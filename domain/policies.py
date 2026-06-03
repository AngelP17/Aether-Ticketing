from dataclasses import dataclass


@dataclass(frozen=True)
class ScoringWeights:
    SEVERITY: float = 0.20
    URGENCY: float = 0.16
    BUSINESS_IMPACT: float = 0.18
    SLA_RISK: float = 0.12
    RECURRENCE: float = 0.10
    DEPENDENCY_CRITICALITY: float = 0.08
    GRAPH_CENTRALITY: float = 0.10
    ACTIONABILITY: float = 0.06
    UNCERTAINTY_PENALTY: float = 0.10
    version_tag: str = "rules-2026-graph-v2"


SCORING_WEIGHTS = ScoringWeights()


@dataclass(frozen=True)
class ClusteringThresholds:
    TEXT_SIMILARITY: float = 0.78
    TIME_WINDOW_HOURS: int = 24
    MIN_CONFIDENCE_TO_LINK: float = 0.60
    MIN_CONFIDENCE_TO_CREATE: float = 0.75


CLUSTERING_THRESHOLDS = ClusteringThresholds()


@dataclass(frozen=True)
class GraphFeatureWeights:
    """Per-edge-type weights for the ticket relationship graph.

    Weights are intentionally small (sub-1.0) so that an unweighted
    edge from `similar_cases_count` cannot be drowned out, and so that
    a ticket with many edges still produces a bounded feature.
    """

    REQUESTER: float = 0.6
    ASSIGNEE: float = 0.5
    SITE: float = 0.8
    ASSET: float = 1.0
    CATEGORY: float = 0.7
    ROOT_CAUSE: float = 0.9
    TIME_WINDOW: float = 0.3


GRAPH_FEATURE_WEIGHTS = GraphFeatureWeights()
GRAPH_TIME_WINDOW_HOURS = 6


@dataclass(frozen=True)
class UncertaintyBandThresholds:
    """Cutoffs that map (priority, confidence, edge_density) to a band."""

    HIGH_CONFIDENCE_MIN_PRIORITY: float = 70.0
    HIGH_CONFIDENCE_MIN_CONFIDENCE: float = 80.0
    REVIEW_NEEDED_MAX_CONFIDENCE: float = 60.0
    REVIEW_NEEDED_MAX_PRIORITY: float = 55.0
    UNCERTAINTY_PENALTY_REVIEW: float = 25.0


UNCERTAINTY_BAND_THRESHOLDS = UncertaintyBandThresholds()


BAND_HIGH_CONFIDENCE_ACTION = "high_confidence_action"
BAND_REVIEW_NEEDED = "review_needed"
BAND_STANDARD_QUEUE = "standard_queue"


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
