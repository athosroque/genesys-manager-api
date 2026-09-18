import logging
from typing import List, Dict, Any
from .db_tickets import upsert_ticket

logger = logging.getLogger(__name__)

# --- Mock External DB Data ---
# In a real scenario, this would connect to the external SQLite database
# e.g., sqlite3.connect("external_source.db")
MOCK_EXTERNAL_TICKETS = [
    {
        "external_id": "TKT-1001",
        "title": "Sistema sem áudio no ramal",
        "description": "Estou tentando atender uma ligação no WebRTC e o cliente não me escuta, nem eu escuto ele. O ramal parece estar mudo.",
        "status": "Aberto",
        "category": "Telefonia"
    },
    {
        "external_id": "TKT-1002",
        "title": "Erro ao logar na fila",
        "description": "Ao tentar logar na fila de atendimento de Vendas, o sistema acusa erro 403 de permissão.",
        "status": "Em Andamento",
        "category": "Acesso"
    },
    {
        "external_id": "TKT-1003",
        "title": "Relatório de produtividade não carrega",
        "description": "A tela fica girando e não traz os dados de ontem.",
        "status": "Fechado",
        "category": "Relatórios"
    }
]

def fetch_external_tickets() -> List[Dict[str, Any]]:
    """Simulates fetching new or updated tickets from an external source."""
    return MOCK_EXTERNAL_TICKETS

def analyze_and_enrich_ticket(ticket: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applies logic to suggest a classification and a default response/debug steps.
    This simulates an 'AI' or heuristic rule engine.
    """
    title = ticket.get("title", "").lower()
    desc = ticket.get("description", "").lower()
    
    classification = "Outros"
    suggested_response = "Por favor, aguarde a análise técnica."
    is_faq = False
    
    if "áudio" in title or "webrtc" in desc or "mudo" in desc:
        classification = "Falha WebRTC"
        suggested_response = "Sugerimos realizar o teste de eco no WebRTC. Verifique se o microfone está liberado no navegador (cadeado na barra de endereço). Acesse 'Configurações' > 'Testar Áudio'."
        is_faq = True
    elif "erro 403" in desc or "permissão" in desc or "logar" in title:
        classification = "Erro de Permissão (Filas)"
        suggested_response = "O erro 403 indica falta de perfil. Verifique no painel de administração se o usuário possui a 'skill' ou grupo associado à fila desejada."
        is_faq = True
    elif "relatório" in title or "carrega" in title:
        classification = "Lentidão/Timeout em Relatórios"
        suggested_response = "Identificamos que relatórios de grandes períodos podem sofrer timeout. Tente reduzir o filtro para intervalos menores de data."
    
    enriched_ticket = dict(ticket)
    enriched_ticket["classification"] = classification
    enriched_ticket["suggested_response"] = suggested_response
    enriched_ticket["is_faq"] = is_faq
    
    return enriched_ticket

def sync_tickets():
    """Main job to fetch from external DB, enrich and save locally."""
    logger.info("Starting ticket synchronization...")
    
    raw_tickets = fetch_external_tickets()
    
    synced_count = 0
    for tkt in raw_tickets:
        try:
            enriched = analyze_and_enrich_ticket(tkt)
            upsert_ticket(enriched)
            synced_count += 1
        except Exception as e:
            logger.error(f"Error syncing ticket {tkt.get('external_id')}: {e}")
            
    logger.info(f"Synchronization completed. Processed {synced_count} tickets.")
    return {"status": "success", "synced_count": synced_count}

if __name__ == "__main__":
    # Test execution
    logging.basicConfig(level=logging.INFO)
    sync_tickets()
