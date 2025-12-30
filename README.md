# Setup

```
pip install requests

docker run --detach --name vespa --hostname vespa-container \
  --publish 8080:8080 --publish 19071:19071 \
  vespaengine/vespa

vespa config set target local

vespa status deploy --wait 300

vespa deploy --wait 300 vespa/app

scripts/load-and-search.py
```
