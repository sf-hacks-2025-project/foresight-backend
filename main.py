from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.auth import router as auth_router
from routes.users import router as users_router
from routes.items import router as items_router
from modules.database import init_pinecone

pinecone_index = init_pinecone()

app = FastAPI(
    title="SFHacks API",
    description="API for SFHacks",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api", tags=["authentication"])
app.include_router(users_router, prefix="/api", tags=["users"])
app.include_router(items_router, prefix="/api", tags=["items"])

@app.get("/")
async def root():
    return {"message": "hello world"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", port=8000, reload=True)
