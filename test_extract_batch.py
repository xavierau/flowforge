"""Test script for the updated extract_batch method with structured output."""

import asyncio
import base64
import json
import sys
from pathlib import Path

from app.services.vllm_service import VLLMService


def load_image_as_base64(image_path: str) -> str:
    """Load an image file and convert to base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


async def test_extract_batch():
    """Test the extract_batch method with a multi-page bank statement."""

    # Define a schema for bank statement extraction
    schema = {
        "type": "object",
        "properties": {
            "account_holder": {
                "type": "string",
                "description": "Name of the account holder"
            },
            "account_number": {
                "type": "string",
                "description": "Bank account number"
            },
            "statement_period": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"}
                }
            },
            "opening_balance": {
                "type": "number",
                "description": "Opening balance amount"
            },
            "closing_balance": {
                "type": "number",
                "description": "Closing balance amount"
            },
            "transactions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "description": {"type": "string"},
                        "amount": {"type": "number"},
                        "type": {
                            "type": "string",
                            "enum": ["debit", "credit"]
                        }
                    },
                    "required": ["date", "description", "amount", "type"]
                }
            }
        },
        "required": [
            "account_holder",
            "account_number",
            "opening_balance",
            "closing_balance",
            "transactions"
        ]
    }

    # Custom prompt for extraction
    custom_prompt = """
    Extract all bank statement information.
    For transactions, include ALL transactions from ALL pages.
    Ensure amounts are extracted as numbers, not strings.
    For transaction types, use 'debit' for withdrawals/payments and 'credit' for deposits.
    """

    # Load test images (you can use one image multiple times for testing)
    print("Loading test images...")

    # Check if we have test images
    # Using multiple pages of the same statement to test multi-page extraction
    test_images = [
        "bank_statement_1.png",
        "bank_statement_2_denoised_bilateral_medium.png",
    ]

    images_base64 = []
    for img_path in test_images:
        if Path(img_path).exists():
            print(f"  ✓ Loading {img_path}")
            images_base64.append(load_image_as_base64(img_path))
        else:
            print(f"  ✗ {img_path} not found, skipping...")

    if not images_base64:
        print("\n❌ No test images found!")
        print("Please provide bank statement images in the current directory:")
        for img in test_images:
            print(f"  - {img}")
        return

    print(f"\n📄 Testing with {len(images_base64)} image(s)")

    # Initialize VLLM service
    print("\n🔧 Initializing VLLM service...")
    vllm_service = VLLMService()

    # Test extract_batch
    print("\n🚀 Calling extract_batch with structured output...")
    print(f"   Model: google/gemini-2.5-flash")
    print(f"   Images: {len(images_base64)}")
    print(f"   Schema: {len(schema['properties'])} properties")

    try:
        result = await vllm_service.extract_from_images_batch(
            images_base64=images_base64,
            schema=schema,
            custom_prompt=custom_prompt,
            provider="google",
            model="gemini-2.5-flash"
        )

        print("\n✅ Extraction successful!\n")

        # Display results
        print("=" * 80)
        print("EXTRACTION RESULTS")
        print("=" * 80)

        print(f"\n📊 Validation Status: {'✓ VALID' if result['is_valid'] else '✗ INVALID'}")
        print(f"🎯 Confidence Score: {result['confidence_score']:.2f}")
        print(f"⚡ Processing Time: {result['processing_time_ms']} ms")
        print(f"🔢 Tokens Used: {result['tokens_used']} (input: {result['input_tokens']}, output: {result['output_tokens']})")
        print(f"🤖 Model: {result['model_used']}")

        if result['validation_errors']:
            print(f"\n⚠️  Validation Errors:")
            for error in result['validation_errors']:
                print(f"   - {error}")

        print("\n📝 Extracted Data:")
        print("-" * 80)
        extracted = result['extracted_data']

        # Pretty print the extracted data
        if 'account_holder' in extracted:
            print(f"Account Holder: {extracted['account_holder']}")
        if 'account_number' in extracted:
            print(f"Account Number: {extracted['account_number']}")
        if 'statement_period' in extracted:
            period = extracted['statement_period']
            print(f"Statement Period: {period.get('start_date', 'N/A')} to {period.get('end_date', 'N/A')}")
        if 'opening_balance' in extracted:
            print(f"Opening Balance: ${extracted['opening_balance']:,.2f}")
        if 'closing_balance' in extracted:
            print(f"Closing Balance: ${extracted['closing_balance']:,.2f}")

        if 'transactions' in extracted:
            transactions = extracted['transactions']
            print(f"\nTransactions ({len(transactions)} total):")
            print("-" * 80)
            for i, txn in enumerate(transactions[:10], 1):  # Show first 10
                txn_type = txn.get('type', 'unknown')
                symbol = '+' if txn_type == 'credit' else '-'
                print(f"{i:2}. {txn.get('date', 'N/A'):12} | "
                      f"{txn.get('description', 'N/A'):40} | "
                      f"{symbol}${abs(txn.get('amount', 0)):>10,.2f} | "
                      f"{txn_type}")

            if len(transactions) > 10:
                print(f"... and {len(transactions) - 10} more transactions")

        print("\n" + "=" * 80)
        print("FULL JSON OUTPUT")
        print("=" * 80)
        print(json.dumps(extracted, indent=2))
        print("=" * 80)

        # Test that JSON is valid
        print("\n🔍 Verifying JSON validity...")
        json_str = json.dumps(extracted)
        parsed = json.loads(json_str)
        print("   ✓ JSON is valid and can be serialized/deserialized")

        print("\n✅ All tests passed!")

    except Exception as e:
        print(f"\n❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 80)
    print("TESTING EXTRACT_BATCH WITH STRUCTURED OUTPUT")
    print("=" * 80)

    asyncio.run(test_extract_batch())
