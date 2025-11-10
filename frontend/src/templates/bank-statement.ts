import type { Template } from '@/types/template';

export const bankStatementTemplate: Template = {
  id: 'bank-statement',
  name: 'Bank Statement Schema',
  description: 'Bank statement extraction schema with account info, transactions, and balances',
  category: 'Financial',
  icon: 'FileText',
  schema: {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Bank Statement Extraction Schema",
    "description": "Schema for extracting structured data from bank statements",
    "type": "object",
    "properties": {
      "bank_name": {
        "type": "string",
        "description": "Name of the financial institution"
      },
      "statement_period": {
        "type": "object",
        "description": "Statement period dates",
        "properties": {
          "start_date": {
            "type": "string",
            "format": "date",
            "description": "Statement start date (YYYY-MM-DD)"
          },
          "end_date": {
            "type": "string",
            "format": "date",
            "description": "Statement end date (YYYY-MM-DD)"
          }
        },
        "required": ["start_date", "end_date"]
      },
      "account_holder": {
        "type": "object",
        "description": "Account holder information",
        "properties": {
          "name": {
            "type": "string",
            "description": "Account holder's full name"
          },
          "address": {
            "type": "string",
            "description": "Account holder's address"
          }
        },
        "required": ["name"]
      },
      "account_details": {
        "type": "object",
        "description": "Account information",
        "properties": {
          "account_number": {
            "type": "string",
            "description": "Bank account number (may be partially masked)"
          },
          "account_type": {
            "type": "string",
            "description": "Type of account",
            "enum": ["checking", "savings", "credit", "investment", "other"]
          },
          "routing_number": {
            "type": "string",
            "description": "Bank routing number"
          },
          "currency": {
            "type": "string",
            "description": "Account currency code",
            "pattern": "^[A-Z]{3}$"
          }
        },
        "required": ["account_number", "account_type"]
      },
      "opening_balance": {
        "type": "number",
        "description": "Balance at the beginning of the statement period"
      },
      "closing_balance": {
        "type": "number",
        "description": "Balance at the end of the statement period"
      },
      "transactions": {
        "type": "array",
        "description": "List of transactions during the statement period",
        "items": {
          "type": "object",
          "properties": {
            "date": {
              "type": "string",
              "format": "date",
              "description": "Transaction date"
            },
            "description": {
              "type": "string",
              "description": "Transaction description"
            },
            "type": {
              "type": "string",
              "description": "Transaction type",
              "enum": ["debit", "credit", "fee", "interest", "transfer", "withdrawal", "deposit", "other"]
            },
            "amount": {
              "type": "number",
              "description": "Transaction amount (positive for credits, negative for debits)"
            },
            "balance": {
              "type": "number",
              "description": "Account balance after this transaction"
            },
            "reference": {
              "type": "string",
              "description": "Transaction reference or check number"
            },
            "category": {
              "type": "string",
              "description": "Transaction category (e.g., groceries, utilities, salary)"
            }
          },
          "required": ["date", "description", "amount"]
        }
      },
      "summary": {
        "type": "object",
        "description": "Statement summary",
        "properties": {
          "total_deposits": {
            "type": "number",
            "description": "Total amount of deposits/credits",
            "minimum": 0
          },
          "total_withdrawals": {
            "type": "number",
            "description": "Total amount of withdrawals/debits",
            "minimum": 0
          },
          "total_fees": {
            "type": "number",
            "description": "Total fees charged",
            "minimum": 0
          },
          "interest_earned": {
            "type": "number",
            "description": "Interest earned during the period",
            "minimum": 0
          },
          "transaction_count": {
            "type": "integer",
            "description": "Total number of transactions",
            "minimum": 0
          }
        }
      }
    },
    "required": [
      "bank_name",
      "statement_period",
      "account_holder",
      "account_details",
      "closing_balance",
      "transactions"
    ]
  },
};
