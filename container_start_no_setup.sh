#!/bin/sh

# Start nginx
nginx

# Navigate to the app and start gunicorn
cd memberportal

# We should migrate on startup in case there's been any db changes
python3 manage.py migrate

exec gunicorn membermatters.wsgi:application --bind unix:/tmp/gunicorn.sock --access-logfile '/usr/src/logs/access.log' --error-logfile '/usr/src/logs/error.log' --workers 6
