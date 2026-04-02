# Reporting Architecture

## 5-Tab Excel Workbook

| Tab | Contents |
|---|---|
| Executive Summary | KPIs, charts, top risks |
| Operational Queue | Full ticket table, styled, filterable |
| Incident Clusters | Cluster summary with linked tickets |
| Decision Intelligence | Score breakdowns, root cause, recommendations |
| Audit Extract | Event timeline, feedback status, execution outcomes |

## Report Generation Flow

```mermaid
flowchart TD
    A[Request /api/reports/excel] --> B[pipelines/reports/excel_report.py]
    B --> C[Fetch tickets + decisions + incidents]
    C --> D[Build Executive Summary tab]
    C --> E[Build Operational Queue tab]
    C --> F[Build Incident Clusters tab]
    C --> G[Build Decision Intelligence tab]
    C --> H[Build Audit Extract tab]
    D --> I[Apply visual formatting]
    E --> I
    F --> I
    G --> I
    H --> I
    I --> J[Return .xlsx download]
```

## Formatting Standards

- **Header row**: dark fill (#1a1a1a), white bold Calibri 11pt
- **Frozen row**: row 1 always frozen
- **Auto filters**: on all data tables
- **Alternating rows**: subtle gray banding
- **Risk colors**:
  - Critical/High risk → red (#fecaca)
  - At risk → amber (#fef3c7)
  - Healthy/resolved → green (#dcfce7)
- **Charts**: embedded in Executive Summary (status pie, priority bar, SLA risk histogram)
