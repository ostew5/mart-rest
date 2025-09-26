import psycopg2, logging, os
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def checkAIJobsTableExists(app):
    # This function checks if the 'aijobs' table exists in the PostgreSQL database.
    logger.info("Checking AI Jobs Table...")
    try:
        # It uses a cursor to execute a SQL query that checks for the existence of the table.
        cur = app.state.postgresql_db.cursor()
        check_table_query = """
            SELECT EXISTS (
                SELECT 1
                FROM   pg_tables
                WHERE  schemaname = 'public'
                AND    tablename = 'aijobs'
            );
            """
        cur.execute(check_table_query)
        
        result = cur.fetchone()
        logger.debug(f"Query Result: {result}")
        
        # If the table does not exist, it logs an error and returns False.
        if not result or len(result) == 0:
            logger.error("Unexpected query result format.")
            return False
        
        table_exists = result[0]
  
        if not table_exists:
            logger.info("AI Jobs Table doesn't exist")
            return False
    except Exception as e:
        # If there is an exception during the process, it rolls back any changes and logs the error before returning False.
        app.state.postgresql_db.rollback()
        logger.error(f"Error checking AI Jobs Table: {e}")
        return False
    finally:
        cur.close()

    # If the table exists, it logs a success message and returns True.
    logger.info("AI Jobs Table does exist")
    return True

def createDefaultAIJobsTable(app):
    # This function creates a default 'AIJobs' table in the PostgreSQL database if it does not already exist.
    logger.info("Creating AI Jobs Table...")
    try:
        # Attempts to create a cursor object from the PostgreSQL database connection stored in the app's state.
        cur = app.state.postgresql_db.cursor()
        
        create_table_query = """
            CREATE TABLE AIJobs (
                JobID UUID PRIMARY KEY,
                CreatedBy UUID,
                JobType VARCHAR(20) CHECK (JobType IN ('IndexResume', 'GenerateCoverletter')),
                Status VARCHAR(500),
                Created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                Finished TIMESTAMP
            );
        """
        
        # Executes the SQL query to create the table using the cursor.
        cur.execute(create_table_query)
        
        # Commits the transaction to save changes to the database if the table creation is successful.
        app.state.postgresql_db.commit()
        
        logger.info("Created Default AI Jobs Table successfully")
    except psycopg2.errors.DuplicateTable as e:
        # Catches a specific exception for duplicate table errors and rolls back the transaction.
        app.state.postgresql_db.rollback()
        logger.warning(f"Table 'AIJobs' already exists: {e}")
    except Exception as e:
        # Catches any other exceptions that may occur during the table creation process.
        app.state.postgresql_db.rollback()
        logger.error(f"An error occurred when creating AI Jobs Table: {e}")
        return False
    finally:
        cur.close()
    
    # Returns True to indicate that the table creation was successful.
    return True

def initialiseAIJobsTable(app):
    # This function initializes the 'AIJobs' table in the PostgreSQL database.
    logger.info("Initialising AI Jobs Table...")

    try:
        # If the table does not exist, logs an informational message and proceeds to create it by calling `createDefaultAIJobsTable`.
        if not checkAIJobsTableExists(app):
            logger.info("Creating Default AIJobs table since it doesn't exist.")
            createDefaultAIJobsTable(app)
        else:
            logger.info("AIJobs table already exists. Skipping creation.")
    except Exception as e:
        # Logs an error message indicating that the initialization of the AI Jobs Table failed.
        logger.error("Failed to initialise AI Jobs Table")
        exit(1)
        
    return True

def createJob(app, job_uuid, user_uuid, job_type, status):
    # This function creates a new AI job entry in the PostgreSQL database.
    logger.info(f"Creating new AI job with Job UUID: {job_uuid} and User UUID: {user_uuid}")
    
    try:
        # Inserts a new AI job record into the PostgreSQL database with the provided details and commits the transaction.
        cur = app.state.postgresql_db.cursor()
        
        query = """
            INSERT INTO AIJobs (JobID, CreatedBy, JobType, Status, Created)
            VALUES (%s, %s, %s, %s, %s);
        """
        
        created_at = datetime.utcnow()
        
        cur.execute(query, (
            job_uuid,
            user_uuid,
            job_type,
            status,
            created_at
        ))
        
        app.state.postgresql_db.commit()
        
        logger.info(f"AI job created successfully for Job UUID: {job_uuid} and User UUID: {user_uuid}")
        return True
    
    except psycopg2.DatabaseError as e:
        app.state.postgresql_db.rollback()
        logger.error(f"Database error while creating AI job: {e}")
    
    except Exception as e:
        # Catches and handles any other unexpected exceptions that may occur.
        logger.error(f"An unexpected error occurred while creating AI job: {e}")
    
    finally:
        # Ensures that the cursor is closed regardless of whether an exception was raised or not.
        cur.close()

    # Returns False to indicate that the job creation failed due to an error.
    return False

def getJob(app, job_uuid, user_uuid):
    # This function fetches AI job details from the PostgreSQL database using Job UUID and User UUID.
    logger.info(f"Fetching AI job: {job_uuid}")
    result = {}
    try:
        # Tries to execute the following block of code which involves interacting with the database to retrieve job details.
        cur = app.state.postgresql_db.cursor()
        
        query = """
            SELECT * FROM AIJobs WHERE JobID = %s AND CreatedBy = %s;
        """
        
        cur.execute(query, (job_uuid, user_uuid,))
        row = cur.fetchone()

        if row is None:
            logger.error(f"No details found for Job UUID: {job_uuid} and User UUID: {user_uuid}")
            return None

        logger.info(f"Details found for Job UUID: {job_uuid} and User UUID: {user_uuid}")

        result = {
            "JobID": str(row[0]),
            "CreatedBy": str(row[1]),
            "JobType": row[2],
            "Status": row[3],
            "Created": row[4].isoformat(),
            "Finished": row[5].isoformat() if row[5] else None
        }

    except Exception as e:
        # Catches and handles any exceptions that may occur during the database operation.
        app.state.postgresql_db.rollback()
        logger.error(f"Error fetching Job: {e}")
    finally:
        cur.close()

    # Returns the result dictionary containing the job details, or None if no details were found.
    return result

def updateJobStatus(app, job_uuid, new_status):
    # This function updates the status of an AI job in the PostgreSQL database using Job UUID and new status.
    logger.info(f"Updating AI job status for Job UUID: {job_uuid} to {new_status}")
    
    try:
        # Tries to execute the following block of code which involves interacting with the database to update the job status.
        cur = app.state.postgresql_db.cursor()
        
        query = """
            UPDATE AIJobs
            SET Status = %s
            WHERE JobID = %s;
        """
        
        cur.execute(query, (
            new_status,
            job_uuid
        ))
        
        app.state.postgresql_db.commit()
        
        if cur.rowcount == 0:
            logger.warning(f"No AI job found with Job UUID: {job_uuid}")
        else:
            logger.info(f"AI job status updated successfully for Job UUID: {job_uuid} to {new_status}")
    
    except psycopg2.DatabaseError as e:
        # Catches and handles any exceptions that may occur during the database operation.
        app.state.postgresql_db.rollback()
        logger.error(f"Database error while updating AI job status: {e}")
        return False
    except Exception as e:
        # Catches and handles any exceptions that may occur during the database operation.
        logger.error(f"An unexpected error occurred while updating AI job status: {e}")
        return False
    finally:
        cur.close()
    
    # Returns True to indicate that the job status was updated successfully, otherwise returns False.
    return True

def completeJob(app, job_uuid):
    # This function marks an AI job as completed in the PostgreSQL database using Job UUID.
    logger.info(f"Marking AI job as completed for Job UUID: {job_uuid}")
    
    try:
        # Tries to execute the following block of code which involves interacting with the database to update the job status and completion time.
        cur = app.state.postgresql_db.cursor()
        
        query = """
            UPDATE AIJobs
            SET Status = %s, Finished = %s
            WHERE JobID = %s;
        """
        
        finished_at = datetime.utcnow()
        
        cur.execute(query, (
            "Completed",
            finished_at,
            job_uuid
        ))
        
        app.state.postgresql_db.commit()
        
        if cur.rowcount == 0:
            logger.warning(f"No AI job found with Job UUID: {job_uuid}")
        else:
            logger.info(f"AI job marked as completed successfully for Job UUID: {job_uuid} at {finished_at}")
        
        return True
    
    except psycopg2.DatabaseError as e:
        # Catches and handles any exceptions that may occur during the database operation.
        app.state.postgresql_db.rollback()
        logger.error(f"Database error while marking AI job as completed: {e}")
    
    except Exception as e:
        # Catches and handles any exceptions that may occur during the database operation.
        logger.error(f"An unexpected error occurred while marking AI job as completed: {e}")
    
    finally:
        cur.close()
    
    # Returns True to indicate that the job was marked as completed successfully, otherwise returns False.
    return False

def getRecentJobs(app, user_uuid):
    # This function retrieves recent AI jobs (from the past hour) for a given user from the PostgreSQL database.
    logger.info("Getting jobs from user in past hour")
    try:
        # Tries to execute the following block of code which involves interacting with the database to fetch recent job details.
        cur = app.state.postgresql_db.cursor()

        query = """
        SELECT *
        FROM AIJobs
        WHERE Created > NOW() - INTERVAL '1 hour' AND CreatedBy = %s;
        """

        cur.execute(query, (user_uuid,))
        
        recent_jobs = cur.fetchall()
        
        return recent_jobs

    except psycopg2.DatabaseError as e:
        # Catches and handles any exceptions that may occur during the database operation.
        app.state.postgresql_db.rollback()
        logger.error(f"Database error while marking AI job as completed: {e}")
    
    except Exception as e:
        # Catches and handles any exceptions that may occur during the database operation.
        logger.error(f"An unexpected error occurred while marking AI job as completed: {e}")
    
    finally:
        cur.close()

    # Returns a list of recent jobs or an empty list if no jobs were found or an error occurred.
    return []