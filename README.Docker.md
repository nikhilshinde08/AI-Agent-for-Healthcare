# Healthcare Database Assistant - Docker Setup

This guide explains how to run the Healthcare Database Assistant using Docker.

## Prerequisites

- Docker Engine 20.10 or later
- Docker Compose 2.0 or later
- At least 4GB of available RAM
- At least 10GB of available disk space

## Quick Start

1. **Clone the repository and navigate to the project directory**
   ```bash
   cd healthcare-database-assistant
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

3. **Build and start all services**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - Frontend: http://localhost
   - Backend API: http://localhost:8002
   - Database: localhost:5432

## Services

### Backend (Python/FastAPI)
- **Port**: 8002
- **Container**: healthcare-assistant-backend
- **Health check**: http://localhost:8002/health

### Frontend (React/Nginx)
- **Port**: 80
- **Container**: healthcare-assistant-frontend
- **Nginx configuration**: Proxies API calls to backend

### Database (PostgreSQL)
- **Port**: 5432
- **Container**: healthcare-assistant-db
- **Database**: healthcare_db
- **Username**: healthcareuser
- **Password**: healthcarepass

## Docker Commands

### Start services
```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# Build and start
docker-compose up --build
```

### Stop services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### View logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs backend
docker-compose logs frontend
docker-compose logs db
```

### Development

#### Rebuild specific service
```bash
docker-compose build backend
docker-compose build frontend
```

#### Run database migrations
```bash
docker-compose exec backend python -c "from src.database.connection import DatabaseConnection; DatabaseConnection().create_tables()"
```

#### Access database
```bash
docker-compose exec db psql -U healthcareuser -d healthcare_db
```

## Environment Variables

Required environment variables in `.env` file:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name
AZURE_OPENAI_MODEL_NAME=gpt-4

# Tavily Search (Optional)
TAVILY_API_KEY=your_tavily_key

# Database (configured in docker-compose.yml)
DATABASE_URL=postgresql://healthcareuser:healthcarepass@db:5432/healthcare_db
```

## Volumes

The application uses the following volumes for data persistence:

- `postgres_data`: Database files
- `./api_storage`: API request/response storage
- `./conversation_memory`: Chat conversation history
- `./json_responses`: JSON response cache
- `./logs`: Application logs

## Networking

All services run on a custom Docker network `healthcare-network` for internal communication.

## Troubleshooting

### Common Issues

1. **Port conflicts**
   ```bash
   # Check if ports are in use
   netstat -tlnp | grep :80
   netstat -tlnp | grep :8002
   ```

2. **Permission issues with volumes**
   ```bash
   # Fix permissions
   sudo chown -R $USER:$USER ./api_storage ./conversation_memory ./json_responses ./logs
   ```

3. **Database connection issues**
   ```bash
   # Check database status
   docker-compose logs db
   
   # Restart database
   docker-compose restart db
   ```

4. **Frontend build issues**
   ```bash
   # Clear node modules and rebuild
   docker-compose build --no-cache frontend
   ```

### View running containers
```bash
docker-compose ps
```

### Check container health
```bash
docker-compose exec backend curl http://localhost:8002/health
```

### Reset everything
```bash
# Stop and remove all containers, networks, volumes
docker-compose down -v --remove-orphans
docker system prune -f
```

## Production Deployment

For production deployment, consider:

1. **Use environment-specific compose files**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up
   ```

2. **Enable SSL/TLS**
   - Configure reverse proxy (nginx/traefik)
   - Use Let's Encrypt certificates

3. **Database backup strategy**
   ```bash
   # Backup database
   docker-compose exec db pg_dump -U healthcareuser healthcare_db > backup.sql
   ```

4. **Resource limits**
   - Add memory and CPU limits to docker-compose.yml
   - Monitor resource usage

5. **Security considerations**
   - Change default passwords
   - Use secrets management
   - Enable firewall rules
   - Regular security updates