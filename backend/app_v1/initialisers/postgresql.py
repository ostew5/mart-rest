import psycopg2, logging, os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RDS_DBNAME = os.getenv("RDS_DBNAME")
RDS_USER = os.getenv("RDS_USER")
RDS_PASSWORD = os.getenv("RDS_PASSWORD")
RDS_HOST = os.getenv("RDS_HOST")
RDS_PORT = os.getenv("RDS_PORT")

def initialisePostgreSQL(app):
    logger.info("Initialising PostgreSQL...")
    try:
        conn = psycopg2.connect(
            dbname=RDS_DBNAME,
            user=RDS_USER,
            password=RDS_PASSWORD,
            host=RDS_HOST,
            port=RDS_PORT
        )
        app.state.postgresql_db = conn
        logger.info("Connected to PostgreSQL database.")
        
        logger.info("Verifying PostgreSQL connection...")
        cur = conn.cursor()
        cur.execute("SELECT version();")
        db_version = cur.fetchone()
        logger.info(f"PostgreSQL database version: {db_version}")

        cur.close()
        logger.info("PostgreSQL initialised successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        return False