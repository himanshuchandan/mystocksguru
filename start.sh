#!/bin/bash
# Start Market Copilot on port 8001 (port 8000 reserved for rea-as okta)
source venv/bin/activate && uvicorn app.main:app --reload --port 8001
