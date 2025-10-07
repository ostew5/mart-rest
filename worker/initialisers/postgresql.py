import psycopg2, logging, os
from app_v1.helpers.rate_limits import initialiseRateLimitsTable
from app_v1.helpers.ai_jobs import initialiseAIJobsTable

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RDS_DBNAME = os.getenv("RDS_DBNAME")
RDS_USER = os.getenv("RDS_USER")
RDS_PASSWORD = os.getenv("RDS_PASSWORD")
RDS_HOST = os.getenv("RDS_HOST")
RDS_PORT = os.getenv("RDS_PORT")

DROP_TABLES = os.getenv("DROP_TABLES", "False")

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
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        return False

    if DROP_TABLES == "True":
        try:
            drop_tables_sql = """
            DROP SCHEMA public CASCADE;
            CREATE SCHEMA public;
            """
            cur = app.state.postgresql_db.cursor()
            cur.execute(drop_tables_sql)
            app.state.postgresql_db.commit()
            cur.close()
            logger.info(f"Successfully dropped tables")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")

    try:
        initialiseRateLimitsTable(app)
        initialiseAIJobsTable(app)
    except Exception as e:
        logger.error(f"Failed to initialise tables: {e}")
        return False

    logger.info("PostgreSQL and tables initialised successfully.")
    return True