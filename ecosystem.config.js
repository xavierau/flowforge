module.exports = {
  apps: [
    {
      name: 'ai-document-processing-api',
      script: '.venv/bin/python',
      args: '-m uvicorn app.main:app --host 0.0.0.0 --port 8000',
      cwd: '/home/forge/flowforge_app.activedevelopment.cloud',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
      },
      error_file: './logs/uvicorn-error.log',
      out_file: './logs/uvicorn-out.log',
      log_file: './logs/uvicorn-combined.log',
      time: true,
    },
    {
      name: 'ai-document-processing-celery-worker',
      script: '.venv/bin/python',
      args: '-m celery -A app.tasks.celery_app worker --loglevel=info',
      cwd: '/home/forge/flowforge_app.activedevelopment.cloud',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
      },
      error_file: './logs/celery-error.log',
      out_file: './logs/celery-out.log',
      log_file: './logs/celery-combined.log',
      time: true,
    },
  ],
};
