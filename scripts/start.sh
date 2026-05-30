#!/bin/bash

NODE_OPTIONS="--max-old-space-size=4096" nohup openclaw gateway run --port 5000 > /app/work/logs/bypass/dev.log 2>&1 &