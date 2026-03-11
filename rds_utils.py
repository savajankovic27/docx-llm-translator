import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_rds_terms():
    """
    Connects to AWS RDS PostgreSQL and fetches
    the protected terms for the translation engine.
    """
    try:
        conn = psycopg2.connect(
            host=os.environ.get("RDS_HOST"),        # your RDS endpoint
            port=os.environ.get("RDS_PORT", 5432),
            dbname=os.environ.get("RDS_DB", "postgres"),
            user=os.environ.get("RDS_USER", "postgres"),
            password=os.environ.get("RDS_PASSWORD"),
            sslmode="require"
        )

        cursor = conn.cursor()
        cursor.execute("SELECT term FROM protected_glossary")
        terms = [row[0] for row in cursor.fetchall()]
        print(f"Successfully synced {len(terms)} terms from RDS.")
        return terms

    except Exception as e:
        print(f"Error connecting to RDS: {e}")
        # Fallback to a minimal list if the connection fails
        return ["CDEV", "CEEFC", "TMC"]
    finally:
        if 'conn' in locals():
            conn.close()


def log_token_usage(token_count):
    """
    Logs LLM token usage to RDS for cost tracking.
    """
    try:
        conn = psycopg2.connect(
            host=os.environ.get("RDS_HOST"),
            port=os.environ.get("RDS_PORT", 5432),
            dbname=os.environ.get("RDS_DB", "postgres"),
            user=os.environ.get("RDS_USER", "postgres"),
            password=os.environ.get("RDS_PASSWORD"),
            sslmode="require"
        )

        cursor = conn.cursor()

        # Create table if it doesn't exist yet
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_token_count (
                run_number SERIAL PRIMARY KEY,
                number_of_tokens INTEGER,
                run_date TIMESTAMP DEFAULT NOW()
            )
        """)

        cursor.execute(
            "INSERT INTO llm_token_count (number_of_tokens) VALUES (%s)",
            (token_count,)
        )
        conn.commit()
        print(f"Logged {token_count} tokens to RDS.")

    except Exception as e:
        print(f"Failed to log tokens: {e}")
    finally:
        if 'conn' in locals():
            conn.close()


# Test the connection by running 'python rds_utils.py'
if __name__ == "__main__":
    print("Testing RDS connection...")
    terms = get_rds_terms()
    print(f"Terms retrieved: {terms}")