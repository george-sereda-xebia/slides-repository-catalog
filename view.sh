#!/bin/bash
# View catalog in browser

echo "🌐 Starting catalog server..."
cd site && python3 -m http.server 8000 &
PID=$!
echo "Server started (PID: $PID)"
echo ""
echo "Open: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop"
wait $PID
