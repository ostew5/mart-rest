Assignment 2 - Cloud Services Exercises - Response to Criteria
================================================

Instructions
------------------------------------------------
- Keep this file named A2_response_to_criteria.md, do not change the name
- Upload this file along with your code in the root directory of your project
- Upload this file in the current Markdown format (.md extension)
- Do not delete or rearrange sections.  If you did not attempt a criterion, leave it blank
- Text inside [ ] like [eg. S3 ] are examples and should be removed


Overview
------------------------------------------------

- **Name:** Oliver Stewart
- **Student number:** n11588608
- **Partner name (if applicable):** NA
- **Application name:** Mart - LLM & RAG Powered Cover Letter Generator
- **Two line description:** I implemented a pipeline which automates indexing an applicants resume, web scraping a job listing, generating a ready-to-use cover letter pdf. The combination of Retrieval-Augmented Generation and the Large Language Model enables hallucination resistant cover letter generation that doesn't invent facts about the applicant.
- **EC2 instance name or ID:** A2-Southeast2-n11588608-CoverletterGen (i-00cdcb39555a29393)

------------------------------------------------

### Core - First data persistence service

- **AWS service name:**  

    S3

- **What data is being stored?:** 

    - `a2-n11588608-coverlettergen:resumes/` Paired indexed resume data (raw text compressed as a `.bin` and text vector embeddings as `.pkl`)
    - `a2-n11588608-coverlettergen:cover_letters/`Generated cover letters (as a `.pdf`)

- **Why is this service suited to this data?:** 

    The whole indexed resume data must be retrieved all at once for processing and the generated cover letters should also be retrieved all at once for user download.

- **Why is are the other services used not suitable for this data?:** 

    Other suitable resources may be: RDS and EFS. RDS would be beneficial if the application knew beforehand where the most relevant sections of the resume for each section of the cover letter was, since it doesn't and it needs the entire dataset of vector embeddings to be loaded in memory to make comparisons a service which retrieves the whole file is better suited, these services are EFS and S3. EFS is known for being fast at downloading and uploading files, however, metadata operations can be slow with EFS, unlike S3. As the files stored, `.pkl`, `.bin`, `.pdf` aren't very large we don't need exceedingly fast download speeds, however, a quicker retrieval of the file we are looking for would be beneficial. As the number of user's using the app increases, EFS may struggle with fetching files from a massive set of files.

- **Bucket/instance/table name:**

    - a2-n11588608-coverlettergen

- **Video timestamp:**

- **Relevant files:**

    `backend/app_v1/app.py` @ line 32

    `backend/app_v1/initialisers/s3.py`

    `backend/app_v1/routers/generate_cover_letter/result.py` @ line 19, 51

    `backend/app_v1/routers/generate_cover_letter/start.py` @ line 33, 247, 325, 376, 385

    `backend/app_v1/routers/index_resume/start.py` @ line 23, 148, 197

### Core - Second data persistence service

- **AWS service name:**  

    Aurora and RDS

- **What data is being stored?:** 

    Subscription Levels and User Launched Jobs data

- **Why is this service suited to this data?:** 

    Allows centralized and stateless control and communication between server's running the same webapp, allowing scaling. If subscription level's need to be added or changed, only the SQL table `UserSubscriptionLevels` needs to be updated, if a job is added on one EC2 instance and the user needs to check the status of that job from another EC2 instance, all job's statuses are stored on the SQL table `AIJobs`. The `AIJobs` table also handles ownership of jobs, allowing users to only access jobs they've started.

- **Why is are the other services used not suitable for this data?:** 

    A NoSQL database could have been used, however, the structure of the data is very consistent, every element has the exact same items with the exact same datatype, therefore, using a NoSQL database would only slow down operations which are optimized on SQL databases.

- **Bucket/instance/table name:**

    > **This had to be self-supplied, I could not start an RDS instance in time due to a pinwheel of death on the *Aurora and RDS* page on the *AWSReservedSSO_CAB432-STUDENT* AWS account. Therefore I have started a free trial with my personal email and have hosted the Aurora and RDS instance there. I didn't realize Aurora and RDS was difficult until too late to be able to go into a practical to get this sorted so unfortunately this will have to do. **

    Aurora and RDS database details:

    | Name                | Value                                                        |
    | ------------------- | ------------------------------------------------------------ |
    | DB identifier       | database-1                                                   |
    | Master username     | postgres                                                     |
    | Master password     | > this can be found on my EC2 instance at `~/mart-rest/.env` as `RDS_PASSWORD` if you need it |
    | PostgreSQL Endpoint | database-1.cfwa8cs6gobn.ap-southeast-2.rds.amazonaws.com     |
    | PostgreSQL Port     | 5432                                                         |
    | Inbound rule        | **Type**: PostgreSQL, **Protocol**: TCP, **Port range**: 5432, **Source**: 0.0.0.0/0 |
    | Outbound rule       | **Type**: All traffic, **Protocol**: All, **Port range**: All, **Source**: 0.0.0.0/0 |

    Tables:

    ```sql
    CREATE TABLE UserSubscriptionLevels (
        SubscriptionLevel VARCHAR(20) PRIMARY KEY,
        Description VARCHAR(100),
        MaxAPIRequestsPerHour INT,
        MaxFileUploadKB INT
    );
    ```

    ```sql
    CREATE TABLE AIJobs (
    	JobID UUID PRIMARY KEY,
    	CreatedBy UUID,
        JobType VARCHAR(20) CHECK (JobType IN ('IndexResume', 'GenerateCoverletter')),
        Status VARCHAR(500),
        Created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        Finished TIMESTAMP
    );
    ```

- **Video timestamp:**

- **Relevant files:**
    `backend/app_v1/app.py` @ line 35
    
    `backend/app_v1/initialisers/postgresql.py`
    
    `backend/app_v1/helpers/ai_jobs.py` @ line 13, 56, 113, 158, 196, 239, 284
    
    `backend/app_v1/helpers/rate_limits.py` @ line 13, 50, 100, 121

### Third data service

- **AWS service name:**  [eg. RDS]
- **What data is being stored?:** [eg video metadata]
- **Why is this service suited to this data?:** [eg. ]
- **Why is are the other services used not suitable for this data?:** [eg. Advanced video search requires complex querries which are not available on S3 and inefficient on DynamoDB]
- **Bucket/instance/table name:**
- **Video timestamp:**
- **Relevant files:**
    -

### S3 Pre-signed URLs

- **S3 Bucket names:**
- **Video timestamp:**
- **Relevant files:**
    -

### In-memory cache

- **ElastiCache instance name:**
- **What data is being cached?:** [eg. Thumbnails from YouTube videos obatined from external API]
- **Why is this data likely to be accessed frequently?:** [ eg. Thumbnails from popular YouTube videos are likely to be shown to multiple users ]
- **Video timestamp:**
- **Relevant files:**
    -

### Core - Statelessness

- **What data is stored within your application that is not stored in cloud data services?:** 

    Intermediate indexed resume data (vector embeddings as `.pkl` and raw compressed text as `.bin`) Subscription Level Data and the Jobs being completed on the network.

- **Why is this data not considered persistent state?:** 

    Intermediate files can be recreated from source if they are lost and subscription levels should be able to be updated if users require more or less API requests / File Upload limits.

- **How does your application ensure data consistency if the app suddenly stops?:** 

    If the app suddenly stops the jobs can be easily restarted

- **Relevant files:**
    `backend/app_v1/routers/generate_cover_letter/start.py`
    
    `backend/app_v1/routers/index_resume/start.py`

### Graceful handling of persistent connections

- **Type of persistent connection and use:** NA no persistent connections


### Core - Authentication with Cognito

- **User pool name: **

  n11588608-CoverletterGen-assessment-2

- **How are authentication tokens handled by the client?:** 

  Response to `/v1/user/authenticate` endpoint returns an AccessToken which is set as a Bearer Token as the cookie

- **Video timestamp:**

- **Relevant files:**
`backend/app_v1/app.py` @ Line 33
`backend/app_v1/initialisers/cognito.py`
`backend/app_v1/helpers/cognito_auth.py` @ Line 26, 
`backend/app_v1/routers/user/authenticate.py` @ Line 27
`backend/app_v1/routers/user/change_subscription.py` @ Line 35
`backend/app_v1/routers/user/confirm.py` @ Line 27
`backend/app_v1/routers/user/register.py` @ Line 35

### Cognito multi-factor authentication

- **What factors are used for authentication:** [eg. password, SMS code]
- **Video timestamp:**
- **Relevant files:**
    -

### Cognito federated identities

- **Identity providers used:**
- **Video timestamp:**
- **Relevant files:**
    -

### Cognito groups

- **How are groups used to set permissions?:** [eg. 'admin' users can delete and ban other users]
- **Video timestamp:**
- **Relevant files:**
    -

### Core - DNS with Route53

- **Subdomain**:  

  mart.cab432.com

- **Video timestamp:**

### Parameter store

- **Parameter names:** [eg. n1234567/base_url]
- **Video timestamp:**
- **Relevant files:**
    -

### Secrets manager

- **Secrets names:** [eg. n1234567-youtube-api-key]
- **Video timestamp:**
- **Relevant files:**
    -

### Infrastructure as code

- **Technology used:**
- **Services deployed:**
- **Video timestamp:**
- **Relevant files:**
    -

### Other (with prior approval only)

- **Description:**
- **Video timestamp:**
- **Relevant files:**
    -

### Other (with prior permission only)

- **Description:**
- **Video timestamp:**
- **Relevant files:**
    -
