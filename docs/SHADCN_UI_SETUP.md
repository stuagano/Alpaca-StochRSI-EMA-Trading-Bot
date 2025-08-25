# Shadcn/UI Setup Guide for Alpaca Trading Bot

## ✅ Setup Complete

Shadcn/UI has been successfully integrated into your trading bot project. The modern React frontend with shadcn components is ready for development.

## 📁 Project Structure

```
frontend-shadcn/
├── app/
│   ├── globals.css         # Global styles with Tailwind
│   ├── layout.tsx          # Root layout with theme provider
│   └── page.tsx            # Trading dashboard demo
├── components/
│   ├── ui/                 # Shadcn UI components
│   │   ├── badge.tsx
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   └── tabs.tsx
│   └── theme-provider.tsx  # Dark/light theme support
├── lib/
│   └── utils.ts            # Utility functions (cn)
├── components.json         # Shadcn configuration
├── tailwind.config.ts      # Tailwind configuration
├── tsconfig.json          # TypeScript configuration
├── package.json           # Dependencies
├── next.config.js         # Next.js configuration
└── postcss.config.js      # PostCSS configuration
```

## 🚀 Getting Started

### 1. Install Dependencies
```bash
cd frontend-shadcn
npm install
```

### 2. Run Development Server
```bash
npm run dev
```

The app will be available at http://localhost:3001

### 3. Build for Production
```bash
npm run build
npm start
```

## 🎨 Available Shadcn Components

### Currently Installed:
- **Card** - Container component for content sections
- **Button** - Interactive button with variants
- **Badge** - Status indicators and labels
- **Tabs** - Tabbed navigation interface

### How to Add More Components:

#### Using Shadcn CLI (Recommended):
```bash
cd frontend-shadcn
npx shadcn@latest add [component-name]

# Examples:
npx shadcn@latest add dialog
npx shadcn@latest add dropdown-menu
npx shadcn@latest add chart
npx shadcn@latest add table
npx shadcn@latest add form
npx shadcn@latest add input
npx shadcn@latest add select
npx shadcn@latest add toast
```

#### Using Shadcn MCP Server:
If you have the MCP server running with a GitHub token:
```bash
shadcn-ui-mcp-server --github-api-key ghp_your_token_here
```

Then in Claude Code, you can use MCP tools to add components automatically.

## 📊 Trading Dashboard Features

The example dashboard (`app/page.tsx`) includes:

### 1. **Header Section**
- Logo and branding
- Connect to Alpaca button
- Settings access

### 2. **Statistics Cards**
- Total Balance with percentage change
- Today's P&L (Profit & Loss)
- Active Positions count
- Win Rate percentage

### 3. **Tabbed Interface**
- **Positions Tab**: Monitor open trading positions
- **Signals Tab**: Real-time StochRSI and EMA signals
- **Orders Tab**: Order history and pending orders
- **Analytics Tab**: Performance charts and metrics

### 4. **Position Display**
- LONG/SHORT badges
- Symbol and entry details
- Real-time P&L tracking
- Color-coded gains/losses

### 5. **Signal Display**
- Buy/Sell indicators
- Signal strength percentage
- One-click execution buttons
- Indicator source (StochRSI/EMA)

## 🔧 Customization Guide

### Theme Configuration
Edit `app/globals.css` to customize colors:
```css
:root {
  --primary: 240 5.9% 10%;           /* Primary color */
  --secondary: 240 4.8% 95.9%;       /* Secondary color */
  --destructive: 0 84.2% 60.2%;      /* Error/danger color */
  --chart-1: 12 76% 61%;             /* Chart color 1 */
  /* ... more color variables */
}
```

### Adding New Pages
Create new files in `app/` directory:
```tsx
// app/settings/page.tsx
export default function SettingsPage() {
  return (
    <div>
      {/* Your settings content */}
    </div>
  )
}
```

### Creating Custom Components
```tsx
// components/trading-chart.tsx
"use client"

import { Card } from "@/components/ui/card"

export function TradingChart({ symbol }: { symbol: string }) {
  return (
    <Card>
      {/* Chart implementation */}
    </Card>
  )
}
```

## 🔗 Integration with Backend

### Connect to API Gateway
```typescript
// lib/api.ts
const API_BASE_URL = 'http://localhost:9000'

export async function fetchPositions() {
  const response = await fetch(`${API_BASE_URL}/positions`)
  return response.json()
}

export async function executeOrder(order: OrderData) {
  const response = await fetch(`${API_BASE_URL}/orders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(order)
  })
  return response.json()
}
```

### WebSocket for Real-time Data
```typescript
// lib/websocket.ts
export function connectToMarketData() {
  const ws = new WebSocket('ws://localhost:9005/stream')
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    // Handle real-time market data
  }
  
  return ws
}
```

## 📦 Recommended Additional Components

For a complete trading interface, consider adding:

### Charts & Data Visualization
```bash
npx shadcn@latest add chart        # Recharts integration
npm install lightweight-charts      # TradingView charts
```

### Forms & Input
```bash
npx shadcn@latest add form
npx shadcn@latest add input
npx shadcn@latest add select
npx shadcn@latest add slider        # For position sizing
```

### Feedback & Notifications
```bash
npx shadcn@latest add toast         # Notifications
npx shadcn@latest add alert         # Alert messages
npx shadcn@latest add progress      # Loading states
```

### Data Display
```bash
npx shadcn@latest add table         # Order history
npx shadcn@latest add scroll-area   # Scrollable areas
npx shadcn@latest add skeleton      # Loading skeletons
```

## 🎯 Next Steps

1. **Install Dependencies**:
   ```bash
   cd frontend-shadcn && npm install
   ```

2. **Start Development**:
   ```bash
   npm run dev
   ```

3. **Add More Components**:
   ```bash
   npx shadcn@latest add dialog
   npx shadcn@latest add dropdown-menu
   ```

4. **Connect to Backend**:
   - Integrate with API Gateway (port 9000)
   - Set up WebSocket connections
   - Add authentication

5. **Enhance Trading Features**:
   - Add real-time charts
   - Implement order forms
   - Create position management UI
   - Add risk management controls

## 🛠️ Development Tips

### Component Library
All shadcn components are fully customizable. They're copied into your project, not installed as dependencies, giving you complete control.

### TypeScript Support
Full TypeScript support with type safety for all components and props.

### Dark Mode
Dark mode is already configured with next-themes. Toggle between light/dark themes automatically.

### Responsive Design
All components are mobile-responsive by default using Tailwind's responsive utilities.

### Performance
- Next.js App Router for optimal performance
- React Server Components where possible
- Automatic code splitting

## 📚 Resources

- [Shadcn/UI Documentation](https://ui.shadcn.com)
- [Component Examples](https://ui.shadcn.com/examples)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [Next.js Documentation](https://nextjs.org/docs)
- [Radix UI Primitives](https://www.radix-ui.com)

## 🆘 Troubleshooting

### Module not found errors
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Styling issues
```bash
# Ensure Tailwind is processing your files
npm run dev
```

### TypeScript errors
```bash
# Check TypeScript configuration
npx tsc --noEmit
```

---

**Status**: ✅ Shadcn/UI Setup Complete
**Frontend Location**: `/frontend-shadcn`
**Development URL**: http://localhost:3001
**Last Updated**: 2025-08-25