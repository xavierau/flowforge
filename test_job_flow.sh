#!/bin/bash

# Test script for complete job flow
# Usage: ./test_job_flow.sh <pdf_file> <api_token>

if [ $# -lt 1 ]; then
    echo "Usage: $0 <pdf_file> [api_token]"
    echo "Example: $0 invoice.pdf eyJ..."
    exit 1
fi

PDF_FILE=$1
API_TOKEN=${2:-""}
BASE_URL="http://localhost:8000/api/v1"

# Step 1: Upload document
echo "📤 Uploading document: $PDF_FILE"
if [ -n "$API_TOKEN" ]; then
    UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/documents/upload" \
        -H "Authorization: Bearer $API_TOKEN" \
        -F "file=@$PDF_FILE")
else
    UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/documents/upload" \
        -F "file=@$PDF_FILE")
fi

DOCUMENT_ID=$(echo $UPLOAD_RESPONSE | jq -r '.document_id')
echo "✓ Document uploaded: $DOCUMENT_ID"
echo ""

# Step 2: Create extraction job with a simple schema
echo "🔄 Creating extraction job..."
JOB_RESPONSE=$(curl -s -X POST "$BASE_URL/documents/$DOCUMENT_ID/parse" \
    -H "Authorization: Bearer $API_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "extraction_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "total_amount": {"type": "number"}
            },
            "required": ["title"]
        },
        "model_provider_config": {
            "provider": "google",
            "model": "gemini-2.5-flash"
        },
        "processing_mode": "batch"
    }')

JOB_ID=$(echo $JOB_RESPONSE | jq -r '.extraction_job_id')
echo "✓ Job created: $JOB_ID"
echo ""

# Step 3: Monitor job status
echo "⏳ Monitoring job status..."
for i in {1..30}; do
    STATUS_RESPONSE=$(curl -s -X GET "$BASE_URL/jobs/$JOB_ID/status" \
        -H "Authorization: Bearer $API_TOKEN")

    STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
    echo "  Check $i: $STATUS"

    if [ "$STATUS" = "completed" ]; then
        echo "✅ Job completed!"

        # Get results
        RESULT=$(curl -s -X GET "$BASE_URL/jobs/$JOB_ID/result" \
            -H "Authorization: Bearer $API_TOKEN")
        echo ""
        echo "📊 Results:"
        echo $RESULT | jq '.'
        exit 0
    elif [ "$STATUS" = "failed" ]; then
        echo "❌ Job failed!"
        echo $STATUS_RESPONSE | jq '.'
        exit 1
    fi

    sleep 2
done

echo "⏱️  Timeout waiting for job to complete"
exit 1
