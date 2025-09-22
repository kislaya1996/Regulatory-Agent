#!/bin/bash

# Regulatory Tracker Quick Start Script
# This script sets up and runs the complete regulatory tracking system

set -e  # Exit on any error

echo "🚀 Regulatory Tracker Quick Start"
echo "=================================="

# Check if we're in the right directory
if [ ! -f "llamindex/scraper.py" ]; then
    echo "❌ Error: Please run this script from the regulatory-tracker root directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "📚 Installing dependencies..."
    pip install -r requirements.txt
else
    echo "⚠️  No requirements.txt found. Installing common dependencies..."
    pip install llama-index chromadb pdfplumber beautifulsoup4 requests python-dotenv boto3
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating template..."
    cat > .env << EOF
# AWS Credentials for Bedrock
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here

# Optional: Custom scrape URL (defaults to MERC tariff orders)
REGULATORY_SCRAPE_URL=https://merc.gov.in/consumer-corner/tariff-orders
EOF
    echo "📝 Please edit .env file with your AWS credentials before continuing"
    echo "   Then run this script again."
    exit 1
fi

# Check if AWS credentials are set
if grep -q "your_access_key_here" .env; then
    echo "❌ Error: Please update .env file with your actual AWS credentials"
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p downloads
mkdir -p regulatory_storage
mkdir -p cache
mkdir -p embeddings_cache

# Navigate to llamindex directory
cd llamindex

echo ""
echo "🔄 Step 1: Scraping and Indexing Documents"
echo "=========================================="
echo "This may take 10-30 minutes depending on document size..."
python run_scrape_index.py

echo ""
echo "🧪 Step 2: Testing RAG System"
echo "============================="
python regulatory_tool_calling_test.py

echo ""
echo "✅ Setup Complete!"
echo "=================="
echo "Your regulatory tracker is now ready to use."
echo ""
echo "To run again in the future:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Navigate to llamindex: cd llamindex"
echo "3. Run scraper: python run_scrape_index.py"
echo "4. Test system: python regulatory_tool_calling_test.py"
echo ""
echo "📖 See README.md for detailed documentation and customization options." 