import json
import sys


def log(event, **fields):
    print(json.dumps({"event": event, **fields}), file=sys.stdout, flush=True)
