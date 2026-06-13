"""Company settings — read by frontend, write by admin."""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.schemas import CompanyInfo, SettingsResponse

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings(db: Session = Depends(get_db)):
    """Public endpoint — returns company info for the frontend."""
    result = db.execute(text("SELECT key, value FROM settings"))
    rows = {row.key: json.loads(row.value) for row in result}

    company = CompanyInfo(**rows.get("company", {}))
    defaults = rows.get("defaults", {"max_devices": 1, "session_timeout": 86400})

    return SettingsResponse(company=company, defaults=defaults)


@router.put("", response_model=SettingsResponse)
async def update_settings(
    company: CompanyInfo,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    """Admin updates company settings."""
    value_json = json.dumps(company.model_dump())
    db.execute(
        text("""
            INSERT INTO settings (key, value, updated_at)
            VALUES ('company', :val, now())
            ON CONFLICT (key) DO UPDATE SET value = :val2, updated_at = now()
        """),
        {"val": value_json, "val2": value_json},
    )
    db.commit()
    return await get_settings(db)
