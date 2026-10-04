FROM python:3.12-slim

# Log immediately and avoid writing Python bytecode files.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
# Cache dependency installation until requirements change.
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 fastmcp \
    && useradd --uid 10001 --gid fastmcp --no-create-home --home-dir /tmp fastmcp

# Include the server and license; tool code is supplied through the runtime mount.
COPY server.py LICENSE ./
# Keep the image's tools directory empty.
RUN mkdir /app/tools

# Serve as an unprivileged user; probe HTTP availability without extra packages.
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).close()"
CMD ["python", "server.py"]
