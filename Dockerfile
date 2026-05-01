FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt ./

# Strip test-only deps so the image stays small.
RUN sed -i '/playwright/d;/^pytest/d' requirements.txt \
 && pip install -r requirements.txt

COPY app ./app
COPY config ./config
COPY run.py ./

EXPOSE 8000

CMD ["uvicorn", "run:app", "--host", "0.0.0.0", "--port", "8000"]
