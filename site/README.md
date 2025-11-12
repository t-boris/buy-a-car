# AutoFinder - Dark Theme UI

Modern dark-themed car inventory search with AI-powered filtering.

## Features

### ✨ Dark Theme
- Sleek dark gradient background
- Glass-morphism cards with backdrop blur
- Modern blue gradient accents

### 🎯 Two Views
1. **Cars View** - Searchable inventory table with advanced filters
2. **Dealers View** - Beautiful dealer cards with contact info

### 🔍 Advanced Filters
- **Make** - Filter by car manufacturer
- **Price Range** - Slider from $0 to $100k
- **Year Range** - Filter by model year
- **Max Mileage** - Up to 200k miles
- **Dealer** - Filter by specific dealerships

### 🤖 AI Search (Powered by Gemini)
Natural language search like:
- "reliable SUV under $15k"
- "low mileage Honda or Toyota"
- "newest cars with best price drop"

## Setup

### 1. Install Dependencies
\`\`\`bash
npm install
\`\`\`

### 2. Configure Gemini API (Optional - for AI Search)
1. Get your API key from: https://makersuite.google.com/app/apikey
2. Create `.env` file:
\`\`\`bash
VITE_GEMINI_API_KEY=your-api-key-here
\`\`\`

### 3. Copy Data Files
\`\`\`bash
npm run copy-data
\`\`\`

### 4. Start Dev Server
\`\`\`bash
npm run dev
\`\`\`

Visit: http://localhost:3000/buy-a-car/

## Usage

### Cars View
- Use sidebar filters to narrow down results
- Click column headers to sort
- Use AI search for natural language queries
- Click "View" to visit dealer listing

### Dealers View
- Browse dealer cards with:
  - Numbered badges (#1, #2, etc.)
  - Vehicle count
  - Phone number (clickable to call)
  - Website link
  - Snippet/description
- Click "View Inventory" to see dealer's cars
- Click 🔗 to visit dealer website

## Color Scheme

- **Background**: Dark slate gradient
- **Cards**: Semi-transparent with blur
- **Accents**: Blue to light blue gradient
- **Text**: Slate tones for readability
- **Trends**:
  - 🟢 Green = Price dropped
  - 🔴 Red = Price increased
  - 🔵 Blue = New listing

## Build for Production

\`\`\`bash
npm run build
\`\`\`

Output will be in `dist/` directory.
