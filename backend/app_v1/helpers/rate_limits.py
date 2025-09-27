import psycopg2, logging, os
from fastapi import Request, HTTPException
from app_v1.helpers.cognito_auth import authenticateSession
from app_v1.helpers.ai_jobs import getRecentJobs

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
                FROM   pg_tables
                WHERE  schemaname = 'public'
                AND    tablename = 'usersubscriptionlevels'
            );
            """
        cur.execute(check_table_query)
        
        # Fetch the result and log it
        result = cur.fetchone()
        logger.debug(f"Query Result: {result}")
        
        if not result or len(result) == 0:
            logger.error("Unexpected query result format.")
            return False
        
        table_exists = result[0]
  
        if not table_exists:
            logger.info("Rate Limits Table doesn't exist")
            return False
    except Exception as e:
        app.state.postgresql_db.rollback()
        logger.error(f"Error checking Rate Limits Table: {e}")
        return False
    finally:
        cur.close()  # Ensure the cursor is closed

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
                MaxFileUploadKB INT
            );
            """

        cur.execute(create_table_query)

        insert_data_query = """
            INSERT INTO UserSubscriptionLevels (SubscriptionLevel, Description, MaxAPIRequestsPerHour, MaxFileUploadKB)
            VALUES 
            ('Basic', 'Basic subscription level with limited features.', 5, 100),
            ('Premium', 'Premium subscription level with enhanced features.', 100, 500),
            ('Admin', 'Administrator access with no limits.', -1, -1);
            """
        
        cur.execute(insert_data_query)
        app.state.postgresql_db.commit()

        logger.info("Created Default UserSubscriptionLevels successfully")
    except psycopg2.errors.DuplicateTable as e:
        app.state.postgresql_db.rollback()
        logger.warning(f"Table 'UserSubscriptionLevels' already exists: {e}")
    except Exception as e:
        app.state.postgresql_db.rollback()
        logger.error(f"An error occured when creating UserSubscriptionLevels: {e}")
        return False
    return True

def initialiseRateLimitsTable(app):
    logger.info("Initialising Rate Limits Table...")

    try:
        if not checkRateLimitsTableExists(app):
            logger.info("Creating Default UserSubscriptionLevels table since it doesn't exist.")
            createDefaultRateLimitsTable(app)
        else:
            logger.info("UserSubscriptionLevels table already exists. Skipping creation.")
    except Exception as e:
        logger.error("Failed to initialise Rate Limits Table")
        exit(1)
    return True

def getValidSubscriptionLevels(app):
    logger.info("Fetching valid Subscription Levels...")
    try:
        cur = app.state.postgresql_db.cursor()
        
        query = """
            SELECT SubscriptionLevel FROM UserSubscriptionLevels;
        """
        
        cur.execute(query)
        subscription_levels = [row[0] for row in cur.fetchall()]
        
        logger.info(f"Found {len(subscription_levels)} valid subscription levels.")
        return subscription_levels
    except Exception as e:
        app.state.postgresql_db.rollback()
        logger.error(f"Error fetching Subscription Levels: {e}")
        return []

def getSubscription(app, subscription_level):
    logger.info(f"Fetching user subscription: {subscription_level}")
    try:
        cur = app.state.postgresql_db.cursor()
        
        query = """
            SELECT * FROM UserSubscriptionLevels WHERE SubscriptionLevel = %s;
        """
        
        cur.execute(query, (subscription_level, ))
        row = cur.fetchone()
        
        if row is None:
            logger.error(f"No details found for subscription level: {subscription_level}")
            return None

        logger.info(f"Details found for subscription level: {subscription_level}")
        return {
            "SubscriptionLevel": row[0], 
            "Description": row[1], 
            "MaxAPIRequestsPerHour": row[2], 
            "MaxFileUploadKB": row[3]
        }
    except Exception as e:
        app.state.postgresql_db.rollback()
        logger.error(f"Error fetching Subscription Levels: {e}")
        return {}

def authenticateSessionAndRateLimit(request: Request):
    logger.info("Authenticating user and enforcing rate limits")

    user_data = authenticateSession(request)
    logger.info(f"Got user_data: {user_data}")

    uuid = ""
    
    for attr in user_data['UserAttributes']:
        if attr['Name'] == "sub":
            uuid = attr['Value']
    
    if uuid == "":
        raise HTTPException(status_code=401, detail=f"authenticateSessionAndRateLimit: No uuid (sub) in user_data")
    logger.info(f"Got uuid: {uuid}")

    subscription = {}
    for attr in user_data['UserAttributes']:
        if attr['Name'] == "custom:subscriptionLevel":
            subscription = getSubscription(request.app, attr['Value'])

    if subscription == {}:
        raise HTTPException(status_code=401, detail=f"authenticateSessionAndRateLimit: No custom:subscriptionLevel in user_data")
    logger.info(f"Got subscription: {subscription}")

    n_jobs_by_user = len(getRecentJobs(request.app, uuid))
    logger.info(f"Got number of recent jobs: {n_jobs_by_user}")

    if n_jobs_by_user >= subscription['MaxAPIRequestsPerHour'] and subscription['MaxAPIRequestsPerHour'] > 0:
        raise HTTPException(status_code=429, detail=f"User has used their subscription rate limit of {subscription['MaxAPIRequestsPerHour']} API requests per hour")

    return user_data