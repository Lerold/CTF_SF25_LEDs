#!/bin/bash

# Configuration
HOST="192.168.104.110"
PORT="5000"
SECRET="super_secret"  # Change this to match your secret.env

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to make webhook requests
make_request() {
    local challenge_id=$1
    local event=$2
    local response=$(curl -s -w "\n%{http_code}" -X POST "http://$HOST:$PORT/webhook" \
        -H "Content-Type: application/json" \
        -H "X-Webhook-Secret: $SECRET" \
        -d "{\"challenge_id\": $challenge_id, \"event\": \"$event\"}")
    
    local status_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')
    
    echo -e "Response: $body"
    echo -e "Status Code: $status_code"
    echo "----------------------------------------"
}

# Function to check health endpoint
check_health() {
    echo -e "${GREEN}Checking health endpoint...${NC}"
    curl -s "http://$HOST:$PORT/health" | python3 -m json.tool
    echo "----------------------------------------"
}

# Main test sequence
echo -e "${GREEN}Starting webhook tests...${NC}"
echo "----------------------------------------"

# Check health first
check_health

# Test solving a challenge
echo -e "${GREEN}Testing solve webhook for satellite 0...${NC}"
make_request 0 "solve"

# Wait a moment
sleep 2

# Check health again
check_health

# Test unsolving a challenge
echo -e "${GREEN}Testing unsolve webhook for satellite 0...${NC}"
make_request 0 "unsolve"

# Wait a moment
sleep 2

# Check health one final time
check_health

echo -e "${GREEN}Tests complete!${NC}" 