from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from services.db_tickets import (
    get_tickets, 
    get_ticket, 
    update_ticket_classification, 
    get_faq_metrics
)
from services.ticket_automation import sync_tickets

router = APIRouter(prefix="/tickets", tags=["tickets"])

class TicketUpdate(BaseModel):
    classification: str
    is_faq: bool

@router.post("/sync")
async def trigger_sync():
    """Triggers the synchronization process with the external database."""
    result = sync_tickets()
    return result

@router.get("/")
async def list_tickets(limit: int = 50, offset: int = 0, status: Optional[str] = None):
    """List all enriched tickets."""
    tickets = get_tickets(limit=limit, offset=offset, status=status)
    return {"tickets": tickets}

@router.get("/knowledge-base")
async def get_knowledge_base():
    """Returns FAQ metrics and top categories for the Knowledge Base UI."""
    metrics = get_faq_metrics()
    return metrics

@router.get("/{external_id}")
async def get_ticket_details(external_id: str):
    """Get details of a specific ticket."""
    ticket = get_ticket(external_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@router.put("/{external_id}")
async def update_ticket(external_id: str, update_data: TicketUpdate):
    """Allows humans to review and update the ticket's classification and FAQ status."""
    ticket = get_ticket(external_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    update_ticket_classification(
        external_id=external_id,
        classification=update_data.classification,
        is_faq=update_data.is_faq
    )
    return {"status": "success", "message": "Ticket updated"}
