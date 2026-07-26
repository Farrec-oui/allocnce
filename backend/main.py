import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers import admin, allocations, auth, files

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

# Le schéma est géré exclusivement par Alembic (`make migrate`).
# Un create_all() ici recréerait silencieusement les tables supprimées par une
# migration et ferait diverger la base des révisions.

app = FastAPI(title="AllocNCE API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(allocations.router)
app.include_router(files.router)


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve the React build in production (docker / deploy.sh).
# Le front utilise react-router en mode history : /login et /admin sont des
# routes client sans fichier correspondant. StaticFiles seul renverrait 404 sur
# un accès direct ou un rafraîchissement, d'où le repli sur index.html.
_static = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static):
    class SPAStaticFiles(StaticFiles):
        async def get_response(self, path: str, scope):
            response = await super().get_response(path, scope)
            if response.status_code == 404:
                return await super().get_response("index.html", scope)
            return response

    app.mount("/", SPAStaticFiles(directory=_static, html=True), name="frontend")
