#!/bin/bash
# Run this with sudo: sudo bash ~/workspace/rentaiagent/deploy/setup-nginx.sh
set -e

echo "=== Installing nginx + certbot ==="
apt update
apt install -y nginx certbot python3-certbot-nginx

echo "=== Copying nginx config ==="
cp ~/workspace/rentaiagent/deploy/nginx-site.conf /etc/nginx/sites-available/rentaiagent
ln -sf /etc/nginx/sites-available/rentaiagent /etc/nginx/sites-enabled/rentaiagent
rm -f /etc/nginx/sites-enabled/default

echo "=== Testing nginx config ==="
nginx -t

echo "=== Starting nginx ==="
systemctl enable nginx
systemctl restart nginx

echo "=== Nginx is running! ==="
echo ""
echo "Now set up DNS records (A records for rentaiagent.io, www.rentaiagent.io, api.rentaiagent.io → 72.61.225.168)"
echo "Then run: sudo certbot --nginx -d rentaiagent.io -d www.rentaiagent.io -d api.rentaiagent.io"
echo ""
echo "Test: curl -I http://rentaiagent.io"
