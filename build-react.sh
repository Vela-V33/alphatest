#!/bin/bash

echo "🚀 Building AlphaTest React Components..."

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Create dist directory
mkdir -p static/dist

# Build React components
echo "🔨 Building React bundle..."
npm run build

if [ $? -eq 0 ]; then
    echo "✅ Build complete! Bundle available at static/dist/collaboration-bundle.js"
    ls -lh static/dist/collaboration-bundle.js
else
    echo "❌ Build failed!"
    exit 1
fi
