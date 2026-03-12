# Hierarchical Device Data Dashboard

A next-generation, AI-augmented feature for the Belden Horizon platform that enables users to navigate and visualize operational data across the complete data hierarchy using immersive spatial interfaces, natural language commands, and autonomous intelligence.

## Project Structure

```
app/
├── __init__.py
├── config.py              # Configuration management
├── models/                # Data models
│   ├── __init__.py
│   ├── base.py           # SQLAlchemy base
│   └── entities.py       # Core entities (Tenant, Customer, Site, etc.)
├── db/                    # Database module
│   ├── __init__.py
│   └── database.py       # Database connection and session management
├── services/              # Business logic services
├── api/                   # API endpoints
├── state/                 # State management
└── tests/                 # Tests
    ├── __init__.py
    ├── test_models.py
    └── test_database.py

alembic/                   # Database migrations
├── env.py
├── script.py.mako
└── versions/

pyproject.toml            # Project configuration
pytest.ini                # Pytest configuration
alembic.ini               # Alembic configuration
```

## Core Data Models

- **Tenant**: Top-level organizational unit
- **Customer**: Customer account within a tenant
- **Site**: Physical or logical location within a customer
- **Gateway**: Edge computing device that collects data
- **Device**: Edge device connected to a gateway
- **User**: Individual user account associated with a site
- **DataStream**: Continuous stream of metrics from a device

## Setup

### Prerequisites

- Python 3.10+
- pip

### Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -e ".[dev]"
```

3. Initialize the database:
```bash
python -c "from app.db import initialize_db, create_db_tables; initialize_db(); create_db_tables()"
```

## Running Tests

```bash
pytest
```

## Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

## Configuration

Copy `.env.example` to `.env` and update as needed:
```bash
cp .env.example .env
```

## Requirements Covered

This task implements the foundational infrastructure for Requirements 1-7:
- Requirement 1: Customer Selection
- Requirement 2: Site-Level Navigation
- Requirement 3: User-Level Navigation
- Requirement 4: Device Information Display
- Requirement 5: Production Plant Visualization
- Requirement 6: Production Cell Visualization
- Requirement 7: Comprehensive Customer-Level Information View
