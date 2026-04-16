#!/bin/bash
source venv/bin/activate
echo "Starting MUN Argument Builder..."
uvicorn api.server:app --reload --port 8000 &
sleep 2
open mun_webapp.html
wait
