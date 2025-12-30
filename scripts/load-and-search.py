#!/usr/bin/env python3

import json
import requests

base_url = 'http://localhost:8080'

documents = [
        {
            "fields": {
                "url": "https://google.com/",
                "title": "Google",
                "domain": "google.com",
                "content": "I'm feeling lucky",
            }
        }
]

for doc in documents:
    data = json.dumps(doc)
    # Encode url as doc_id using URL encoding
    url = doc["fields"]["url"]
    doc_id = requests.utils.quote(url, safe='')
    print(f'Indexing document: {url}')
    response = requests.post(f'{base_url}/document/v1/docs/websites/docid/{doc_id}', data=data, headers={'Content-Type': 'application/json'})
    print(f'Response: {response.status_code} - {response.text}')

# Perform a search

query = 'select * from sources * where default contains \"Google\"'

search_data = {
    "yql": query,
    "hits": 10,
}

response = requests.post(f'{base_url}/search/', data=json.dumps(search_data), headers={'Content-Type': 'application/json'})
print(f'Search Response: {response.status_code} - {response.text}')
