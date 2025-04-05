from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.vision import router as vision_router
from routes.conversation import router as conversation_router
from routes.user import router as user_router
from routes.tts import router as tts_router

app = FastAPI(
    title="SFHacks API",
    description="API for SFHacks Project",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router, prefix="/api", tags=["user"])
app.include_router(vision_router, prefix="/api", tags=["vision"])
app.include_router(conversation_router, prefix="/api", tags=["conversation"])
app.include_router(tts_router, prefix="/api", tags=["tts"])

@app.get("/")
async def root():
    return {"message": "hi i am running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", port=8000)
