import type { Template } from '@/types/template';

export const passportTemplate: Template = {
  id: 'passport',
  name: 'Passport Schema',
  description: 'International passport extraction schema for identity verification',
  category: 'Identity',
  icon: 'User',
  schema: {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Passport Extraction Schema",
    "description": "Schema for extracting structured data from passports",
    "type": "object",
    "properties": {
      "passport_type": {
        "type": "string",
        "description": "Type of passport (e.g., P for personal, D for diplomatic, S for service)",
        "pattern": "^[A-Z]{1,2}$"
      },
      "country_code": {
        "type": "string",
        "description": "Issuing country code (ISO 3166-1 alpha-3)",
        "pattern": "^[A-Z]{3}$"
      },
      "passport_number": {
        "type": "string",
        "description": "Passport number"
      },
      "surname": {
        "type": "string",
        "description": "Surname / Family name"
      },
      "given_names": {
        "type": "string",
        "description": "Given name(s) / First name(s)"
      },
      "nationality": {
        "type": "string",
        "description": "Nationality"
      },
      "date_of_birth": {
        "type": "string",
        "format": "date",
        "description": "Date of birth (YYYY-MM-DD)"
      },
      "place_of_birth": {
        "type": "string",
        "description": "Place of birth (city/country)"
      },
      "sex": {
        "type": "string",
        "description": "Sex/Gender",
        "enum": ["M", "F", "X"]
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
      "authority": {
        "type": "string",
        "description": "Issuing authority"
      },
      "place_of_issue": {
        "type": "string",
        "description": "Place of issue"
      },
      "mrz_line1": {
        "type": "string",
        "description": "Machine Readable Zone (MRZ) - Line 1"
      },
      "mrz_line2": {
        "type": "string",
        "description": "Machine Readable Zone (MRZ) - Line 2"
      },
      "personal_number": {
        "type": "string",
        "description": "Personal identification number (if applicable)"
      },
      "height": {
        "type": "string",
        "description": "Height of passport holder"
      },
      "eye_color": {
        "type": "string",
        "description": "Eye color"
      }
    },
    "required": [
      "passport_type",
      "country_code",
      "passport_number",
      "surname",
      "given_names",
      "nationality",
      "date_of_birth",
      "sex",
      "date_of_issue",
      "date_of_expiry"
    ]
  },
};
