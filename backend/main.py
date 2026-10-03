from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings, GRUPOS_MIGRACAO, validate_production_settings
from auth import get_token
from auth_local import get_current_user, require_admin

IS_PRODUCTION = settings.ENVIRONMENT == "production"
validate_production_settings()

# Swagger/OpenAPI só fora de produção — evita mapa da API exposto publicamente
app = FastAPI(
    title="Genesys Manager",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)

# Setup CORS
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
if IS_PRODUCTION:
    origins = [o for o in origins if "localhost" not in o and "127.0.0.1" not in o]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)
from routes import users, queues, groups, migration, auth_routes, audits, roles, divisions, analytics, diagnostics, tickets, system_diagnostics

# Rotas de negócio
app.include_router(auth_routes.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(queues.router, prefix="/queues", tags=["Queues"])
app.include_router(groups.router, prefix="/groups", tags=["Groups"])
app.include_router(roles.router, prefix="/roles", tags=["Roles"])
app.include_router(divisions.router, prefix="/divisions", tags=["Divisions"])
app.include_router(migration.router, prefix="/migration", tags=["Migration"])
app.include_router(audits.router, prefix="/audits", tags=["Auditoria"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(diagnostics.router, prefix="/diagnostics", tags=["Diagnostics"])
app.include_router(system_diagnostics.router, prefix="/system-diagnostics", tags=["System Diagnostics"])
app.include_router(tickets.router, prefix="/tickets", tags=["Tickets"])

@app.get("/config/groups", dependencies=[Depends(get_current_user)])
async def get_groups_config():
    """
    Exibe a lista de grupos permitidos para migração configurados no backend.
    """
    return GRUPOS_MIGRACAO

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/auth/test", dependencies=[Depends(require_admin)])
async def auth_test():
    # Não devolve nenhum trecho do token Genesys — só confirma que a credencial funciona
    token = await get_token()
    return {"authenticated": bool(token)}
