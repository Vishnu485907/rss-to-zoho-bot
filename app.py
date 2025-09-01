import feedparser
import requests
import sqlite3
import time
import os
from datetime import datetime

RSS_FEED_URL = "https://rss.app/feeds/_uK2pJPoyCu8mMUt2.xml"
WEBHOOK_URL = "https://cliq.zoho.com/api/v2/channelsbyname/newsfeeda/message?zapikey=1001.df712eb8183bd653ba1a000217fd5cd7.4bf31cee4acba2c6e939d97f40e4d6fa"

def init_db():
    conn = sqlite3.connect('rss_feed.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS posted_articles
                 (id TEXT PRIMARY KEY, title TEXT, link TEXT, published TIMESTAMP)''')
    conn.commit()
    conn.close()

def check_if_posted(entry_id):
    conn = sqlite3.connect('rss_feed.db')
    c = conn.cursor()
    c.execute("SELECT id FROM posted_articles WHERE id=?", (entry_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def mark_as_posted(entry_id, title, link, published):
    conn = sqlite3.connect('rss_feed.db')
    c = conn.cursor()
    c.execute("INSERT INTO posted_articles (id, title, link, published) VALUES (?, ?, ?, ?)",
              (entry_id, title, link, published))
    conn.commit()
    conn.close()

def send_to_cliq(title, link, summary):
    message = {
        "text": f"**{title}**\n\n{summary}\n\n[Read more]({link})"
    }
    response = requests.post(WEBHOOK_URL, json=message)
    return response.status_code == 200

def check_feed():
    feed = feedparser.parse(RSS_FEED_URL)
    new_entries = 0
    
    for entry in feed.entries:
        entry_id = entry.get('id', entry.link)
        
        if not check_if_posted(entry_id):
            published = entry.get('published_parsed', entry.get('updated_parsed', None))
            if published:
                published = datetime(*published[:6])
            
            success = send_to_cliq(entry.title, entry.link, entry.summary)
            
            if success:
                mark_as_posted(entry_id, entry.title, entry.link, published)
                new_entries += 1
                print(f"Posted new article: {entry.title}")
            else:
                print(f"Failed to post article: {entry.title}")
    
    return new_entries

if __name__ == "__main__":
    init_db()
    print(f"Starting RSS feed monitor for {RSS_FEED_URL}")
    print("Press Ctrl+C to stop")
    
    while True:
        try:
            print(f"{datetime.now()}: Checking feed...")
            new_count = check_feed()
            if new_count > 0:
                print(f"Posted {new_count} new articles")
            else:
                print("No new articles found")
            time.sleep(600)
        except KeyboardInterrupt:
            print("Stopping RSS feed monitor")
            break
        except Exception as e:
            print(f"Error occurred: {e}")
            time.sleep(600)
