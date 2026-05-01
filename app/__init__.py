import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv


def create_app() -> FastAPI:
    load_dotenv()

    app = FastAPI(title="StreetKind AI", version="0.1.0")

    origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from .routes import router
    app.include_router(router)

    # Local-disk audio mode (dev only). When AUDIO_LOCAL_DIR is set, serve
    # uploaded audio blobs from that directory at /local-audio/. The frontend
    # gets a same-origin URL so <audio src=...> works without CORS or auth
    # plumbing. Production deployments leave this unset and use signed GCS URLs.
    audio_local_dir = os.getenv("AUDIO_LOCAL_DIR")
    if audio_local_dir:
        root = Path(audio_local_dir)
        root.mkdir(parents=True, exist_ok=True)
        app.mount(
            "/local-audio",
            StaticFiles(directory=str(root.resolve())),
            name="local-audio",
        )

    return app
