import psycopg2, logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def shutdownPostgreSQL(app):
    try:
        app.state.postgresql_db.close()

        logger.info("PostgreSQL clossed successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to close PostgreSQL: {e}")
        return False