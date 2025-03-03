import urllib3
import json
from urllib.parse import urlencode
import os
import logging
import psycopg2  # type: ignore # Package used for interacting with PostgreSQL db
from dotenv import load_dotenv  # Import dotenv to load environment variables

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger()
logger.setLevel('INFO')

# Fetching environment variables from .env file
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REFRESH_TOKEN = os.getenv('SPOTIFY_REFRESH_TOKEN')
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER_NAME = os.getenv('DB_USER_NAME')
DB_USER_PASSWORD = os.getenv('DB_USER_PASSWORD')

def lambda_handler(event, context):
    """Retrieve the user's recent listening history from Spotify and store it in a PostgreSQL database."""
    # Initialize a PoolManager instance
    http = urllib3.PoolManager()

    # Define the URL for the token refresh endpoint
    url = 'https://accounts.spotify.com/api/token'

    # Define the headers
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    # Define the payload with the required parameters
    payload = {
        'client_id': SPOTIFY_CLIENT_ID,
        'client_secret': SPOTIFY_CLIENT_SECRET,
        'refresh_token': SPOTIFY_REFRESH_TOKEN,
        'grant_type': 'refresh_token'
    }

    # Encode the payload
    encoded_payload = urlencode(payload)

    # Make the POST request
    response = http.request(
        'POST',
        url,
        body=encoded_payload,
        headers=headers
    )
    # Parse the response
    response_data = json.loads(response.data.decode('utf-8'))
    access_token = response_data['access_token']

    # Retrieve the recently played tracks
    response = http.request(
        "GET",
        "https://api.spotify.com/v1/me/player/recently-played?limit=50",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )

    # Parse the response to get the recently played tracks
    results = json.loads(response.data.decode('utf-8'))

    # Establishing connection to the PostgreSQL database
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER_NAME,
            password=DB_USER_PASSWORD,
            port='5432'
        )
        cur = conn.cursor()
    except Exception as e:
        logger.error(f"Error connecting to PostgreSQL: {str(e)}")
        return {"statusCode": 500, "body": json.dumps("Failed to connect to database")}

    tracks_count = 0
    for track in results["items"]:
        track_uri = track["track"]["uri"]
        track_name = track["track"]["name"]
        album_name = track["track"]["album"]["name"]
        artist_name = track["track"]["artists"][0]["name"]
        played_at = track["played_at"]
        ms_played = track["track"]["duration_ms"]
        popularity = track["track"]["popularity"]
        
        try:
            cur.execute(
                """INSERT INTO listening_history (track_uri, track_name, artist_name, album_name, played_at, ms_played, popularity)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (played_at) DO NOTHING""",
                (track_uri, track_name, artist_name, album_name, played_at, ms_played, popularity),
            )
            tracks_count += 1
            logger.info(f"Added {track_name} by {artist_name} to Postgres DB")
        except Exception as e:
            logger.error(f"Error inserting track {track_name} by {artist_name}: {str(e)}")

    # Commit and close the connection
    try:
        conn.commit()
    except Exception as e:
        logger.error(f"Error committing to database: {str(e)}")
    finally:
        conn.close()
