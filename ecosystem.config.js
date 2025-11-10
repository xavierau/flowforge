const path = require('path');

const projectRoot = '/home/forge/flowforge_app.activedevelopment.cloud';
const venvPython = path.join(projectRoot, '.venv', 'bin', 'python');

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
