"""Live sessions and auth log — for admin dashboard."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.schemas import LiveSessionResponse, AuthLogResponse

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("/live", response_model=list[LiveSessionResponse])
async def live_sessions(
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    result = db.execute(
        text("""
            SELECT RadAcctId, UserName, NASIPAddress, AcctStartTime,
                   AcctSessionTime, AcctInputOctets, AcctOutputOctets,
                   FramedIPAddress
            FROM radacct
            WHERE AcctStopTime IS NULL
            ORDER BY AcctStartTime DESC
            LIMIT 100
        """)
    )
    results = []
    for row in result:
        results.append({
            "radacct_id": row[0],
            "username": row[1],
            "nas_ip": str(row[2]) if row[2] else "",
            "start_time": row[3],
            "session_time": row[4] or 0,
            "input_bytes": row[5] or 0,
            "output_bytes": row[6] or 0,
            "framed_ip": row[7] if row[7] else None,
        })
    return results


@router.get("/auth-log", response_model=list[AuthLogResponse])
async def auth_log(
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
    limit: int = 100,
):
    result = db.execute(
        text("""
            SELECT id, username, reply, authdate
            FROM radpostauth
            ORDER BY authdate DESC
            LIMIT :lim
        """),
        {"lim": limit},
    )
    return [dict(row._mapping) for row in result]
