#!/bin/bash
# Load API keys from secrets.md
#
# Usage:
#   source load_secrets.sh
#   # or
#   . load_secrets.sh

if [ ! -f "secrets.md" ]; then
    echo "❌ secrets.md not found!"
    echo ""
    echo "Create it with:"
    echo "  cp .secrets.example.md secrets.md"
    echo ""
    echo "Then edit secrets.md and add your API keys."
    return 1 2>/dev/null || exit 1
fi

# Extract and execute export commands from secrets.md
eval "$(grep '^export' secrets.md)"

# Verify keys are loaded
if [ -z "$GEMINI_API_KEY" ] || [ -z "$GOOGLE_CSE_ID" ] || [ -z "$GOOGLE_API_KEY" ]; then
    echo "⚠️  Some API keys are missing!"
    echo ""
    echo "Make sure secrets.md contains:"
    echo "  export GEMINI_API_KEY='...'"
    echo "  export GOOGLE_CSE_ID='...'"
    echo "  export GOOGLE_API_KEY='...'"
    return 1 2>/dev/null || exit 1
fi

echo "✅ API keys loaded successfully!"
echo ""
echo "Loaded keys:"
echo "  GEMINI_API_KEY: ${GEMINI_API_KEY:0:20}..."
echo "  GOOGLE_CSE_ID: ${GOOGLE_CSE_ID}"
echo "  GOOGLE_API_KEY: ${GOOGLE_API_KEY:0:20}..."
echo ""
echo "You can now run:"
echo "  python run_local.py"
