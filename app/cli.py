"""Command-line interface for database management."""

import logging
import click
from app.db.database import Database, initialize_db, create_db_tables, drop_db_tables
from app.services.database_seeder import DatabaseSeeder

logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Database management CLI."""
    pass


@cli.command()
def init_db():
    """Initialize database with schema."""
    click.echo("Initializing database...")
    try:
        initialize_db()
        create_db_tables()
        click.echo("✓ Database initialized successfully")
    except Exception as e:
        click.echo(f"✗ Error initializing database: {e}", err=True)
        raise


@cli.command()
def reset_db():
    """Reset database (delete all data)."""
    if click.confirm("Are you sure you want to reset the database? This will delete all data."):
        click.echo("Resetting database...")
        try:
            db = Database()
            session = db.get_session()
            seeder = DatabaseSeeder(session)
            seeder.reset_database()
            click.echo("✓ Database reset successfully")
        except Exception as e:
            click.echo(f"✗ Error resetting database: {e}", err=True)
            raise


@cli.command()
def seed_all():
    """Seed database with complete mock dataset."""
    click.echo("Seeding database with mock data...")
    try:
        db = Database()
        session = db.get_session()
        seeder = DatabaseSeeder(session)
        counts = seeder.seed_all()
        
        click.echo("✓ Database seeding completed successfully")
        click.echo("\nEntity counts:")
        for entity_type, count in counts.items():
            click.echo(f"  {entity_type}: {count}")
        
        # Verify seeding
        click.echo("\nVerifying seeding...")
        verification = seeder.verify_seeding()
        click.echo("✓ Verification completed")
    except Exception as e:
        click.echo(f"✗ Error seeding database: {e}", err=True)
        raise


@cli.command()
@click.option('--customer', type=click.Choice(['verizon', 'att']), required=True, help='Customer to seed')
def seed_customer(customer):
    """Seed database with data for a specific customer."""
    click.echo(f"Seeding database for customer: {customer}...")
    try:
        db = Database()
        session = db.get_session()
        seeder = DatabaseSeeder(session)
        counts = seeder.seed_customer(customer)
        
        click.echo(f"✓ Customer {customer} seeding completed successfully")
        click.echo("\nEntity counts:")
        for entity_type, count in counts.items():
            click.echo(f"  {entity_type}: {count}")
    except Exception as e:
        click.echo(f"✗ Error seeding customer: {e}", err=True)
        raise


@cli.command()
def verify():
    """Verify database seeding."""
    click.echo("Verifying database...")
    try:
        db = Database()
        session = db.get_session()
        seeder = DatabaseSeeder(session)
        counts = seeder.verify_seeding()
        
        click.echo("✓ Database verification completed")
        click.echo("\nEntity counts:")
        for entity_type, count in counts.items():
            click.echo(f"  {entity_type}: {count}")
        
        # Check expected counts
        expected = {
            "tenants": 1,
            "customers": 2,
            "sites": 10,
            "gateways": 30,
            "devices": 300,
            "users": 50,
            "data_streams": 900,
        }
        
        click.echo("\nExpected vs Actual:")
        all_match = True
        for entity_type, expected_count in expected.items():
            actual_count = counts.get(entity_type, 0)
            status = "✓" if actual_count == expected_count else "✗"
            click.echo(f"  {status} {entity_type}: expected {expected_count}, got {actual_count}")
            if actual_count != expected_count:
                all_match = False
        
        if all_match:
            click.echo("\n✓ All counts match expected values")
        else:
            click.echo("\n✗ Some counts do not match expected values")
    except Exception as e:
        click.echo(f"✗ Error verifying database: {e}", err=True)
        raise


if __name__ == "__main__":
    cli()
