from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from database import SessionLocal, engine, Base
from models import Ticket

def get_connection():
    # Deprecated for raw queries, but kept for compatibility if someone expects a connection-like object
    # It's better to use SessionLocal() directly
    pass

def init_db():
    Base.metadata.create_all(bind=engine)

def upsert_ticket(ticket_data: Dict[str, Any]) -> None:
    db = SessionLocal()
    try:
        existing = db.query(Ticket).filter(Ticket.external_id == ticket_data["external_id"]).first()
        
        if existing:
            existing.title = ticket_data.get("title", existing.title)
            existing.description = ticket_data.get("description", existing.description)
            existing.status = ticket_data.get("status", existing.status)
            existing.category = ticket_data.get("category", existing.category)
            existing.classification = ticket_data.get("classification", existing.classification)
            existing.suggested_response = ticket_data.get("suggested_response", existing.suggested_response)
            if "is_faq" in ticket_data:
                existing.is_faq = ticket_data["is_faq"]
        else:
            new_ticket = Ticket(
                external_id=ticket_data["external_id"],
                title=ticket_data.get("title"),
                description=ticket_data.get("description"),
                status=ticket_data.get("status"),
                category=ticket_data.get("category"),
                classification=ticket_data.get("classification"),
                suggested_response=ticket_data.get("suggested_response"),
                is_faq=ticket_data.get("is_faq", False),
            )
            db.add(new_ticket)
        
        db.commit()
    finally:
        db.close()

def get_tickets(limit: int = 50, offset: int = 0, status: Optional[str] = None) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        query = db.query(Ticket)
        if status:
            query = query.filter(Ticket.status == status)
            
        tickets = query.order_by(desc(Ticket.created_at)).offset(offset).limit(limit).all()
        return [
            {
                "id": t.id,
                "external_id": t.external_id,
                "title": t.title,
                "description": t.description,
                "status": t.status,
                "category": t.category,
                "classification": t.classification,
                "suggested_response": t.suggested_response,
                "is_faq": t.is_faq,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            }
            for t in tickets
        ]
    finally:
        db.close()

def get_ticket(external_id: str) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        t = db.query(Ticket).filter(Ticket.external_id == external_id).first()
        if t:
            return {
                "id": t.id,
                "external_id": t.external_id,
                "title": t.title,
                "description": t.description,
                "status": t.status,
                "category": t.category,
                "classification": t.classification,
                "suggested_response": t.suggested_response,
                "is_faq": t.is_faq,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            }
        return None
    finally:
        db.close()

def update_ticket_classification(external_id: str, classification: str, is_faq: bool) -> None:
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.external_id == external_id).first()
        if ticket:
            ticket.classification = classification
            ticket.is_faq = is_faq
            db.commit()
    finally:
        db.close()

def get_faq_metrics() -> Dict[str, Any]:
    db = SessionLocal()
    try:
        # Categories count
        top_categories_raw = db.query(
            Ticket.classification, 
            func.count(Ticket.id).label('count')
        ).filter(
            Ticket.is_faq == True,
            Ticket.classification != None
        ).group_by(
            Ticket.classification
        ).order_by(
            desc('count')
        ).limit(5).all()
        
        top_categories = [{"classification": row[0], "count": row[1]} for row in top_categories_raw]
        
        # Recent FAQs
        recent_faqs_raw = db.query(
            Ticket.external_id,
            Ticket.title,
            Ticket.suggested_response,
            Ticket.classification
        ).filter(
            Ticket.is_faq == True
        ).order_by(
            desc(Ticket.updated_at)
        ).limit(10).all()
        
        recent_faqs = [
            {
                "external_id": r.external_id,
                "title": r.title,
                "suggested_response": r.suggested_response,
                "classification": r.classification
            }
            for r in recent_faqs_raw
        ]
        
        return {
            "top_categories": top_categories,
            "recent_faqs": recent_faqs
        }
    finally:
        db.close()

# Initialize on module load
init_db()
