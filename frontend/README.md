# PPR Bitcoin - Frontend

React + TypeScript + Vite frontend for the PPR Bitcoin portfolio calculator.

## Features

- **PPR Selection**: Select one or more PPR funds for your portfolio
- **Bitcoin Allocation**: Adjust Bitcoin allocation percentage with visual slider
- **Investment Parameters**: Configure initial investment, monthly contributions, and rebalancing frequency
- **Period Selection**: Choose date ranges with quick preset buttons
- **Portfolio Visualization**: Interactive charts showing portfolio evolution over time
- **Comprehensive Metrics**: CAGR, Sharpe Ratio, Sortino Ratio, Volatility, Max Drawdown, and more

## Tech Stack

- React 18
- TypeScript
- Vite (build tool)
- Tailwind CSS (styling)
- Recharts (charts)
- Axios (API client)
- React Router (navigation)
- date-fns (date utilities)

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running on http://localhost:8000

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

The app will be available at http://localhost:3000

### Build for Production

```bash
npm run build
```

The build output will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Environment Variables

Create a `.env` file in the frontend directory:

```
VITE_API_URL=http://localhost:8000
```

For production, update this to your production backend URL.

## Project Structure

```
frontend/
├── src/
│   ├── api/          # API client and endpoints
│   ├── components/   # React components
│   ├── types/        # TypeScript type definitions
│   ├── App.tsx       # Main application component
│   ├── main.tsx      # Application entry point
│   └── index.css     # Global styles (Tailwind)
├── public/           # Static assets
└── index.html        # HTML entry point
```

## Components

- **DisclaimerBanner**: Legal warning banner
- **PPRSelector**: Multi-select dropdown for PPR funds
- **BitcoinSlider**: Slider to adjust Bitcoin allocation
- **PeriodSelector**: Date range selector with quick presets
- **InvestmentInputs**: Configure investment amounts and rebalancing
- **PortfolioChart**: Line chart showing portfolio evolution
- **MetricsPanel**: Display comprehensive portfolio metrics

## API Integration

The frontend communicates with the backend via REST API:

- `GET /api/v1/pprs/` - Fetch available PPR funds
- `POST /api/v1/portfolio/calculate` - Calculate portfolio performance
- `POST /api/v1/portfolio/compare` - Compare multiple portfolios

## Troubleshooting

### Backend connection errors

Make sure the backend is running:
```bash
cd ..
python -m uvicorn app.main:app --reload
```

### Port conflicts

If port 3000 is in use, Vite will automatically try the next available port.

## License

Educational use only. Not financial advice.
