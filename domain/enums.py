from enum import Enum


class TicketStatus(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    WAITING_FOR_INFO = "Waiting for Info"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


class EventType(str, Enum):
    TICKET_CREATED = "ticket_created"
    STATUS_CHANGED = "status_changed"
    ASSIGNMENT_CHANGED = "assignment_changed"
    COMMENT_ADDED = "comment_added"
    PRIORITY_CHANGED = "priority_changed"
    DESCRIPTION_UPDATED = "description_updated"
    DECISION_GENERATED = "decision_generated"
    RECOMMENDATION_ACCEPTED = "recommendation_accepted"
    RECOMMENDATION_REJECTED = "recommendation_rejected"
    RECOMMENDATION_OVERRIDDEN = "recommendation_overridden"
    INCIDENT_LINKED = "incident_linked"
    INCIDENT_CREATED = "incident_created"


class ActorType(str, Enum):
    SYSTEM = "system"
    OPERATOR = "operator"
    IMPORT = "import"
    AUTOMATION = "automation"


class LinkType(str, Enum):
    PRIMARY = "primary"
    RELATED = "related"
    DUPLICATE = "duplicate"
    INFERRED = "inferred"


class FeedbackType(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    OVERRIDDEN = "overridden"
    NOT_USEFUL = "not_useful"
    DUPLICATE_FIX = "duplicate_fix"
    WRONG_PRIORITY = "wrong_priority"


class RootCauseClass(str, Enum):
    ACCESS_IDENTITY = "access_identity"
    EMAIL_MESSAGING = "email_messaging"
    SHARED_MAILBOX_FORWARDING = "shared_mailbox_forwarding"
    PRINTER_SCANNER = "printer_scanner"
    FILE_SHARE_PERMISSIONS = "file_share_permissions"
    ERP_APPLICATION = "erp_application"
    WORKSTATION_ENDPOINT = "workstation_endpoint"
    NETWORK_CONNECTIVITY = "network_connectivity"
    INFRASTRUCTURE_SERVICE = "infrastructure_service"
    SECURITY_SPAM_BLOCK = "security_spam_block"
    PRODUCTION_SYSTEM_INTEGRATION = "production_system_integration"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendationStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"


class ActionType(str, Enum):
    APPLY_RUNBOOK = "apply_runbook"
    ASSIGN_TEAM = "assign_team"
    REQUEST_INFO = "request_info"
    ESCALATE = "escalate"
    LINK_INCIDENT = "link_incident"
    AUTO_RESOLVE = "auto_resolve"


class IncidentStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    RESOLVED = "resolved"
    CLOSED = "closed"
