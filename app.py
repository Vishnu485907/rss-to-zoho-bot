import feedparser
import requests
import sqlite3
import time
import os
from datetime import datetime

RSS_FEED_URL = "https://rss.app/feeds/_uK2pJPoyCu8mMUt2.xml"
WEBHOOK_URL = "https://cliq.zoho.com/api/v2/channelsbyname/newsfeeda/message?zapikey=1001.df712eb8183bd653ba1a000217fd5cd7.4bf31cee4acba2c6e939d97f40e4d6fa"

def init_db():
    try:
        conn = sqlite3.connect('rss_feed.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS posted_articles
                     (id TEXT PRIMARY KEY, title TEXT, link TEXT, published TIMESTAMP)''')
        conn.commit()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database error: {e}")
        raise

def check_if_posted(entry_id):
    try:
        conn = sqlite3.connect('rss_feed.db')
        c = conn.cursor()
        c.execute("SELECT id FROM posted_articles WHERE id=?", (entry_id,))
        result = c.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        print(f"Database query error: {e}")
        return False

def mark_as_posted(entry_id, title, link, published):
    try:
        conn = sqlite3.connect('rss_feed.db')
        c = conn.cursor()
        c.execute("INSERT INTO posted_articles (id, title, link, published) VALUES (?, ?, ?, ?)",
                  (entry_id, title, link, published))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database insert error: {e}")
        return False

def send_to_cliq(title, link, summary):
    message = {
        "text": f"**{title}**\n\n{summary}\n\n[Read more]({link})"
    }
    try:
        response = requests.post(WEBHOOK_URL, json=message, timeout=30)
        print(f"Zoho API response status: {response.status_code}")
        if response.status_code != 200:
            print(f"Zoho API response text: {response.text}")
        return response.status_code == 200
    except requests.exceptions.Timeout:
        print("Request to Zoho Cliq timed out")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Request to Zoho Cliq failed: {e}")
        return False

def check_feed():
    try:
        print("Parsing RSS feed...")
        feed = feedparser.parse(RSS_FEED_URL)
        print(f"RSS feed status: {feed.get('status', 'Unknown')}")
        print(f"Number of entries: {len(feed.entries)}")
        
        # Check if feed parsing failed
        if feed.bozo:  # bozo flag indicates parsing issues
            print(f"RSS feed parsing error: {feed.bozo_exception}")
            return 0
    except Exception as e:
        print(f"Failed to parse RSS feed: {e}")
        return 0
        
    new_entries = 0
    
    for i, entry in enumerate(feed.entries):
        print(f"Processing entry {i+1}/{len(feed.entries)}")
        entry_id = entry.get('id', entry.link)
        
        if not check_if_posted(entry_id):
            print(f"New entry found: {entry.title}")
            published = entry.get('published_parsed', entry.get('updated_parsed', None))
            if published:
                published = datetime(*published[:6])
            
            success = send_to_cliq(entry.title, entry.link, entry.summary)
            
            if success:
                if mark_as_posted(entry_id, entry.title, entry.link, published):
                    new_entries += 1
                    print(f"Posted new article: {entry.title}")
                else:
                    print(f"Failed to save article to database: {entry.title}")
            else:
                print(f"Failed to post article to Zoho: {entry.title}")
        else:
            print(f"Already posted: {entry.title}")
    
    return new_entries

if __name__ == "__main__":
    try:
        print("Starting RSS feed monitor...")
        init_db()
        print(f"Checking feed: {RSS_FEED_URL}")
        print(f"Current time: {datetime.now()}")
        new_count = check_feed()
        if new_count > 0:
            print(f"Successfully posted {new_count} new articles")
        else:
            print("No new articles found")
        print("RSS check completed successfully")
    except Exception as e:
        print(f"Critical error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
