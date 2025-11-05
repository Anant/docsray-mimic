# Deployment Guide

This guide explains how to deploy Docsray MCP on various platforms including Coolify.

## Docker Deployment

### Building the Docker Image

The project includes a multi-stage Dockerfile that handles SSL certificate issues that may occur in restricted network environments:

```bash
# Build production runtime image
make docker-build

# Or using Docker directly
docker build --target runtime -t docsray-mcp .
```

### Testing the Docker Image

```bash
# Run automated tests
make docker-test

# Test manually
docker run --rm docsray-mcp docsray --version
```

### Running with Docker

```bash
# Run in stdio mode (default for MCP clients)
docker run -it --rm docsray-mcp

# Run in HTTP mode (for web integrations)
docker run -it --rm -p 3000:3000 \
  -e DOCSRAY_TRANSPORT=http \
  docsray-mcp docsray start --transport http --port 3000
```

## Docker Compose Deployment

### Using Docker Compose

The project includes three pre-configured services:

1. **docsray-mcp** - Production MCP server (stdio mode)
2. **docsray-http** - HTTP mode server for web integrations
3. **docsray-dev** - Development server with all features enabled

```bash
# Start the production MCP server
docker compose up -d docsray-mcp

# Start the HTTP server
docker compose up -d docsray-http

# Start the development server (dev profile)
docker compose --profile dev up -d docsray-dev

# View logs
docker compose logs -f

# Stop all services
docker compose down
```

## Coolify Deployment

Coolify is a self-hostable platform-as-a-service alternative to Heroku. Here's how to deploy Docsray MCP on Coolify:

### Prerequisites

- Coolify instance running (self-hosted or cloud)
- Access to your Coolify dashboard
- This repository pushed to a Git provider (GitHub, GitLab, etc.)

### Deployment Steps

1. **Create a New Service**
   - In Coolify dashboard, click "New Service"
   - Select "Docker Compose" or "Dockerfile"
   - Connect to your Git repository

2. **Configuration for Dockerfile Deployment**
   - **Build Command**: `make docker-build` (or `docker build --target runtime -t docsray-mcp .`)
   - **Container Port**: 3000 (if using HTTP mode)
   - **Health Check**: `/health` endpoint (for HTTP mode)

3. **Configuration for Docker Compose Deployment**
   - Point to `docker-compose.yml`
   - Select which service to deploy (docsray-mcp or docsray-http)

4. **Environment Variables**
   
   Required variables depend on which providers you want to enable:
   
   ```env
   # Transport Mode
   DOCSRAY_TRANSPORT=stdio  # or http for web integrations
   DOCSRAY_HTTP_PORT=3000   # only needed for HTTP mode
   DOCSRAY_HTTP_HOST=0.0.0.0
   
   # Logging
   DOCSRAY_LOG_LEVEL=INFO
   
   # Providers (all optional)
   DOCSRAY_PYMUPDF_ENABLED=true
   DOCSRAY_PYTESSERACT_ENABLED=false
   
   # API Keys (only if using AI providers)
   # DOCSRAY_LLAMAPARSE_API_KEY=your_key_here
   # DOCSRAY_MISTRAL_API_KEY=your_key_here
   
   # Caching
   DOCSRAY_CACHE_ENABLED=true
   DOCSRAY_CACHE_TTL=3600
   ```

5. **Persistent Storage (Optional)**
   
   Mount volumes for persistent cache and logs:
   - `/app/cache` - Document processing cache
   - `/app/logs` - Application logs
   - `/app/data` - Document storage

6. **Deploy**
   - Click "Deploy" in Coolify
   - Monitor the build logs for any issues
   - Once deployed, verify the service is running

### SSL Certificate Handling

The Dockerfile includes automatic SSL certificate handling:

- Installs and updates ca-certificates in the build stage
- Uses `--trusted-host` fallback for pip in restrictive environments
- Should work in most corporate/proxy environments

If you encounter SSL issues during build:
- The build will automatically retry with `--trusted-host` flags
- This is safe for PyPI downloads but ensure your Coolify environment is secure

### Health Checks

For HTTP mode deployments, Coolify can use the built-in health check:

- **Endpoint**: `http://localhost:3000/health`
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3

## Troubleshooting

### Build Fails with SSL Errors

The Dockerfile includes automatic fallback for SSL issues. If you still encounter problems:

1. Check your network proxy settings
2. Ensure ca-certificates are properly installed in your base image
3. The build will automatically retry with `--trusted-host` flags

### Container Won't Start

1. Check logs: `docker compose logs docsray-mcp`
2. Verify environment variables are set correctly
3. Ensure required volumes are mounted
4. Check that ports aren't already in use

### Import Errors

If you see Python import errors:
1. Verify the package was installed: `docker run --rm docsray-mcp pip list | grep docsray`
2. Check PYTHONPATH is set correctly: `docker run --rm docsray-mcp env | grep PYTHON`

## Production Considerations

1. **API Keys**: Never commit API keys. Use environment variables or secrets management
2. **Resource Limits**: Set appropriate memory/CPU limits in docker-compose.yml or Coolify
3. **Monitoring**: Enable logging and monitoring for production deployments
4. **Updates**: Use version tags instead of `latest` for production
5. **Security**: Run as non-root user (already configured in Dockerfile)

## Development Deployment

For development with all features enabled:

```bash
# Build development image
make docker-build-dev

# Or with Docker Compose
docker compose --profile dev up -d docsray-dev
```

The development image includes:
- All optional dependencies (ocr, ai)
- Development tools (git, vim, nano, htop)
- Debug logging enabled
- Source code volume mount for hot-reloading

## Support

For issues or questions:
- Check the [main README](README.md)
- Review [CONTRIBUTING guidelines](CONTRIBUTING.md)
- Open an issue on GitHub
