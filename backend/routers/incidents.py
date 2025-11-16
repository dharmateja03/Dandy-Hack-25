"""
Incident Auto-Detection and Management API endpoints
"""

from fastapi import APIRouter, Request, HTTPException
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/create")
async def create_incident(
    severity: str,
    reported_by: str,
    description: str,
    keywords: list = None,
    request: Request = None
):
    """
    Create incident from auto-detection

    Severity: critical, high, medium
    """
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        # Create incident in database
        incident_id = await db.create_incident({
            "severity": severity,
            "reported_by": reported_by,
            "description": description,
            "detected_keywords": keywords or [],
            "created_at": datetime.utcnow(),
            "status": "open"
        })

        logger.info(f"✅ Incident {incident_id} created with severity {severity}")

        # Send alert to on-call engineer / managers
        # TODO: Integrate with on-call schedule
        try:
            # Get managers/on-call users
            managers = await db.get_managers()
            for mgr in managers:
                # Send notification (could integrate with Slack/PagerDuty)
                logger.info(f"📢 Incident {incident_id} alerting {mgr.get('name')}")
        except Exception as e:
            logger.warning(f"⚠️ Could not notify managers: {e}")

        return {
            "status": "success",
            "id": incident_id,
            "severity": severity,
            "created_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error creating incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{incident_id}")
async def get_incident(incident_id: int, request: Request = None):
    """Get incident details"""
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        incident = await db.get_incident(incident_id)

        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")

        return {
            "status": "success",
            "incident": incident
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active/list")
async def get_active_incidents(request: Request = None):
    """Get all active incidents"""
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        incidents = await db.get_active_incidents()

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2}
        incidents.sort(key=lambda x: severity_order.get(x.get("severity", "medium"), 99))

        return {
            "status": "success",
            "incidents": incidents,
            "count": len(incidents),
            "critical_count": sum(1 for i in incidents if i.get("severity") == "critical")
        }

    except Exception as e:
        logger.error(f"Error fetching active incidents: {e}")
        return {
            "status": "success",
            "incidents": [],
            "count": 0,
            "critical_count": 0
        }


@router.post("/{incident_id}/resolve")
async def resolve_incident(incident_id: int, resolution_notes: str = "", request: Request = None):
    """Mark incident as resolved"""
    try:
        mcp = request.app.state.mcp
        db = mcp.database

        await db.resolve_incident(incident_id, resolution_notes)

        logger.info(f"✅ Incident {incident_id} resolved")

        return {
            "status": "success",
            "incident_id": incident_id,
            "resolved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error resolving incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))
