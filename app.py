import feedparser
import requests
import sqlite3
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
        print("✓ Database initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False

def check_if_posted(entry_id):
    try:
        conn = sqlite3.connect('rss_feed.db')
        c = conn.cursor()
        c.execute("SELECT id FROM posted_articles WHERE id=?", (entry_id,))
        result = c.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        print(f"✗ Database query error: {e}")
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
        print(f"✗ Database insert error: {e}")
        return False

def send_to_cliq(title, link, summary):
    # Truncate summary if it's too long
    if summary and len(summary) > 500:
        summary = summary[:500] + "..."
    
    message = {
        "text": f"**{title}**\n\n{summary}\n\n[Read more]({link})"
    }
    
    try:
        response = requests.post(WEBHOOK_URL, json=message, timeout=30)
        print(f"✓ Zoho API response status: {response.status_code}")
        return response.status_code == 200
    except requests.exceptions.Timeout:
        print("✗ Request to Zoho Cliq timed out")
        return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Request to Zoho Cliq failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error sending to Zoho: {e}")
        return False

def check_feed():
    try:
        print("📡 Parsing RSS feed...")
        feed = feedparser.parse(RSS_FEED_URL)
        print(f"✓ RSS feed status: {feed.get('status', 'Unknown')}")
        print(f"✓ Number of entries: {len(feed.entries)}")
        
        if not feed.entries:
            print("ℹ No entries found in RSS feed")
            return 0
            
    except Exception as e:
        print(f"✗ Failed to parse RSS feed: {e}")
        return 0
        
    new_entries = 0
    
    for i, entry in enumerate(feed.entries):
        print(f"📄 Processing entry {i+1}/{len(feed.entries)}")
        
        # Get entry ID or use link as fallback
        entry_id = entry.get('id', entry.get('link', f"entry_{i}"))
        title = entry.get('title', 'No title')
        
        if not check_if_posted(entry_id):
            print(f"🆕 New entry found: {title}")
            
            # Get publication date
            published = entry.get('published_parsed') or entry.get('updated_parsed')
            if published:
                published = datetime(*published[:6])
            else:
                published = datetime.now()
            
            # Send to Zoho Cliq
            summary = entry.get('summary', entry.get('description', 'No summary available'))
            success = send_to_cliq(title, entry.link, summary)
            
            if success:
                # Save to database
                if mark_as_posted(entry_id, title, entry.link, published):
                    new_entries += 1
                    print(f"✅ Posted: {title}")
                else:
                    print(f"❌ Failed to save to database: {title}")
            else:
                print(f"❌ Failed to post to Zoho: {title}")
        else:
            print(f"ℹ Already posted: {title}")
    
    return new_entries

if __name__ == "__main__":
    print("🚀 Starting RSS to Zoho Cliq Bot")
    print("=" * 50)
    
    if init_db():
        new_count = check_feed()
        print("=" * 50)
        
        if new_count > 0:
            print(f"✅ Successfully posted {new_count} new articles")
        else:
            print("ℹ No new articles found")
        
        print("✅ Script completed successfully")
    else:
        print("❌ Script failed due to database error")
        exit(1)
