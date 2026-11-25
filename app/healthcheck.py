"""Script run by the Dockerfile HEALTHCHECK instruction.

Docker runs this every 30 seconds inside the container.
Exit code 0 = healthy, exit code 1 = unhealthy.
We use Python's standard library so the image needs no extra tools like curl.
"""
import os
import sys
import urllib.request

try:
    # Same PORT variable the server uses, so the two can never disagree.
    url = f"http://127.0.0.1:{os.getenv('PORT', '8000')}/health"
    with urllib.request.urlopen(url, timeout=2) as resp:
        sys.exit(0 if resp.status == 200 else 1)
except Exception:
    # Connection refused, timeout, etc. -> container is not healthy
    sys.exit(1)
