FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt ./

# Install only the runtime deps. Whisper is a heavyweight dependency that
# pulls in torch and ffmpeg; the production API uses Web Speech + Foundry
# Claude, so we skip whisper + playwright/pytest to keep the image small.
RUN sed -i '/openai-whisper/d;/playwright/d;/pytest/d;/^pytest/d' requirements.txt \
 && pip install -r requirements.txt

COPY app ./app
COPY config ./config
COPY run.py ./

EXPOSE 8000

CMD ["uvicorn", "run:app", "--host", "0.0.0.0", "--port", "8000"]
