import csv
import io
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.alert import Alert, AlertLevel, AlertType
from app.models.helmet import Helmet
from app.models.sensor_data import SensorData
from app.models.supervisor import Supervisor
from app.models.worker import Worker

router = APIRouter()

# ── Shared PDF helpers ────────────────────────────────────────────────────────

_RED    = colors.HexColor("#e63946")
_DARK   = colors.HexColor("#1a1a2e")
_LIGHT  = colors.HexColor("#f4f4f4")
_WHITE  = colors.white
_STYLES = getSampleStyleSheet()

_H1 = ParagraphStyle("h1", parent=_STYLES["Title"],   textColor=_DARK,  fontSize=18, spaceAfter=4)
_H2 = ParagraphStyle("h2", parent=_STYLES["Heading2"], textColor=_DARK, fontSize=12, spaceBefore=12, spaceAfter=4)
_SM = ParagraphStyle("sm", parent=_STYLES["Normal"],  fontSize=8,  textColor=colors.grey)
_BODY = ParagraphStyle("body", parent=_STYLES["Normal"], fontSize=9)


def _header_elements(title: str, subtitle: str = "") -> list:
    els = [
        Paragraph("Smart Helmet Safety System", _SM),
        Paragraph(title, _H1),
        HRFlowable(width="100%", color=_RED, thickness=1.5),
        Spacer(1, 0.2 * cm),
    ]
    if subtitle:
        els.append(Paragraph(subtitle, _SM))
        els.append(Spacer(1, 0.3 * cm))
    els.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", _SM))
    els.append(Spacer(1, 0.5 * cm))
    return els


def _table_style(header_bg=None) -> TableStyle:
    bg = header_bg or _RED
    return TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  bg),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  _WHITE),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0),  8),
        ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 1), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_WHITE, _LIGHT]),
        ("GRID",         (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
    ])


def _level_color(level) -> str:
    v = str(level).lower()
    if "critical" in v: return "#e63946"
    if "warning"  in v: return "#f4a261"
    return "#2a9d8f"


def _build_pdf(elements: list) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    doc.build(elements)
    return buf.getvalue()


# ── Pydantic models ───────────────────────────────────────────────────────────

class ReportRequest(BaseModel):
    title: str
    start: datetime
    end: datetime
    include_alerts: bool = True
    include_sensor_summary: bool = False
    helmet_ids: Optional[List[uuid.UUID]] = None


# ── Legacy endpoints (kept for backward compat) ───────────────────────────────

@router.get("/alerts")
async def alert_report(
    start: datetime = Query(...),
    end: datetime = Query(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(
        select(Alert).where(Alert.created_at >= start, Alert.created_at <= end)
    )
    alerts = result.scalars().all()
    return {"total": len(alerts), "alerts": alerts}


@router.get("/sensor-data/{helmet_id}")
async def sensor_data_report(
    helmet_id: uuid.UUID,
    start: datetime = Query(...),
    end: datetime = Query(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(
        select(SensorData).where(
            SensorData.helmet_id == helmet_id,
            SensorData.recorded_at >= start,
            SensorData.recorded_at <= end,
        )
    )
    data = result.scalars().all()
    return {"helmet_id": str(helmet_id), "total": len(data), "data": data}


@router.post("/generate")
async def generate_report(
    data: ReportRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    report = {
        "title": data.title,
        "generated_at": datetime.utcnow().isoformat(),
        "period": {"start": data.start.isoformat(), "end": data.end.isoformat()},
    }
    if data.include_alerts:
        alerts = (await db.execute(
            select(Alert).where(Alert.created_at >= data.start, Alert.created_at <= data.end)
        )).scalars().all()
        report["alerts"] = {
            "total": len(alerts),
            "critical": sum(1 for a in alerts if a.level == AlertLevel.critical),
            "resolved": sum(1 for a in alerts if a.is_resolved),
        }
    if data.include_sensor_summary:
        q = select(SensorData).where(
            SensorData.recorded_at >= data.start, SensorData.recorded_at <= data.end
        )
        if data.helmet_ids:
            q = q.where(SensorData.helmet_id.in_(data.helmet_ids))
        readings = (await db.execute(q)).scalars().all()
        report["sensor_data"] = {"total_readings": len(readings)}
    return report


@router.get("/audit-logs")
async def audit_logs(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(
        select(Alert).order_by(Alert.created_at.desc()).offset(skip).limit(limit)
    )
    alerts = result.scalars().all()
    return {
        "total": len(alerts),
        "logs": [
            {
                "id": str(a.id),
                "event": f"Alert triggered: {a.type} [{a.level}]",
                "detail": a.message,
                "status": "resolved" if a.is_resolved else "active",
                "timestamp": a.created_at.isoformat(),
            }
            for a in alerts
        ],
    }


# ── Download: Alerts ──────────────────────────────────────────────────────────

@router.get("/download/alerts")
async def download_alerts(
    format: str = Query("csv", enum=["csv", "pdf"]),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    level: Optional[str] = Query(None, enum=["critical", "warning", "info"]),
    resolved: Optional[bool] = Query(None),
    limit: int = Query(2000, le=5000),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    q = select(Alert).order_by(Alert.created_at.desc())
    if start:
        q = q.where(Alert.created_at >= start)
    if end:
        q = q.where(Alert.created_at <= end)
    if level:
        q = q.where(Alert.level == level)
    if resolved is not None:
        q = q.where(Alert.is_resolved == resolved)
    q = q.limit(limit)
    alerts = (await db.execute(q)).scalars().all()

    date_str = datetime.utcnow().strftime("%Y%m%d")

    if format == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["id", "type", "level", "message", "is_resolved",
                    "resolved_at", "helmet_id", "worker_id", "created_at"])
        for a in alerts:
            w.writerow([
                str(a.id), a.type.value if hasattr(a.type, "value") else a.type,
                a.level.value if hasattr(a.level, "value") else a.level,
                a.message, a.is_resolved,
                a.resolved_at.isoformat() if a.resolved_at else "",
                str(a.helmet_id) if a.helmet_id else "",
                str(a.worker_id) if a.worker_id else "",
                a.created_at.isoformat(),
            ])
        return StreamingResponse(
            io.BytesIO(buf.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=alerts_{date_str}.csv"},
        )

    # PDF
    elements = _header_elements(
        "Alerts Report",
        f"Period: {start.strftime('%Y-%m-%d') if start else 'All'} → "
        f"{end.strftime('%Y-%m-%d') if end else 'Now'}  |  Total: {len(alerts)}",
    )

    critical = sum(1 for a in alerts if str(a.level).lower() == "critical")
    warning  = sum(1 for a in alerts if str(a.level).lower() == "warning")
    resolved_count = sum(1 for a in alerts if a.is_resolved)

    summary = [
        ["Total Alerts", "Critical", "Warning", "Resolved", "Unresolved"],
        [len(alerts), critical, warning, resolved_count, len(alerts) - resolved_count],
    ]
    elements.append(Table(summary, style=_table_style(_DARK)))
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph("Alert Details", _H2))

    rows = [["#", "Type", "Level", "Message", "Resolved", "Created"]]
    for i, a in enumerate(alerts, 1):
        rows.append([
            i,
            str(a.type.value if hasattr(a.type, "value") else a.type),
            str(a.level.value if hasattr(a.level, "value") else a.level).upper(),
            Paragraph(a.message[:80], _BODY),
            "Yes" if a.is_resolved else "No",
            a.created_at.strftime("%Y-%m-%d %H:%M"),
        ])

    col_widths = [1*cm, 2.5*cm, 2*cm, 8.5*cm, 1.8*cm, 3.5*cm]
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(_table_style())
    elements.append(t)

    return StreamingResponse(
        io.BytesIO(_build_pdf(elements)),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=alerts_{date_str}.pdf"},
    )


# ── Download: Workers ─────────────────────────────────────────────────────────

@router.get("/download/workers")
async def download_workers(
    format: str = Query("csv", enum=["csv", "pdf"]),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    q = select(Worker).options(selectinload(Worker.user), selectinload(Worker.dept))
    if is_active is not None:
        q = q.where(Worker.is_active == is_active)
    q = q.order_by(Worker.full_name)
    workers = (await db.execute(q)).scalars().all()

    date_str = datetime.utcnow().strftime("%Y%m%d")

    if format == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["employee_id", "full_name", "email", "phone",
                    "zone", "department", "status", "supervisor_id", "created_at"])
        for wk in workers:
            w.writerow([
                wk.employee_id, wk.full_name,
                wk.user.email if wk.user else "",
                wk.phone or "",
                wk.zone or "",
                wk.dept.name if wk.dept else (wk.zone or ""),
                "Active" if wk.is_active else "Inactive",
                str(wk.supervisor_id) if wk.supervisor_id else "",
                wk.created_at.strftime("%Y-%m-%d"),
            ])
        return StreamingResponse(
            io.BytesIO(buf.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=workers_{date_str}.csv"},
        )

    # PDF
    active_count   = sum(1 for w in workers if w.is_active)
    inactive_count = len(workers) - active_count

    elements = _header_elements(
        "Workers Report",
        f"Total: {len(workers)}  |  Active: {active_count}  |  Inactive: {inactive_count}",
    )

    summary = [["Total Workers", "Active", "Inactive"],
               [len(workers), active_count, inactive_count]]
    elements.append(Table(summary, style=_table_style(_DARK)))
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph("Worker List", _H2))

    rows = [["#", "Employee ID", "Full Name", "Email", "Zone / Dept", "Status", "Joined"]]
    for i, wk in enumerate(workers, 1):
        rows.append([
            i,
            wk.employee_id,
            wk.full_name,
            wk.user.email if wk.user else "—",
            wk.dept.name if wk.dept else (wk.zone or "—"),
            "Active" if wk.is_active else "Inactive",
            wk.created_at.strftime("%Y-%m-%d"),
        ])

    col_widths = [0.8*cm, 2.5*cm, 4*cm, 4.5*cm, 3.5*cm, 2*cm, 2.5*cm]
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(_table_style())
    elements.append(t)

    return StreamingResponse(
        io.BytesIO(_build_pdf(elements)),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=workers_{date_str}.pdf"},
    )


# ── Download: Sensor data for a helmet ───────────────────────────────────────

@router.get("/download/sensor-data/{helmet_id}")
async def download_sensor_data(
    helmet_id: uuid.UUID,
    format: str = Query("csv", enum=["csv", "pdf"]),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    limit: int = Query(2000, le=5000),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    helmet = (await db.execute(
        select(Helmet).where(Helmet.id == helmet_id)
    )).scalar_one_or_none()
    if not helmet:
        raise HTTPException(status_code=404, detail="Helmet not found")

    q = select(SensorData).where(SensorData.helmet_id == helmet_id).order_by(
        SensorData.recorded_at.desc()
    )
    if start:
        q = q.where(SensorData.recorded_at >= start)
    if end:
        q = q.where(SensorData.recorded_at <= end)
    q = q.limit(limit)
    rows_data = (await db.execute(q)).scalars().all()

    date_str = datetime.utcnow().strftime("%Y%m%d")
    filename_base = f"sensor_{helmet.helmet_code}_{date_str}"

    if format == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow([
            "recorded_at", "temperature", "humidity", "gas_level", "co_ppm",
            "ch4_percent", "vibration_detected", "helmet_worn",
            "accel_x", "accel_y", "accel_z", "gyro_x", "gyro_y", "gyro_z",
            "battery_level", "signal_strength", "step_count", "heading_deg",
            "est_zone", "ai_prediction", "ai_confidence",
        ])
        for d in rows_data:
            w.writerow([
                d.recorded_at.isoformat(), d.temperature, d.humidity,
                d.gas_level, d.co_ppm, d.ch4_percent,
                d.vibration_detected, d.helmet_worn,
                d.accelerometer_x, d.accelerometer_y, d.accelerometer_z,
                d.gyro_x, d.gyro_y, d.gyro_z,
                d.battery_level, d.signal_strength,
                d.step_count, d.heading_deg, d.est_zone,
                d.ai_prediction, d.ai_confidence,
            ])
        return StreamingResponse(
            io.BytesIO(buf.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.csv"},
        )

    # PDF
    elements = _header_elements(
        f"Sensor Data — {helmet.helmet_code}",
        f"Readings: {len(rows_data)}  |  "
        f"Period: {start.strftime('%Y-%m-%d') if start else 'All'} → "
        f"{end.strftime('%Y-%m-%d') if end else 'Now'}",
    )

    if rows_data:
        temps = [d.temperature for d in rows_data if d.temperature is not None]
        co_vals = [d.co_ppm for d in rows_data if d.co_ppm is not None]
        worn_count = sum(1 for d in rows_data if d.helmet_worn)
        vib_count  = sum(1 for d in rows_data if d.vibration_detected)

        summary = [[
            "Readings", "Avg Temp (°C)", "Max CO (ppm)",
            "Helmet Worn %", "Vibration Events",
        ], [
            len(rows_data),
            f"{sum(temps)/len(temps):.1f}" if temps else "—",
            f"{max(co_vals):.1f}" if co_vals else "—",
            f"{worn_count/len(rows_data)*100:.1f}%" if rows_data else "—",
            vib_count,
        ]]
        elements.append(Table(summary, style=_table_style(_DARK)))
        elements.append(Spacer(1, 0.5 * cm))

    elements.append(Paragraph("Readings", _H2))
    rows = [["Time", "Temp", "Hum", "CO ppm", "Gas", "Worn", "Vib", "Battery", "AI"]]
    for d in rows_data:
        rows.append([
            d.recorded_at.strftime("%m-%d %H:%M"),
            f"{d.temperature:.1f}" if d.temperature is not None else "—",
            f"{d.humidity:.0f}%" if d.humidity is not None else "—",
            f"{d.co_ppm:.1f}" if d.co_ppm is not None else "—",
            str(d.gas_level or "—"),
            "Yes" if d.helmet_worn else "No",
            "Yes" if d.vibration_detected else "No",
            f"{d.battery_level:.0f}%" if d.battery_level else "—",
            d.ai_prediction or "—",
        ])

    col_widths = [2.5*cm, 1.8*cm, 1.8*cm, 2*cm, 1.8*cm, 1.5*cm, 1.5*cm, 2*cm, 4.4*cm]
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(_table_style())
    elements.append(t)

    return StreamingResponse(
        io.BytesIO(_build_pdf(elements)),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename_base}.pdf"},
    )


# ── Download: Full safety summary PDF ────────────────────────────────────────

@router.get("/download/safety-summary")
async def download_safety_summary(
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    """Comprehensive PDF safety report: summary stats + alerts + workers + helmets."""
    now = datetime.utcnow()

    # Fetch all data
    alert_q = select(Alert).order_by(Alert.created_at.desc())
    if start:
        alert_q = alert_q.where(Alert.created_at >= start)
    if end:
        alert_q = alert_q.where(Alert.created_at <= end)
    alerts = (await db.execute(alert_q)).scalars().all()

    workers   = (await db.execute(
        select(Worker).options(selectinload(Worker.user), selectinload(Worker.dept))
    )).scalars().all()
    helmets   = (await db.execute(select(Helmet))).scalars().all()
    supervisors = (await db.execute(select(Supervisor))).scalars().all()

    total_readings = (await db.execute(
        select(func.count()).select_from(SensorData)
    )).scalar()
    worn_readings = (await db.execute(
        select(func.count()).select_from(SensorData).where(SensorData.helmet_worn == True)
    )).scalar()

    period_str = (
        f"{start.strftime('%Y-%m-%d') if start else 'Beginning'} → "
        f"{end.strftime('%Y-%m-%d') if end else now.strftime('%Y-%m-%d')}"
    )

    elements = _header_elements("Safety Summary Report", f"Period: {period_str}")

    # ── Summary stats table
    elements.append(Paragraph("Overview", _H2))
    active_workers = sum(1 for w in workers if w.is_active)
    critical_alerts = sum(1 for a in alerts if str(a.level).lower() == "critical")
    unresolved = sum(1 for a in alerts if not a.is_resolved)
    compliance = round(worn_readings / total_readings * 100, 1) if total_readings else 0.0

    overview = [
        ["Metric", "Value"],
        ["Total Workers",         len(workers)],
        ["Active Workers",        active_workers],
        ["Total Supervisors",     len(supervisors)],
        ["Total Helmets",         len(helmets)],
        ["Total Alerts (period)", len(alerts)],
        ["Critical Alerts",       critical_alerts],
        ["Unresolved Alerts",     unresolved],
        ["Helmet Compliance",     f"{compliance}%"],
        ["Total Sensor Readings", total_readings],
    ]
    ov_table = Table(overview, colWidths=[8*cm, 6*cm])
    ov_table.setStyle(_table_style(_DARK))
    elements.append(ov_table)
    elements.append(Spacer(1, 0.5 * cm))

    # ── Alerts breakdown
    elements.append(Paragraph("Alerts Breakdown", _H2))
    by_type: dict = {}
    for a in alerts:
        k = str(a.type.value if hasattr(a.type, "value") else a.type)
        by_type[k] = by_type.get(k, 0) + 1
    alert_rows = [["Alert Type", "Count"]] + [[t, c] for t, c in sorted(by_type.items(), key=lambda x: -x[1])]
    if len(alert_rows) > 1:
        elements.append(Table(alert_rows, colWidths=[8*cm, 6*cm], style=_table_style()))
    else:
        elements.append(Paragraph("No alerts in this period.", _BODY))
    elements.append(Spacer(1, 0.5 * cm))

    # ── Workers table
    elements.append(Paragraph("Worker List", _H2))
    worker_rows = [["Employee ID", "Name", "Zone / Dept", "Status"]]
    for wk in workers:
        worker_rows.append([
            wk.employee_id, wk.full_name,
            wk.dept.name if wk.dept else (wk.zone or "—"),
            "Active" if wk.is_active else "Inactive",
        ])
    wt = Table(worker_rows, colWidths=[3*cm, 5.5*cm, 5.5*cm, 2.5*cm], repeatRows=1)
    wt.setStyle(_table_style())
    elements.append(wt)
    elements.append(Spacer(1, 0.5 * cm))

    # ── Helmets table
    elements.append(Paragraph("Helmet Status", _H2))
    helmet_rows = [["Helmet Code", "Status", "Zone", "Active", "Last Seen"]]
    for h in helmets:
        helmet_rows.append([
            h.helmet_code,
            str(h.status.value if hasattr(h.status, "value") else h.status),
            h.zone or "—",
            "Yes" if h.is_active else "No",
            h.last_seen.strftime("%Y-%m-%d %H:%M") if h.last_seen else "Never",
        ])
    ht = Table(helmet_rows, colWidths=[3.5*cm, 2.5*cm, 4*cm, 2*cm, 4.5*cm], repeatRows=1)
    ht.setStyle(_table_style())
    elements.append(ht)

    date_str = now.strftime("%Y%m%d")
    return StreamingResponse(
        io.BytesIO(_build_pdf(elements)),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=safety_summary_{date_str}.pdf"},
    )


# ── Legacy export (kept for backward compat) ──────────────────────────────────

@router.get("/export")
async def export_report(
    resource: str = Query("alerts", enum=["alerts", "sensor_data"]),
    format: str = Query("json", enum=["json", "csv"]),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    if resource == "alerts":
        items = (await db.execute(
            select(Alert).order_by(Alert.created_at.desc()).limit(1000)
        )).scalars().all()
        if format == "csv":
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["id", "type", "level", "message", "is_resolved", "helmet_id", "worker_id", "created_at"])
            for a in items:
                w.writerow([str(a.id), a.type, a.level, a.message, a.is_resolved,
                             str(a.helmet_id), str(a.worker_id), a.created_at])
            return StreamingResponse(
                io.BytesIO(buf.getvalue().encode()),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=alerts.csv"},
            )
        return {"resource": resource, "total": len(items), "data": items}

    items = (await db.execute(
        select(SensorData).order_by(SensorData.recorded_at.desc()).limit(1000)
    )).scalars().all()
    if format == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["id", "helmet_id", "temperature", "humidity", "gas_level",
                    "co_ppm", "vibration_detected", "helmet_worn", "recorded_at"])
        for d in items:
            w.writerow([str(d.id), str(d.helmet_id), d.temperature, d.humidity,
                        d.gas_level, d.co_ppm, d.vibration_detected, d.helmet_worn, d.recorded_at])
        return StreamingResponse(
            io.BytesIO(buf.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=sensor_data.csv"},
        )
    return {"resource": resource, "total": len(items), "data": items}
