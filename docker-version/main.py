import urllib3
import json
from urllib.parse import urlencode
import os
import logging
import psycopg2
from dotenv import load_dotenv
import time
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fetch environment variables
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REFRESH_TOKEN = os.getenv('SPOTIFY_REFRESH_TOKEN')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER_NAME = os.getenv('DB_USER_NAME')
DB_USER_PASSWORD = os.getenv('DB_USER_PASSWORD')

def create_table_if_not_exists(cur):
    """Creates the listening_history table if it doesn't exist."""
    logger.info("Checking if the table exists and creating it if not.")
    create_table_query = """
    CREATE TABLE IF NOT EXISTS listening_history (
        track_uri TEXT,
        track_name TEXT,
        artist_name TEXT,
        album_name TEXT,
        played_at TIMESTAMP PRIMARY KEY,
        ms_played INT,
        popularity INT
    );
    """
    cur.execute(create_table_query)
    logger.info("Checked for table existence and created it if necessary.")

def get_spotify_access_token():
    """Fetches a new Spotify access token using the refresh token."""
    url = 'https://accounts.spotify.com/api/token'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    payload = {
        'client_id': SPOTIFY_CLIENT_ID,
        'client_secret': SPOTIFY_CLIENT_SECRET,
        'refresh_token': SPOTIFY_REFRESH_TOKEN,
        'grant_type': 'refresh_token'
    }
    
    http = urllib3.PoolManager()
    response = http.request('POST', url, body=urlencode(payload), headers=headers)

    if response.status != 200:
        logger.error(f"Failed to get access token: {response.data.decode('utf-8')}")
        return None

    return json.loads(response.data.decode('utf-8')).get('access_token')

def get_recent_tracks(access_token):
    """Retrieves the user's recent listening history from Spotify."""
    url = "https://api.spotify.com/v1/me/player/recently-played?limit=50"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    http = urllib3.PoolManager()
    response = http.request("GET", url, headers=headers)

    if response.status != 200:
        logger.error(f"Failed to retrieve tracks: {response.data.decode('utf-8')}")
        return None

    return json.loads(response.data.decode('utf-8'))

def store_tracks_to_db(tracks):
    """Stores track data in a PostgreSQL database."""
    if not tracks:
        logger.warning("No tracks to store.")
        return

    try:
        with psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER_NAME, password=DB_USER_PASSWORD, port='5432'
        ) as conn:
            with conn.cursor() as cur:
                # Ensure table exists before inserting data
                create_table_if_not_exists(cur)

                batch = []
                for track in tracks["items"]:
                    batch.append((
                        track["track"]["uri"],
                        track["track"]["name"],
                        track["track"]["artists"][0]["name"],
                        track["track"]["album"]["name"],
                        track["played_at"],
                        track["track"]["duration_ms"],
                        track["track"]["popularity"]
                    ))

                if batch:
                    cur.executemany(
                        """INSERT INTO listening_history (track_uri, track_name, artist_name, album_name, played_at, ms_played, popularity)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT (played_at) DO NOTHING""",
                        batch
                    )
                    logger.info(f"Inserted {len(batch)} tracks into the database.")
    except Exception as e:
        logger.error(f"Error storing tracks to database: {str(e)}")

def main():
    """Main function to fetch tracks and store them in the database."""
    while True:
        logger.info(f"Fetching Spotify tracks at {datetime.now()}")

        access_token = get_spotify_access_token()
        if not access_token:
            logger.error("Failed to get Spotify access token.")
            time.sleep(900)  # Wait 15 minutes before retrying
            continue

        tracks = get_recent_tracks(access_token)
        if not tracks:
            logger.error("Failed to fetch recent tracks.")
            time.sleep(900)  # Wait 15 minutes before retrying
            continue

        store_tracks_to_db(tracks)
        
        logger.info("Waiting 15 minutes before the next batch.")
        time.sleep(900)  # Sleep for 15 minutes

if __name__ == "__main__":
    main()
