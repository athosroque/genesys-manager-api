from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings, GRUPOS_MIGRACAO
from auth import get_token

app = FastAPI(title="Genesys Manager")

# Setup CORS
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from routes import users, queues, groups, migration, auth_routes, audits, roles, divisions, analytics

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

@app.get("/config/groups")
async def get_groups_config():
    """
    Exibe a lista de grupos permitidos para migração configurados no backend.
    """
    return GRUPOS_MIGRACAO

@app.get("/health")
async def health_check():
    return {"status": "ok", "region": settings.GENESYS_REGION}

@app.get("/auth/test")
async def auth_test():
    token = await get_token()
    return {
        "authenticated": True,
        "token_preview": token[:10] + "..." if token else None
    }
