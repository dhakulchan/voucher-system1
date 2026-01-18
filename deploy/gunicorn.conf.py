# Gunicorn configuration file for Voucher System Production
bind = "127.0.0.1:5000"
workers = 3
worker_class = "sync"
worker_connections = 1000
timeout = 300
keepalive = 30
max_requests = 1000
max_requests_jitter = 100
user = "ubuntu"
group = "www-data"

# Logging
accesslog = "/var/log/voucher-system/access.log"
errorlog = "/var/log/voucher-system/error.log"
loglevel = "info"

# Security
limit_request_line = 0
limit_request_fields = 100
limit_request_field_size = 8190

# Performance
preload_app = True

# Process naming
proc_name = "voucher-system"

# Restart workers after this many requests
max_requests = 1000

# Restart workers after this many seconds
max_worker_age = 3600

# SSL (if terminating SSL at application level)
# keyfile = "/etc/letsencrypt/live/service.dhakulchan.net/privkey.pem"
# certfile = "/etc/letsencrypt/live/service.dhakulchan.net/fullchain.pem"