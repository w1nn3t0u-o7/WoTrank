from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import players, stats, tournaments

app = FastAPI(title="mammoth API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(players.router, prefix="/players", tags=["players"])
app.include_router(tournaments.router, prefix="/tournaments", tags=["tournaments"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])
