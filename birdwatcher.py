import feedparser
from bs4 import BeautifulSoup
import sqlite3
import requests
import os
from datetime import datetime
import time
import logging
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Load environment variables
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
NITTER_INSTANCE = os.getenv("NITTER_INSTANCE")
BIRD_USER = os.getenv("BIRD_USER")
BIRD_TAG = f"@{BIRD_USER}"
RSS_URL = f"{NITTER_INSTANCE}/{BIRD_USER}/rss"
INTERVAL = int(os.getenv("INTERVAL", 300))
COLOUR = int(os.getenv("COLOUR", 0))

# Nitter instances require a "non-bot" user-agent header
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 "
                  "Safari/537.36"
}

def create_table():
    """Create the SQLite table if it does not exist and ensure all required columns are present."""
    logging.info("Checking database...")
    conn = sqlite3.connect("database/posts.db")
    cursor = conn.cursor()

    # Define the base table structure
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            DATE TEXT,
            TIME TEXT,
            POST_ID TEXT PRIMARY KEY,
            CONTENT TEXT,
            MEDIA TEXT,
            BIRD TEXT,
            QUOTE_ID TEXT
        )
        """
    )

    # Fetch existing columns from the table
    cursor.execute("PRAGMA table_info(posts)")
    existing_columns = [column[1] for column in cursor.fetchall()]

    conn.commit()
    conn.close()


def fetch_rss_feed():
    """Fetch and parse the RSS feed with a custom User-Agent."""
    try:
        response = requests.get(RSS_URL, headers=HEADERS, timeout=10)
        feed = feedparser.parse(response.content)
        return feed
    except requests.exceptions.Timeout:
        logging.error(f"Error fetching RSS feed: Connection timed out. Pausing for 10 minutes.")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching RSS feed: {e}")
        return None

def convert_html_to_markdown(html_content):
    """Convert HTML content to markdown suitable for Discord."""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Convert all <a> tags to markdown links
    for a in soup.find_all('a'):
        markdown_link = f"[{a.text}]({a['href']})"
        a.replace_with(markdown_link)

    return soup.get_text()

def convert_avatar_url(nitter_avatar_url):
    """Convert Nitter avatar URL to Twitter avatar URL."""
    if NITTER_INSTANCE in nitter_avatar_url:
        # Replace the Nitter domain with Twitter's domain and adjust the path
        twitter_avatar_url = nitter_avatar_url.replace(
            f"{NITTER_INSTANCE}/pic/", "https://"
        ).replace("%2F", "/")
        return twitter_avatar_url
    return nitter_avatar_url

def send_discord_webhook(post_id, content, bird, pub_date, pub_time, media_urls, title, webhook_name, avatar_url, quote_id):
    """Send a notification to Discord via webhook."""
    pub_datetime = datetime.fromisoformat(f"{pub_date}T{pub_time}")
    timestamp = pub_datetime.isoformat() + 'Z'

    # Add MP4 link to content if it exists
    if media_urls and media_urls[0].endswith(".mp4"):
        content += f"\n\n**📼 [View Video]({media_urls[0]})**"

    # Create the first embed with all properties
    embed1 = {
        "author": {"name": title},
        "description": content,
        "color": COLOUR,
        "timestamp": timestamp,
        "url": f"https://twitter.com/{bird}/status/{post_id}/"
    }

    # Determine how many embeds to send based on the number of images
    if len(media_urls) == 1 and not media_urls[0].endswith(".mp4"):
        # Single image case: Add image directly to the first embed
        embed1["image"] = {"url": media_urls[0]}
        embeds = [embed1]
    else:
        # Multiple images case: Add the first embed and then additional embeds for images
        embeds = [embed1]
        for idx, media_url in enumerate(media_urls[:4]):
            if not media_url.endswith(".mp4"):  # Ensure it's an image
                embed_image = {
                    "image": {"url": media_url},
                    "url": f"https://twitter.com/{bird}/status/{post_id}/"
                }
                embeds.append(embed_image)

    # Strip the extra username from the webhook_name
    webhook_name = webhook_name.replace(f"/ {BIRD_TAG}", "").strip()

    data = {
        "content": f"[Open tweet](<https://twitter.com/{bird}/status/{post_id}/>)",
        "username": webhook_name,  # Set webhook name dynamically
        "avatar_url": avatar_url,  # Set the avatar URL for the webhook
        "embeds": embeds[:4]  # Limit to 4 embeds total
    }

    headers = {"Content-Type": "application/json"}

    result = requests.post(WEBHOOK_URL, json=data, headers=headers)
    if 200 <= result.status_code < 300:
        logging.info(f"Webhook sent successfully: {result.status_code}")
    else:
        logging.error(f"Failed to send webhook: {result.status_code}, response:\n{result.json()}")

def process_feed():
    """Process the RSS feed and save posts to the database."""
    logging.info("Starting to process feed")
    try:
        feed = fetch_rss_feed()

        # If the feed is None due to a timeout, pause for 10 minutes and return early
        if feed is None:
            logging.info("Pausing for 10 minutes due to timeout.")
            time.sleep(600)  # Pause for 600 seconds (10 minutes)
            return

        # Log the number of entries fetched
        logging.info(f"Fetched {len(feed.entries)} entries from the RSS feed.")

        conn = sqlite3.connect("database/posts.db")
        cursor = conn.cursor()

        # Get the title of the RSS channel for the webhook name
        channel_title = feed.feed.title if 'title' in feed.feed else 'birdwatcher_dm_'

        # Convert the avatar URL to the Twitter URL format
        avatar_url = convert_avatar_url(feed.feed.image.href)

        for entry in feed.entries:
            post_id = entry.guid.split("/")[-1].split("#")[0]

            # Extract date and time separately
            pub_date_time = datetime.strptime(
                entry.published, "%a, %d %b %Y %H:%M:%S %Z"
            )
            pub_date = pub_date_time.date().isoformat()
            pub_time = pub_date_time.time().strftime("%H:%M:%S")

            # Convert HTML content to markdown
            content = convert_html_to_markdown(entry.description)

            # Replace Nitter instance links with twitter.com links
            nitter_domain = re.escape(NITTER_INSTANCE.replace("https://", "").replace("http://", ""))
            twitter_domain = "twitter.com"
            content = re.sub(
                fr"{nitter_domain}",  # Match any occurrence of the Nitter domain
                twitter_domain,      # Replace it with the Twitter domain
                content
            )

            # Fetch bird name
            bird = entry.get("author", "Unknown")  # Use 'author' field

            # Check for quoted tweet and extract QUOTE_ID
            quoted_tweet_match = re.search(
                r"https://twitter\.com/([A-Za-z0-9_]+)/status/(\d+)",
                content
            )
            quote_id = None
            if quoted_tweet_match:
                quote_id = quoted_tweet_match.group(2)

            title = f"{BIRD_TAG} tweeted"
            if quote_id:
                title = f"{BIRD_TAG} quoted a tweet"
            if bird != BIRD_TAG:
                title = f"{BIRD_TAG} retweeted {bird}'s tweet"

            logging.info(f"Processing post with ID: {post_id}, Date: {pub_date}, Time: {pub_time}, Bird: {bird}")

            # Check if post is already in the database
            cursor.execute("SELECT * FROM posts WHERE POST_ID = ?", (post_id,))
            if cursor.fetchone() is None:
                logging.info(f"Inserting new post with ID: {post_id}")

                # Try to fetch media URLs using the vxtwitter API
                media_urls = []
                try:
                    api_response = requests.get(f"https://api.vxtwitter.com/{bird}/status/{post_id}")
                    api_response.raise_for_status()  # Raise an error for bad responses
                    tweet_data = api_response.json()
                    media_urls = tweet_data.get("mediaURLs", [])
                except requests.exceptions.RequestException as e:
                    logging.error(f"Failed to fetch media URLs from API: {e}")
                    # Fallback to old method if API call fails
                    img_tags = BeautifulSoup(entry.description, "html.parser").find_all("img")
                    for img in img_tags:
                        # Replace Nitter image link with Twitter's image server link
                        image_url = img["src"].replace(
                            f"{NITTER_INSTANCE}/pic/", "https://pbs.twimg.com/media/"
                        ).replace("%2F", "/") + "?format=png"
                        media_urls.append(image_url)

                # Store the post in the database
                cursor.execute(
                    "INSERT INTO posts (DATE, TIME, POST_ID, CONTENT, MEDIA, BIRD, QUOTE_ID) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        pub_date,
                        pub_time,
                        post_id,
                        content,
                        ",".join(media_urls),
                        bird,
                        quote_id,
                    ),
                )

                conn.commit()

                # Send a notification via Discord webhook
                send_discord_webhook(post_id, content, bird, pub_date, pub_time, media_urls, title, channel_title, avatar_url, quote_id)

        conn.close()
    except Exception as e:
        logging.error(f"Error processing feed: {e}")
    logging.info(f"Feed processing completed. Waiting for {INTERVAL} seconds.")

if __name__ == "__main__":
    create_table()
    while True:
        process_feed()
        time.sleep(INTERVAL)
