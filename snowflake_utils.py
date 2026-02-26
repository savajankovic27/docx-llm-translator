import snowflake.connector
import os
from dotenv import load_dotenv

load_dotenv()

def get_snowflake_terms():
    """
    Connects to Snowflake using Netlight Azure AD SSO and fetches 
    the protected terms for the translation engine.
    """
    try:
        conn = snowflake.connector.connect(
            user='sava.jankovic@netlight.com',
            account='MUODVQQ-HG28977', # From your account details
            authenticator='externalbrowser',
            warehouse='COMPUTE_WH',
            database='SNOWFLAKE_LEARNING_DB',
            schema='PUBLIC'
        )
        
        cursor = conn.cursor()
        # Fetching terms from your newly created VARCHAR table
        cursor.execute("SELECT PROTECTED_TERM FROM PROTECTED_GLOSSARY")
        
        terms = [row[0] for row in cursor.fetchall()]
        print(f"Successfully synced {len(terms)} terms from Snowflake.")
        return terms

    except Exception as e:
        print(f"Error connecting to Snowflake: {e}")
        # Fallback to a minimal list if the connection fails
        return ["CDEV", "CEEFC", "TMC"] 
    finally:
        if 'conn' in locals():
            conn.close()