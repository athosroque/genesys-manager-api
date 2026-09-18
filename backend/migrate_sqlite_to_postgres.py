import sqlite3
import os
from database import SessionLocal, engine
from models import Ticket, Base
from datetime import datetime

# Set up the SQLAlchemy database (create tables if not exist)
Base.metadata.create_all(bind=engine)

# Ensure we have the SQLite database to read from
SQLITE_DB_PATH = "tickets_enriched.db"

if not os.path.exists(SQLITE_DB_PATH):
    print(f"SQLite DB {SQLITE_DB_PATH} not found. Skipping migration.")
    exit(0)

# Connect to SQLite
sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
sqlite_conn.row_factory = sqlite3.Row
cursor = sqlite_conn.cursor()

# Get all tickets from SQLite
cursor.execute("SELECT * FROM tickets")
sqlite_tickets = cursor.fetchall()

db = SessionLocal()
try:
    migrated_count = 0
    for row in sqlite_tickets:
        ticket_data = dict(row)
        # Check if already exists in postgres
        existing = db.query(Ticket).filter(Ticket.external_id == ticket_data["external_id"]).first()
        
        if not existing:
            # Parse dates if they exist, or let DB handle them (though we might want to keep the old ones)
            created_at = None
            if ticket_data.get("created_at"):
                try:
                    created_at = datetime.fromisoformat(ticket_data["created_at"])
                except ValueError:
                    pass
            
            updated_at = None
            if ticket_data.get("updated_at"):
                try:
                    updated_at = datetime.fromisoformat(ticket_data["updated_at"])
                except ValueError:
                    pass

            new_ticket = Ticket(
                external_id=ticket_data["external_id"],
                title=ticket_data.get("title"),
                description=ticket_data.get("description"),
                status=ticket_data.get("status"),
                category=ticket_data.get("category"),
                classification=ticket_data.get("classification"),
                suggested_response=ticket_data.get("suggested_response"),
                is_faq=bool(ticket_data.get("is_faq")),
            )
            
            # Manually set timestamps if available
            if created_at:
                new_ticket.created_at = created_at
            if updated_at:
                new_ticket.updated_at = updated_at
                
            db.add(new_ticket)
            migrated_count += 1
    
    db.commit()
    print(f"Successfully migrated {migrated_count} tickets from SQLite to PostgreSQL.")
except Exception as e:
    print(f"An error occurred during migration: {e}")
    db.rollback()
finally:
    db.close()
    sqlite_conn.close()
