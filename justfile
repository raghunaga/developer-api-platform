# Hierarchical Device Data Dashboard - Just Commands

# Default recipe
default:
    @just --list

# Start the entire application (backend + frontend)
start:
    @echo "Starting Hierarchical Device Data Dashboard..."
    @echo "Starting backend service..."
    cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
    @echo "Backend started on http://localhost:8000"
    @sleep 2
    @echo "Starting frontend service..."
    cd frontend && npm run dev &
    @echo "Frontend started on http://localhost:5173"
    @echo ""
    @echo "✅ Application started successfully!"
    @echo "Backend API: http://localhost:8000"
    @echo "Frontend: http://localhost:5173"
    @echo "API Docs: http://localhost:8000/docs"
    @echo ""
    @echo "Press Ctrl+C to stop all services"

# Stop the entire application
stop:
    @echo "Stopping Hierarchical Device Data Dashboard..."
    @pkill -f "uvicorn main:app" || true
    @pkill -f "vite" || true
    @echo "✅ Application stopped successfully!"

# Start only the backend service
start-backend:
    @echo "Starting backend service..."
    cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Start only the frontend service
start-frontend:
    @echo "Starting frontend service..."
    cd frontend && npm run dev

# Stop only the backend service
stop-backend:
    @echo "Stopping backend service..."
    @pkill -f "uvicorn main:app" || true
    @echo "✅ Backend stopped"

# Stop only the frontend service
stop-frontend:
    @echo "Stopping frontend service..."
    @pkill -f "vite" || true
    @echo "✅ Frontend stopped"

# Initialize database with mock data
init-db:
    @echo "Initializing database with mock data..."
    cd backend && python -m scripts.seed_database
    @echo "✅ Database initialized with Verizon and AT&T mock data"

# Reset database
reset-db:
    @echo "Resetting database..."
    cd backend && python -m scripts.reset_database
    @echo "✅ Database reset"

# Run backend tests
test-backend:
    @echo "Running backend tests..."
    cd backend && python -m pytest tests/ -v

# Run frontend tests
test-frontend:
    @echo "Running frontend tests..."
    cd frontend && npm run test

# Run all tests
test: test-backend test-frontend
    @echo "✅ All tests completed"

# Run linting
lint:
    @echo "Running linting..."
    cd backend && python -m flake8 . --max-line-length=120
    cd frontend && npm run lint
    @echo "✅ Linting completed"

# Format code
format:
    @echo "Formatting code..."
    cd backend && python -m black .
    cd frontend && npm run format
    @echo "✅ Code formatted"

# Build frontend for production
build-frontend:
    @echo "Building frontend for production..."
    cd frontend && npm run build
    @echo "✅ Frontend build completed"

# Build Docker images
docker-build:
    @echo "Building Docker images..."
    docker-compose build
    @echo "✅ Docker images built"

# Start with Docker Compose
docker-start:
    @echo "Starting application with Docker Compose..."
    docker-compose up -d
    @echo "✅ Application started with Docker"
    @echo "Backend API: http://localhost:8000"
    @echo "Frontend: http://localhost:5173"

# Stop Docker Compose
docker-stop:
    @echo "Stopping Docker Compose..."
    docker-compose down
    @echo "✅ Docker Compose stopped"

# View logs
logs:
    @echo "Viewing application logs..."
    docker-compose logs -f

# Install dependencies
install:
    @echo "Installing dependencies..."
    cd backend && pip install -r requirements.txt
    cd frontend && npm install
    @echo "✅ Dependencies installed"

# Clean up
clean:
    @echo "Cleaning up..."
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    cd frontend && rm -rf node_modules dist build
    @echo "✅ Cleanup completed"

# Show status
status:
    @echo "Checking application status..."
    @echo ""
    @echo "Backend (port 8000):"
    @curl -s http://localhost:8000/health || echo "❌ Backend not running"
    @echo ""
    @echo "Frontend (port 5173):"
    @curl -s http://localhost:5173 > /dev/null && echo "✅ Frontend running" || echo "❌ Frontend not running"
    @echo ""

# Development setup
dev-setup: install init-db
    @echo "✅ Development environment setup completed"

# Production setup
prod-setup: install build-frontend docker-build
    @echo "✅ Production environment setup completed"

# Help
help:
    @echo "Hierarchical Device Data Dashboard - Just Commands"
    @echo ""
    @echo "Main Commands:"
    @echo "  just start              - Start backend and frontend"
    @echo "  just stop               - Stop backend and frontend"
    @echo "  just start-backend      - Start only backend"
    @echo "  just start-frontend     - Start only frontend"
    @echo ""
    @echo "Database Commands:"
    @echo "  just init-db            - Initialize database with mock data"
    @echo "  just reset-db           - Reset database"
    @echo ""
    @echo "Testing Commands:"
    @echo "  just test               - Run all tests"
    @echo "  just test-backend       - Run backend tests"
    @echo "  just test-frontend      - Run frontend tests"
    @echo ""
    @echo "Code Quality Commands:"
    @echo "  just lint               - Run linting"
    @echo "  just format             - Format code"
    @echo ""
    @echo "Docker Commands:"
    @echo "  just docker-build       - Build Docker images"
    @echo "  just docker-start       - Start with Docker Compose"
    @echo "  just docker-stop        - Stop Docker Compose"
    @echo "  just logs               - View Docker logs"
    @echo ""
    @echo "Setup Commands:"
    @echo "  just install            - Install dependencies"
    @echo "  just dev-setup          - Setup development environment"
    @echo "  just prod-setup         - Setup production environment"
    @echo ""
    @echo "Utility Commands:"
    @echo "  just clean              - Clean up build artifacts"
    @echo "  just status             - Check application status"
    @echo "  just help               - Show this help message"
