FROM python:3.12.3-slim-bookworm

RUN pip install --no-cache-dir Pillow==10.2.0

WORKDIR /app
COPY automation/lib/*.py /app/automation/lib/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TT_PHASE5_STATE_ROOT=/data \
    TT_PHASE5_ALLOWED_CLIENT=n8n

USER 1000:1000
EXPOSE 8787
ENTRYPOINT ["python", "/app/automation/lib/phase5_worker.py"]
CMD ["--host", "0.0.0.0", "--port", "8787", "--state-root", "/data", "--allowed-client", "n8n"]
