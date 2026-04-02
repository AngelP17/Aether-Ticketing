from pipelines.reports.excel_report import generate_workbook


def test_excel_report_contains_expected_tabs() -> None:
    workbook = generate_workbook(
        tickets=[
            {
                "ticket_id": "IT-1",
                "title": "Email issue",
                "status": "Open",
                "priority_raw": "High",
                "category": "Email Issues",
                "assignee": "tech1",
                "site": "HQ",
                "days_open": 2,
                "priority_score": 82,
                "root_cause_hypothesis": "email_messaging",
                "sla_risk": 65,
                "confidence_score": 74,
                "recommendation": "Route to messaging",
            }
        ],
        incidents=[],
    )
    assert workbook.sheetnames == [
        "Executive Summary",
        "Operational Queue",
        "Incident Clusters",
        "Decision Intelligence",
        "Audit Extract",
    ]
