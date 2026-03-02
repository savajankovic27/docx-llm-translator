-- CREATE SCHEMA IF NOT EXISTS SNOWFLAKE_LEARNING_DB.SJAN_PROTOTYPES;
CREATE OR REPLACE TABLE PROTECTED_GLOSSARY (
    TERM_INDEX int IDENTITY(1,1),
    PROTECTED_TERM VARCHAR(255),
    DATE_ADDED TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)

-- CREATE TABLE "USER$SJAN@NETLIGHT.COM".PUBLIC.PROTECTED_GLOSSARY (
--     TERM_INDEX INT IDENTITY(1,1), -- Auto-incrementing index
--     PROTECTED_TERM STRING,        -- The word or phrase to protect
--     DATE_ADDED TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP() -- Automatically tracks when added
-- );

-- Insert the specific trademarks and identifiers for the Crown Corporation

-- Insert the specific trademarks and identifiers for the Crown Corporation
INSERT INTO SNOWFLAKE_LEARNING_DB.SJAN_PROTOTYPES.PROTECTED_GLOSSARY (PROTECTED_TERM)
VALUES 
    ('CDEV'), 
    ('CEEFC'), 
    ('CHMC'),
    ('IFRS'), 
    ('16342451 CANADA INC.');

-- Verify the data is there
SELECT * FROM SNOWFLAKE_LEARNING_DB.PUBLIC.PROTECTED_GLOSSARY;

-- First, ensure we are in the right context
USE WAREHOUSE SNOWFLAKE_LEARNING_WH;
USE DATABASE SNOWFLAKE_LEARNING_DB;
USE SCHEMA SJAN_PROTOTYPES;

-- Clear any previous test data to avoid duplicates
TRUNCATE TABLE PROTECTED_GLOSSARY;

-- Insert your full list of terms and words
INSERT INTO PROTECTED_GLOSSARY (PROTECTED_TERM)
VALUES 
    ('Canada Development Investment Corporation'), ('CDEV'), ('CEI'), ('CEEFC'), 
    ('CGF'), ('CGFIM'), ('CHHC'), ('CILGC'), ('CIC'), ('TMP Finance'), 
    ('TMC'), ('IFRS'), ('GAAP'), ('IAS'), ('IASB'), ('ESG'), ('CEO'), 
    ('CFO'), ('Trans Mountain Corporation'), ('Trans Mountain Pipeline'), 
    ('Government of Canada'), ('16342451 CANADA INC.'),
    ('CANADA'), ('DEVELOPMENT'), ('INVESTMENT'), ('CORPORATION');

-- Verify the count (should be 26)
SELECT COUNT(*) FROM PROTECTED_GLOSSARY;

SNOWFLAKE_LEARNING_DB.SJAN_PROTOTYPES.LLM_TOKEN_COUNT

create or replace TABLE SNOWFLAKE_LEARNING_DB.SJAN_PROTOTYPES.LLM_TOKEN_COUNT (
	TERM_INDEX NUMBER(38,0) autoincrement start 1 increment 1 noorder,
	NUMBER_OF_TOKENS NUMBER(38,0),
	DATE_ADDED TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
);