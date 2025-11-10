import type { Template } from '@/types/template';

export const receiptTemplate: Template = {
  id: 'receipt',
  name: 'Receipt Schema',
  description: 'Retail receipt extraction schema for purchases, refunds, and transactions',
  category: 'Financial',
  icon: 'FileText',
  schema: {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Receipt Extraction Schema",
    "description": "Schema for extracting structured data from receipts",
    "type": "object",
    "properties": {
      "receipt_number": {
        "type": "string",
        "description": "Unique receipt or transaction identifier"
      },
      "transaction_date": {
        "type": "string",
        "format": "date-time",
        "description": "Date and time of transaction"
      },
      "merchant": {
        "type": "object",
        "description": "Merchant/store information",
        "properties": {
          "name": {
            "type": "string",
            "description": "Merchant name"
          },
          "address": {
            "type": "string",
            "description": "Store location address"
          },
          "phone": {
            "type": "string",
            "description": "Store phone number"
          },
          "store_number": {
            "type": "string",
            "description": "Store or branch number"
          },
          "tax_id": {
            "type": "string",
            "description": "Merchant tax ID or registration number"
          }
        },
        "required": ["name"]
      },
      "items": {
        "type": "array",
        "description": "List of purchased items",
        "items": {
          "type": "object",
          "properties": {
            "description": {
              "type": "string",
              "description": "Item description or name"
            },
            "quantity": {
              "type": "number",
              "description": "Quantity purchased",
              "minimum": 0
            },
            "unit_price": {
              "type": "number",
              "description": "Price per unit",
              "minimum": 0
            },
            "total_price": {
              "type": "number",
              "description": "Total price for this item",
              "minimum": 0
            },
            "sku": {
              "type": "string",
              "description": "SKU or product code"
            },
            "discount": {
              "type": "number",
              "description": "Discount applied to item",
              "minimum": 0,
              "default": 0
            }
          },
          "required": ["description", "total_price"]
        },
        "minItems": 1
      },
      "subtotal": {
        "type": "number",
        "description": "Subtotal before taxes and discounts",
        "minimum": 0
      },
      "tax": {
        "type": "number",
        "description": "Total tax amount",
        "minimum": 0
      },
      "discount": {
        "type": "number",
        "description": "Total discount amount",
        "minimum": 0,
        "default": 0
      },
      "total": {
        "type": "number",
        "description": "Final total amount paid",
        "minimum": 0
      },
      "currency": {
        "type": "string",
        "description": "Currency code (USD, EUR, GBP, etc.)",
        "pattern": "^[A-Z]{3}$"
      },
      "payment_method": {
        "type": "string",
        "description": "Payment method used",
        "enum": ["cash", "credit_card", "debit_card", "mobile_payment", "check", "other"]
      },
      "card_last_four": {
        "type": "string",
        "description": "Last 4 digits of card (if applicable)",
        "pattern": "^[0-9]{4}$"
      },
      "cashier": {
        "type": "string",
        "description": "Cashier name or ID"
      },
      "register": {
        "type": "string",
        "description": "Register or terminal number"
      }
    },
    "required": [
      "receipt_number",
      "transaction_date",
      "merchant",
      "items",
      "total",
      "currency"
    ]
  },
};
