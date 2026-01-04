/**
 * CodeExamplesModal Component
 *
 * Displays code examples for uploading and parsing documents using the simplified API.
 * Shows complete workflow: upload+extract in one call → poll for completion.
 * Uses actual job data (schema, prompt, model config) when available.
 */

import { useState, useEffect } from 'react';
import { Copy, Check, Code, Loader2 } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { getJobResult } from '@/lib/api';

interface CodeExamplesModalProps {
  /**
   * Job ID to fetch actual parameters from
   */
  jobId: string;

  /**
   * Document ID for the job
   */
  documentId?: string;

  /**
   * Optional trigger button text
   */
  triggerText?: string;
}

interface JobConfig {
  schema: Record<string, any>;
  schemaDefinitionId?: string;  // If present, use this instead of schema JSON
  prompt?: string;
  model: string;
  provider: string;
  callbackUrl?: string;
  enableThinking?: boolean;
  thinkingBudget?: number;
}

/**
 * Generate code examples using actual job configuration
 */
function generateCodeExamples(config: JobConfig) {
  const schemaJson = JSON.stringify(config.schema, null, 2);
  const promptText = config.prompt || 'Extract data accurately';
  const callbackUrl = config.callbackUrl || 'https://yourapp.com/webhook/extraction-complete';

  // Determine whether to use schema_definition_id or extraction_schema
  const useSchemaId = !!config.schemaDefinitionId;

  // Get API base URL from environment or use default
  const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:9001';

  return {
    python: `import requests
import time
import json

# Configuration
API_BASE_URL = "${apiBaseUrl}/api/v1"  # Update this to your API server URL
API_KEY = "your_api_key_here"  # Replace with your actual API key

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

# Step 1: Upload and extract in one call
def extract_from_file(file_path: str) -> str:
    """Upload file and start extraction, returns job ID immediately."""
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {${useSchemaId ? `
            'schema_definition_id': '${config.schemaDefinitionId}',` : `
            'extraction_schema': json.dumps(${schemaJson.split('\n').map((line, i) => i === 0 ? line : '            ' + line).join('\n')}),`}
            'model_provider': '${config.provider}',
            'model_name': '${config.model}',
            'custom_prompt': '${promptText}',
            'split_mode': 'batch',  # Options: per_page, batch, auto
            'extraction_mode': 'vllm',  # Options: vllm, markdown
            'callback_url': '${callbackUrl}',
            'enable_thinking': ${config.enableThinking || false},
            'thinking_budget': ${config.thinkingBudget || 3000}
        }

        response = requests.post(
            f"{API_BASE_URL}/jobs/extract",
            headers=headers,
            files=files,
            data=data
        )
        response.raise_for_status()
        return response.json()['extraction_job_id']

# Step 2: Wait for job completion
def wait_for_job_completion(job_id: str, max_wait: int = 120) -> dict:
    """Poll job status until completion."""
    start_time = time.time()
    while time.time() - start_time < max_wait:
        response = requests.get(
            f"{API_BASE_URL}/jobs/{job_id}/status",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()

        if data['status'] == 'completed':
            return data
        elif data['status'] == 'failed':
            raise Exception(f"Job failed: {data.get('error')}")

        time.sleep(3)

    raise TimeoutError("Job processing timeout")

# Complete workflow example
if __name__ == "__main__":
    # Step 1: Upload and start extraction (returns immediately)
    job_id = extract_from_file("your_document.pdf")
    print(f"Started extraction job: {job_id}")

    # Step 2: Wait for completion
    result = wait_for_job_completion(job_id)
    print(f"Extraction completed: {json.dumps(result, indent=2)}")`,

    typescript: `import axios, { AxiosInstance } from 'axios';

// Configuration
const API_BASE_URL = '${apiBaseUrl}/api/v1';  // Update this to your API server URL
const API_KEY = 'your_api_key_here'; // Replace with your actual API key

// Create axios instance with auth
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Authorization': \`Bearer \${API_KEY}\`
  }
});

// Types
interface ExtractResponse {
  extraction_job_id: string;
  document_id: string;
  status: string;
  message: string;
}

interface JobStatusResponse {
  job_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  error?: string;
}

// Step 1: Upload and extract in one call
async function extractFromFile(file: File): Promise<string> {
  const formData = new FormData();
  formData.append('file', file);${useSchemaId ? `
  formData.append('schema_definition_id', '${config.schemaDefinitionId}');` : `
  formData.append('extraction_schema', JSON.stringify(${schemaJson.split('\n').map((line, i) => i === 0 ? line : '    ' + line).join('\n')}));`}
  formData.append('model_provider', '${config.provider}');
  formData.append('model_name', '${config.model}');
  formData.append('custom_prompt', '${promptText}');
  formData.append('split_mode', 'batch');  // Options: per_page, batch, auto
  formData.append('extraction_mode', 'vllm');  // Options: vllm, markdown
  formData.append('callback_url', '${callbackUrl}');
  formData.append('enable_thinking', '${config.enableThinking || false}');
  formData.append('thinking_budget', '${config.thinkingBudget || 3000}');

  const response = await api.post<ExtractResponse>(
    '/jobs/extract',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }
  );

  return response.data.extraction_job_id;
}

// Step 2: Wait for job completion
async function waitForJobCompletion(
  jobId: string,
  maxWaitSeconds: number = 120
): Promise<JobStatusResponse> {
  const startTime = Date.now();

  while (Date.now() - startTime < maxWaitSeconds * 1000) {
    const response = await api.get<JobStatusResponse>(\`/jobs/\${jobId}/status\`);
    const data = response.data;

    if (data.status === 'completed') {
      return data;
    } else if (data.status === 'failed') {
      throw new Error(\`Job failed: \${data.error}\`);
    }

    await new Promise(resolve => setTimeout(resolve, 3000));
  }

  throw new Error('Job processing timeout');
}

// Complete workflow example
async function extractData(file: File): Promise<any> {
  try {
    // Step 1: Upload and start extraction
    const jobId = await extractFromFile(file);
    console.log(\`Started extraction job: \${jobId}\`);

    // Step 2: Wait for completion
    const result = await waitForJobCompletion(jobId);
    console.log('Extraction completed:', result);

    return result;
  } catch (error) {
    console.error('Extraction failed:', error);
    throw error;
  }
}`,

    javascript: `// Using fetch API (browser-compatible)
const API_BASE_URL = '${apiBaseUrl}/api/v1';  // Update this to your API server URL
const API_KEY = 'your_api_key_here'; // Replace with your actual API key

const headers = {
  'Authorization': \`Bearer \${API_KEY}\`
};

// Step 1: Upload and extract in one call
async function extractFromFile(file) {
  const formData = new FormData();
  formData.append('file', file);${useSchemaId ? `
  formData.append('schema_definition_id', '${config.schemaDefinitionId}');` : `
  formData.append('extraction_schema', JSON.stringify(${schemaJson.split('\n').map((line, i) => i === 0 ? line : '    ' + line).join('\n')}));`}
  formData.append('model_provider', '${config.provider}');
  formData.append('model_name', '${config.model}');
  formData.append('custom_prompt', '${promptText}');
  formData.append('split_mode', 'batch');  // Options: per_page, batch, auto
  formData.append('extraction_mode', 'vllm');  // Options: vllm, markdown
  formData.append('callback_url', '${callbackUrl}');
  formData.append('enable_thinking', '${config.enableThinking || false}');
  formData.append('thinking_budget', '${config.thinkingBudget || 3000}');

  const response = await fetch(\`\${API_BASE_URL}/jobs/extract\`, {
    method: 'POST',
    headers: headers,
    body: formData
  });

  if (!response.ok) {
    throw new Error(\`Upload failed: \${response.statusText}\`);
  }

  const data = await response.json();
  return data.extraction_job_id;
}

// Step 2: Wait for job completion
async function waitForJobCompletion(jobId, maxWaitSeconds = 120) {
  const startTime = Date.now();

  while (Date.now() - startTime < maxWaitSeconds * 1000) {
    const response = await fetch(
      \`\${API_BASE_URL}/jobs/\${jobId}/status\`,
      { headers }
    );

    if (!response.ok) {
      throw new Error(\`Job status check failed: \${response.statusText}\`);
    }

    const data = await response.json();

    if (data.status === 'completed') {
      return data;
    } else if (data.status === 'failed') {
      throw new Error(\`Job failed: \${data.error}\`);
    }

    await new Promise(resolve => setTimeout(resolve, 3000));
  }

  throw new Error('Job processing timeout');
}

// Complete workflow example
async function extractData(file) {
  try {
    // Step 1: Upload and start extraction
    const jobId = await extractFromFile(file);
    console.log(\`Started extraction job: \${jobId}\`);

    // Step 2: Wait for completion
    const result = await waitForJobCompletion(jobId);
    console.log('Extraction completed:', result);

    return result;
  } catch (error) {
    console.error('Extraction failed:', error);
    throw error;
  }
}`,

    curl: `#!/bin/bash

# Configuration
API_BASE_URL="${apiBaseUrl}/api/v1"  # Update this to your API server URL
API_KEY="your_api_key_here"  # Replace with your actual API key

# Step 1: Upload and extract in one call
echo "Starting extraction..."
EXTRACT_RESPONSE=$(curl -s -X POST \\
  "$API_BASE_URL/jobs/extract" \\
  -H "Authorization: Bearer $API_KEY" \\
  -F "file=@your_document.pdf" \\${useSchemaId ? `
  -F "schema_definition_id=${config.schemaDefinitionId}" \\` : `
  -F 'extraction_schema=${schemaJson.split('\n').map((line, i) => i === 0 ? JSON.stringify(line) : JSON.stringify('  ' + line)).join('\n  -F "extraction_schema=')}' \\`}
  -F "model_provider=${config.provider}" \\
  -F "model_name=${config.model}" \\
  -F "custom_prompt=${promptText}" \\
  -F "split_mode=batch" \\
  -F "extraction_mode=vllm" \\
  -F "callback_url=${callbackUrl}" \\
  -F "enable_thinking=${config.enableThinking || false}" \\
  -F "thinking_budget=${config.thinkingBudget || 3000}")

JOB_ID=$(echo $EXTRACT_RESPONSE | jq -r '.extraction_job_id')
echo "Extraction job started: $JOB_ID"

# Step 2: Wait for job completion
echo "Waiting for extraction to complete..."
MAX_ATTEMPTS=40
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  JOB_STATUS_RESPONSE=$(curl -s -X GET \\
    "$API_BASE_URL/jobs/$JOB_ID/status" \\
    -H "Authorization: Bearer $API_KEY")

  JOB_STATUS=$(echo $JOB_STATUS_RESPONSE | jq -r '.status')

  if [ "$JOB_STATUS" = "completed" ]; then
    echo "Extraction completed!"
    echo $JOB_STATUS_RESPONSE | jq '.'
    break
  elif [ "$JOB_STATUS" = "failed" ]; then
    ERROR=$(echo $JOB_STATUS_RESPONSE | jq -r '.error')
    echo "Extraction failed: $ERROR"
    exit 1
  fi

  ATTEMPT=$((ATTEMPT + 1))
  sleep 3
done`,
  };
}

/**
 * CodeExamplesModal Component
 */
export function CodeExamplesModal({
  jobId,
  triggerText = 'Show Code Examples'
}: CodeExamplesModalProps) {
  const [copiedLanguage, setCopiedLanguage] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [jobConfig, setJobConfig] = useState<JobConfig | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch job configuration when modal opens
  useEffect(() => {
    if (!isOpen || jobConfig) return;

    async function fetchJobConfig() {
      setIsLoading(true);
      setError(null);

      try {
        const result = await getJobResult(jobId);

        // Extract configuration from job result
        setJobConfig({
          schema: result.extraction_schema,
          schemaDefinitionId: result.schema_definition_id || undefined,  // Include if saved schema was used
          prompt: result.custom_prompt || 'Extract data accurately',
          model: result.model_name,
          provider: result.model_provider,
          callbackUrl: result.callback_url,
          enableThinking: result.enable_thinking || false,
          thinkingBudget: result.thinking_budget || 3000,
        });
      } catch (err) {
        console.error('Failed to fetch job config:', err);
        // Use fallback configuration
        setJobConfig({
          schema: {
            type: 'object',
            properties: {
              field1: { type: 'string' },
              field2: { type: 'number' }
            }
          },
          prompt: 'Extract data accurately',
          model: 'gemini-2.5-flash',
          provider: 'google',
        });
      } finally {
        setIsLoading(false);
      }
    }

    fetchJobConfig();
  }, [isOpen, jobId, jobConfig]);

  const copyToClipboard = async (code: string, language: string) => {
    await navigator.clipboard.writeText(code);
    setCopiedLanguage(language);
    setTimeout(() => setCopiedLanguage(null), 2000);
  };

  const codeExamples = jobConfig ? generateCodeExamples(jobConfig) : null;

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline">
          <Code className="mr-2 h-4 w-4" />
          {triggerText}
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-5xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>API Code Examples</DialogTitle>
          <DialogDescription>
            Simplified workflow: upload and extract in one call, then poll for completion.
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <span className="ml-2">Loading your configuration...</span>
          </div>
        ) : error ? (
          <div className="p-4 bg-destructive/10 border border-destructive rounded-lg">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        ) : codeExamples ? (
          <div className="flex-1 overflow-hidden flex flex-col">
            <Tabs defaultValue="python" className="flex-1 flex flex-col">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="python">Python</TabsTrigger>
                <TabsTrigger value="typescript">TypeScript</TabsTrigger>
                <TabsTrigger value="javascript">JavaScript</TabsTrigger>
                <TabsTrigger value="curl">cURL</TabsTrigger>
              </TabsList>

              <div className="flex-1 overflow-hidden mt-4">
                {Object.entries(codeExamples).map(([language, code]) => (
                  <TabsContent
                    key={language}
                    value={language}
                    className="h-full overflow-y-auto data-[state=active]:flex data-[state=inactive]:hidden flex-col"
                  >
                    <div className="relative flex-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="absolute right-2 top-2 z-10"
                        onClick={() => copyToClipboard(code, language)}
                      >
                        {copiedLanguage === language ? (
                          <>
                            <Check className="h-4 w-4 mr-2" />
                            Copied!
                          </>
                        ) : (
                          <>
                            <Copy className="h-4 w-4 mr-2" />
                            Copy
                          </>
                        )}
                      </Button>
                      <SyntaxHighlighter
                        language={language === 'curl' ? 'bash' : language}
                        style={vscDarkPlus}
                        customStyle={{
                          margin: 0,
                          borderRadius: '0.5rem',
                          fontSize: '0.875rem',
                          maxHeight: '60vh',
                        }}
                        showLineNumbers
                      >
                        {code}
                      </SyntaxHighlighter>
                    </div>
                  </TabsContent>
                ))}
              </div>
            </Tabs>

            <div className="mt-4 p-4 bg-muted rounded-lg">
              <h4 className="font-semibold mb-2">Simplified Workflow:</h4>
              <ol className="list-decimal list-inside space-y-1 text-sm text-muted-foreground">
                <li>Upload file and start extraction via <code className="bg-background px-1 rounded">/jobs/extract</code> (returns job ID immediately)</li>
                <li>Poll job status via <code className="bg-background px-1 rounded">/jobs/{'{job_id}'}/status</code> until <code className="bg-background px-1 rounded">completed</code></li>
                <li>Retrieve extraction results from job response</li>
              </ol>
              <p className="mt-2 text-xs text-muted-foreground">
                Note: The API handles document processing (PDF to images) and extraction automatically in the background.
              </p>
            </div>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
