import psycopg2, logging, os
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def checkAIJobsTableExists(app):
    logger.info("Checking AI Jobs Table...")
    try:
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
        
        if not result or len(result) == 0:
            logger.error("Unexpected query result format.")
            return False
        
        table_exists = result[0]
  
        if not table_exists:
            logger.info("AI Jobs Table doesn't exist")
            return False
    except Exception as e:
        app.state.postgresql_db.rollback()
        logger.error(f"Error checking AI Jobs Table: {e}")
        return False
    finally:
        cur.close()

    logger.info("AI Jobs Table does exist")
    return True

def createDefaultAIJobsTable(app):
    logger.info("Creating AI Jobs Table...")
    try:
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
        
        cur.execute(create_table_query)
        
        app.state.postgresql_db.commit()
        
        logger.info("Created Default AI Jobs Table successfully")
    except psycopg2.errors.DuplicateTable as e:
        app.state.postgresql_db.rollback()
        logger.warning(f"Table 'AIJobs' already exists: {e}")
    except Exception as e:
        app.state.postgresql_db.rollback()
        logger.error(f"An error occurred when creating AI Jobs Table: {e}")
        return False
    finally:
        cur.close()
    
    return True

def initialiseAIJobsTable(app):
    logger.info("Initialising AI Jobs Table...")

    try:
        if not checkAIJobsTableExists(app):
            logger.info("Creating Default AIJobs table since it doesn't exist.")
            createDefaultAIJobsTable(app)
        else:
            logger.info("AIJobs table already exists. Skipping creation.")
    except Exception as e:
        logger.error("Failed to initialise AI Jobs Table")
        exit(1)
        
    return True

def createJob(app, job_uuid, user_uuid, job_type, status):
    logger.info(f"Creating new AI job with Job UUID: {job_uuid} and User UUID: {user_uuid}")
    
    try:
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
        logger.error(f"An unexpected error occurred while creating AI job: {e}")
    
    finally:
        cur.close()
    
    return False

def getJob(app, job_uuid, user_uuid):
    logger.info(f"Fetching AI job: {job_uuid}")
    result = {}
    try:
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
        app.state.postgresql_db.rollback()
        logger.error(f"Error fetching Job: {e}")
    finally:
        cur.close()

    return result

def updateJobStatus(app, job_uuid, new_status):
    logger.info(f"Updating AI job status for Job UUID: {job_uuid} to {new_status}")
    
    try:
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
        app.state.postgresql_db.rollback()
        logger.error(f"Database error while updating AI job status: {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while updating AI job status: {e}")
        return False
    finally:
        cur.close()
    
    return True

def completeJob(app, job_uuid):
    logger.info(f"Marking AI job as completed for Job UUID: {job_uuid}")
    
    try:
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
        app.state.postgresql_db.rollback()
        logger.error(f"Database error while marking AI job as completed: {e}")
    
    except Exception as e:
        logger.error(f"An unexpected error occurred while marking AI job as completed: {e}")
    
    finally:
        cur.close()
    
    return False

def getRecentJobs(app, user_uuid):
    logger.info("Getting jobs from user in past hour")
    try:
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
        app.state.postgresql_db.rollback()
        logger.error(f"Database error while marking AI job as completed: {e}")
    
    except Exception as e:
        logger.error(f"An unexpected error occurred while marking AI job as completed: {e}")
    
    finally:
        cur.close()

    return []