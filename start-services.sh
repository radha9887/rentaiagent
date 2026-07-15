#!/bin/bash
# Start RentAiAgent API
cd /home/openclaw/workspace/rentanagent
pkill -f "uvicorn main:app" 2>/dev/null
sleep 1
setsid python3 -m uvicorn main:app --host 0.0.0.0 --port 8100 >> /tmp/raa-api.log 2>&1 &
disown
echo "API PID=$!"

# Start Dashboard
pkill -f "next-server" 2>/dev/null  
sleep 1
cd /home/openclaw/workspace/rentanagent/dashboard
nohup npx next start -p 3100 >> /tmp/raa-dash.log 2>&1 &
echo "Dashboard PID=$!"

sleep 3
echo "API: $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8100/health)"
echo "Dashboard: $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3100/)"
