const path = require('path');
const fs = require('fs');

// Use __dirname to get the actual project root dynamically
const projectRoot = __dirname;

// Load .env file and parse it
function loadEnvFile(envPath) {
  const envVars = {};
  if (fs.existsSync(envPath)) {
    const content = fs.readFileSync(envPath, 'utf8');
    content.split('\n').forEach(line => {
      // Skip comments and empty lines
      if (line.trim() && !line.startsWith('#')) {
        const [key, ...valueParts] = line.split('=');
        if (key && valueParts.length > 0) {
          let value = valueParts.join('=').trim();

          // Handle quoted values (preserve everything inside quotes)
          if ((value.startsWith('"') && value.includes('"', 1)) ||
              (value.startsWith("'") && value.includes("'", 1))) {
            // Find the closing quote
            const quote = value[0];
            const endQuote = value.indexOf(quote, 1);
            value = value.slice(1, endQuote);
          } else {
            // Unquoted value: strip inline comments
            const commentIndex = value.indexOf('#');
            if (commentIndex > 0) {
              value = value.substring(0, commentIndex).trim();
            }
          }

          envVars[key.trim()] = value;
        }
      }
    });
  }
  return envVars;
}

// Load environment variables from .env
const dotEnvVars = loadEnvFile(path.join(projectRoot, '.env'));
const venvPython = path.join(projectRoot, '.venv', 'bin', 'python');

console.log(`Project root: ${projectRoot}`);
console.log(`Using Python: ${venvPython}`);

module.exports = {
  apps: [
    {
      name: 'ai-document-processing-api',
      script: venvPython,
      args: '-m uvicorn app.main:app --host 0.0.0.0 --port 8000',
      cwd: projectRoot,
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        ...dotEnvVars,
        NODE_ENV: 'production',
        VIRTUAL_ENV: path.join(projectRoot, '.venv'),
        PATH: `${path.join(projectRoot, '.venv', 'bin')}:${process.env.PATH}`,
      },
      error_file: './logs/uvicorn-error.log',
      out_file: './logs/uvicorn-out.log',
      log_file: './logs/uvicorn-combined.log',
      time: true,
    },
    {
      name: 'ai-document-processing-celery-worker',
      script: venvPython,
      args: '-m celery -A app.tasks.celery_app worker --loglevel=info',
      cwd: projectRoot,
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        ...dotEnvVars,
        NODE_ENV: 'production',
        VIRTUAL_ENV: path.join(projectRoot, '.venv'),
        PATH: `${path.join(projectRoot, '.venv', 'bin')}:${process.env.PATH}`,
      },
      error_file: './logs/celery-error.log',
      out_file: './logs/celery-out.log',
      log_file: './logs/celery-combined.log',
      time: true,
    },
  ],
};
