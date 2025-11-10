import type { Template } from '@/types/template';

export const idCardTemplate: Template = {
  id: 'id-card',
  name: 'ID Card Schema',
  description: 'Government-issued ID card extraction schema for identity verification',
  category: 'Identity',
  icon: 'User',
  schema: {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "ID Card Extraction Schema",
    "description": "Schema for extracting structured data from government-issued ID cards",
    "type": "object",
    "properties": {
      "document_type": {
        "type": "string",
        "description": "Type of ID document",
        "enum": ["national_id", "driver_license", "state_id", "resident_permit", "voter_id", "other"]
      },
      "id_number": {
        "type": "string",
        "description": "Unique ID number"
      },
      "issuing_country": {
        "type": "string",
        "description": "Country that issued the ID"
      },
      "issuing_state": {
        "type": "string",
        "description": "State/Province that issued the ID (if applicable)"
      },
      "full_name": {
        "type": "string",
        "description": "Full legal name"
      },
      "surname": {
        "type": "string",
        "description": "Surname / Family name"
      },
      "given_names": {
        "type": "string",
        "description": "Given name(s) / First name(s)"
      },
      "middle_name": {
        "type": "string",
        "description": "Middle name (if applicable)"
      },
      "date_of_birth": {
        "type": "string",
        "format": "date",
        "description": "Date of birth (YYYY-MM-DD)"
      },
      "place_of_birth": {
        "type": "string",
        "description": "Place of birth"
      },
      "sex": {
        "type": "string",
        "description": "Sex/Gender",
        "enum": ["M", "F", "X"]
      },
      "nationality": {
        "type": "string",
        "description": "Nationality"
      },
      "address": {
        "type": "object",
        "description": "Residential address",
        "properties": {
          "street": {
            "type": "string",
            "description": "Street address"
          },
          "city": {
            "type": "string",
            "description": "City"
          },
          "state": {
            "type": "string",
            "description": "State/Province"
          },
          "postal_code": {
            "type": "string",
            "description": "Postal/ZIP code"
          },
          "country": {
            "type": "string",
            "description": "Country"
          }
        }
      },
      "date_of_issue": {
        "type": "string",
        "format": "date",
        "description": "Date of issue (YYYY-MM-DD)"
      },
      "date_of_expiry": {
        "type": "string",
        "format": "date",
        "description": "Date of expiry (YYYY-MM-DD)"
      },
      "issuing_authority": {
        "type": "string",
        "description": "Authority that issued the ID"
      },
      "height": {
        "type": "string",
        "description": "Height"
      },
      "eye_color": {
        "type": "string",
        "description": "Eye color"
      },
      "blood_type": {
        "type": "string",
        "description": "Blood type (if shown)"
      },
      "document_number": {
        "type": "string",
        "description": "Document number (if different from ID number)"
      },
      "endorsements": {
        "type": "array",
        "description": "Endorsements or restrictions (for driver's licenses)",
        "items": {
          "type": "string"
        }
      },
      "class": {
        "type": "string",
        "description": "License class (for driver's licenses)"
      },
      "organ_donor": {
        "type": "boolean",
        "description": "Organ donor status (if applicable)"
      },
      "veteran": {
        "type": "boolean",
        "description": "Veteran status (if applicable)"
      }
    },
    "required": [
      "document_type",
      "id_number",
      "full_name",
      "date_of_birth",
      "date_of_issue"
    ]
  },
};
