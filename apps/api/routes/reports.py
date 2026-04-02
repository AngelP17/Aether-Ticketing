from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO
from datetime import datetime

from apps.api.deps import get_db
from apps.api.services.report_service import ReportService

router = APIRouter()


@router.get("/excel")
def get_excel_report(
    report_type: str = Query("operational"),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    incident_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    try:
        service = ReportService(db)
        wb = service.generate_workbook(report_type, date_from, date_to, incident_id)
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        today = datetime.now()
        filename = f"aether_report_{today.month}_{today.day}_{today.year}.xlsx"

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")
