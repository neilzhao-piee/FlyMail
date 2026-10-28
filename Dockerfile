# syntax=docker/dockerfile:1

# ---------- 前端构建 ----------
FROM --platform=$BUILDPLATFORM node:22-alpine AS ui
WORKDIR /build
COPY VERSION /VERSION
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- 后端运行 ----------
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    FLYMAIL_DATA_DIR=/data \
    FLYMAIL_UI_DIR=/app/backend/ui \
    HTTP_PORT=8080 \
    HTTP_HOST=0.0.0.0 \
    SOCKET_PATH=/tmp/flymail.sock \
    OAUTH_PORT=51010
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY VERSION ./VERSION
COPY backend/ ./backend
COPY --from=ui /dist/ui ./backend/ui
RUN mkdir -p /data
VOLUME ["/data"]
EXPOSE 8080 51010
CMD ["python", "backend/main.py"]
