import type { Template } from '@/types/template';

export const resumeTemplate: Template = {
  id: 'resume',
  name: 'Resume/CV Schema',
  description: 'Comprehensive resume extraction schema with work experience, education, and skills',
  category: 'HR',
  icon: 'User',
  schema: {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Resume/CV Extraction Schema",
    "description": "Schema for extracting structured data from resumes and CVs",
    "type": "object",
    "properties": {
      "personal_info": {
        "type": "object",
        "description": "Personal information of the candidate",
        "properties": {
          "full_name": { "type": "string", "description": "Candidate's full name" },
          "email": { "type": "string", "format": "email", "description": "Email address" },
          "phone": { "type": "string", "description": "Phone number" },
          "location": {
            "type": "object",
            "properties": {
              "city": { "type": "string" },
              "state": { "type": "string" },
              "country": { "type": "string" }
            }
          }
        },
        "required": ["full_name"]
      },
      "work_experience": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "company": { "type": "string" },
            "position": { "type": "string" },
            "start_date": { "type": "string" },
            "end_date": { "type": "string" },
            "responsibilities": { "type": "array", "items": { "type": "string" } }
          },
          "required": ["company", "position", "start_date"]
        },
        "minItems": 1
      },
      "education": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "institution": { "type": "string" },
            "degree": { "type": "string" },
            "graduation_date": { "type": "string" }
          },
          "required": ["institution", "degree"]
        },
        "minItems": 1
      },
      "skills": {
        "type": "object",
        "properties": {
          "technical_skills": { "type": "array", "items": { "type": "string" } },
          "soft_skills": { "type": "array", "items": { "type": "string" } }
        }
      }
    },
    "required": ["personal_info", "work_experience", "education", "skills"]
  },
};
