#!/bin/bash
set -euo pipefail

LOG_FILE=/var/log/trendsearth-codedeploy-bootstrap.log

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

REGION="us-east-1"

log "Starting CodeDeploy agent setup for Trends.Earth API UI"

log "Updating package index"
apt-get update

log "Installing dependencies"
apt-get install -y ruby wget unzip

log "Downloading latest CodeDeploy installer"
cd /tmp
wget -O codedeploy-install https://aws-codedeploy-us-east-1.s3.us-east-1.amazonaws.com/latest/install
chmod +x codedeploy-install

log "Installing / updating CodeDeploy agent"
./codedeploy-install auto

log "Enabling CodeDeploy agent service"
systemctl enable codedeploy-agent
systemctl start codedeploy-agent

log "Ensuring application directory exists"
mkdir -p /opt/trendsearth-api-ui
chown ubuntu:ubuntu /opt/trendsearth-api-ui

log "Configuring log rotation"
cat > /etc/logrotate.d/trendsearth-api-ui <<'LOGROTATE'
/var/log/trendsearth-*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 ubuntu ubuntu
}
LOGROTATE

log "CodeDeploy agent setup finished"
systemctl status codedeploy-agent --no-pager || true
