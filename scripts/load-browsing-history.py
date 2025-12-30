#!/usr/bin/env python3

import json
import requests
import sqlite3
import tempfile
import shutil
import os
import sys

base_url = 'http://localhost:8080'

# Read from ARGV or default to Chrome history path
default_chrome_history_path = os.path.join(os.getenv('HOME'), 'Library/Application Support/Google/Chrome/Default/History')
chrome_history_path = sys.argv[1] if len(sys.argv) > 1 else default_chrome_history_path

documents = []
with tempfile.TemporaryDirectory() as tmp_dir:
    tmp_history = f"{tmp_dir}/History"
    shutil.copy(chrome_history_path, tmp_history)
    conn = sqlite3.connect(tmp_history)
    cursor = conn.cursor()
    # TODO: Skip previously processed urls
    cursor.execute("SELECT url, title, last_visit_time FROM urls")
    rows = cursor.fetchall()
    for row in rows:
        url, title, last_visit_time = row
        print(f"Processing URL: {url}")
        # TODO: Load the actual current page content
        content = f"Visited on {last_visit_time}"
        documents.append({
            "fields": {
                "url": url,
                "title": title,
                "domain": requests.utils.urlparse(url).netloc,
                "content": content,
            }
        })
    conn.close()

for doc in documents:
    data = json.dumps(doc)
    # Encode url as doc_id using URL encoding
    url = doc["fields"]["url"]
    doc_id = requests.utils.quote(url, safe='')
    print(f'Indexing document: {url}')
    response = requests.post(f'{base_url}/document/v1/docs/websites/docid/{doc_id}', data=data, headers={'Content-Type': 'application/json'})
    print(f'Response: {response.status_code} - {response.text}')
