#!/bin/bash

# ==========================================
# Myntra Bot - AWS EC2 Deployment Script
# OS: Ubuntu 22.04 / 24.04 LTS
# Requirements: EC2 Instance (t3.small or t3.medium)
# ==========================================

echo "🚀 Starting Myntra Bot Setup on AWS EC2..."

# 1. Update system and install basic tools
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git unzip python3 python3-pip python3-venv

# 2. Add 2GB Swap Memory (Crucial for AWS Free Tier 1GB RAM)
echo "💾 Allocating 2GB Swap Memory for Playwright..."
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 3. Install Node.js (for the frontend and pm2)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2

# 4. Setup Python Virtual Environment
echo "🐍 Setting up Python Virtual Environment..."
python3 -m venv venv
source venv/bin/activate

# 4. Install Backend Dependencies
echo "📦 Installing Python packages..."
pip install fastapi uvicorn websockets aiohttp playwright pydantic

# 5. Install Playwright and Chrome Dependencies
echo "🌐 Installing Chrome (Playwright)..."
playwright install --with-deps chromium

# 6. Start the Backend using PM2
echo "⚙️ Starting Backend..."
# We use pm2 to run the uvicorn server so it stays alive 24/7
pm2 start "venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000" --name myntra-backend

# 7. Setup Frontend (Static Server)
echo "🌐 Setting up Frontend..."
cd frontend
npm install
pm2 start "npm start" --name myntra-frontend
cd ..

# 8. Save PM2 state so it auto-starts on server reboot
pm2 save
pm2 startup

echo "✅ Setup Complete!"
echo "👉 Backend is running on port 8000"
echo "👉 Frontend is running on port 3000"
echo "⚠️ Make sure to open ports 8000 and 3000 in your AWS EC2 Security Group settings!"
