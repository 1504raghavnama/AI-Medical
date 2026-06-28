from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pipeline.loader import load_all
from api.routes import router


@asynccontextmanager
async def lifespan(app):
    # Startup
    load_all()
    from pipeline.normalizer import nlp_linker
    print("All systems ready.")
    yield


app = FastAPI(
    title="AI Medical Coding System",
    description="ICD-10-CM and HCPCS code suggestion from clinical notes",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Include API routes
app.include_router(router)


# Serve frontend
@app.get("/")
def serve_frontend():
    return FileResponse("frontend/index.html")