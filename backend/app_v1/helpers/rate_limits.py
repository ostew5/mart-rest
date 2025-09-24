import psycopg2, logging, os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def checkRateLimitsTableExists(app):
    logger.info("Checking Rate Limits Table...")
    try:
        cur = app.state.postgresql_db.cursor()
        check_table_query = """
            SELECT EXISTS (
                SELECT 1 
                FROM   information_schema.tables 
                WHERE  table_schema = 'public' 
                AND    table_name = 'UserSubscriptionLevels'
            );
            """
        cur.execute(check_table_query)
        table_exists = cur.fetchone()[0]

        if not table_exists:
            logger.info("Rate Limits Table doesn't exist")
            return False
    except Exception as e:
        logger.error(f"Error checking Rate Limits Table: {e}")
        return False
    logger.info("Rate Limits Table does exist")
    return True

def createDefaultRateLimitsTable(app):
    logger.info("Creating Rate Limits Table...")
    try:
        cur = app.state.postgresql_db.cursor()
        create_table_query = """
            CREATE TABLE UserSubscriptionLevels (
                SubscriptionLevel VARCHAR(20) PRIMARY KEY,
                Description VARCHAR(100),
                MaxAPIRequestsPerHour INT,
                MaxStorageGB INT,
                CanAccessAdvancedFeatures BOOLEAN
            );
            """

        cur.execute(create_table_query)

        insert_data_query = """
            INSERT INTO UserSubscriptionLevels (SubscriptionLevel, Description, MaxAPIRequestsPerHour, MaxStorageGB, CanAccessAdvancedFeatures)
            VALUES 
            ('Basic', 'Basic subscription level with limited features.', 100, 5, FALSE),
            ('Premium', 'Premium subscription level with enhanced features.', 500, 20, TRUE),
            ('Admin', 'Administrator access with no limits and additional administrative privileges.', -1, -1, TRUE);
            """
        
        cur.execute(insert_data_query)
        app.state.postgresql_db.commit()

        logger.info("Created Default UserSubscriptionLevels successfully")
    except Exception as e:
        logger.error(f"An error occured when creating UserSubscriptionLevels: {e}")
        return False
    return True

def initialiseRateLimitsTable(app):
    logger.info("Initialising Rate Limits Table...")
    try:
        if not checkRateLimitsTableExists(app):
            if not createDefaultRateLimitsTable(app):
                raise Exception("Couldn't create table")
    except Exception as e:
        logger.error("Failed to initialise Rate Limits Table")
        exit(1)
    return True