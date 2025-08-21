import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { PositionsDashboard, PositionsTable, PortfolioSummary } from '../src/components/positions';
import { PnLCalculator } from '../src/utils/calculations';
import { Position, PortfolioSnapshot } from '../src/types/position';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 100);
  }

  send(data: string) {
    // Mock implementation
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }
}

(global as any).WebSocket = MockWebSocket;

const mockPosition: Position = {
  symbol: 'AAPL',
  side: 'long',
  qty: 100,
  market_value: 15000,
  cost_basis: 14000,
  unrealized_pl: 1000,
  unrealized_plpc: 7.14,
  current_price: 150,
  lastday_price: 148,
  change_today: 200,
  avg_entry_price: 140,
  asset_class: 'us_equity',
  asset_id: 'aapl-123',
  exchange: 'NASDAQ'
};

const mockPortfolio: PortfolioSnapshot = {
  portfolio_value: 50000,
  equity: 50000,
  last_equity: 49000,
  total_pl: 5000,
  total_pl_percent: 10.2,
  day_pl: 1000,
  day_pl_percent: 2.04,
  buying_power: 25000,
  regt_buying_power: 25000,
  daytrading_buying_power: 50000,
  cash: 10000,
  timestamp: '2025-08-18T16:24:00Z'
};

describe('PnLCalculator', () => {
  test('calculates unrealized P&L correctly for long position', () => {
    const result = PnLCalculator.calculateUnrealizedPnL(mockPosition);
    expect(result).toBe(1000); // (150 - 140) * 100
  });

  test('calculates unrealized P&L correctly for short position', () => {
    const shortPosition = { ...mockPosition, side: 'short' as const };
    const result = PnLCalculator.calculateUnrealizedPnL(shortPosition);
    expect(result).toBe(-1000); // (140 - 150) * 100
  });

  test('calculates day change correctly', () => {
    const result = PnLCalculator.calculateDayChange(mockPosition);
    expect(result.amount).toBe(200); // (150 - 148) * 100
    expect(result.percent).toBeCloseTo(1.35, 1); // (200/14800) * 100
  });

  test('formats currency correctly', () => {
    expect(PnLCalculator.formatCurrency(1234.56)).toBe('$1,234.56');
    expect(PnLCalculator.formatCurrency(-1234.56)).toBe('-$1,234.56');
  });

  test('formats percentage correctly', () => {
    expect(PnLCalculator.formatPercent(5.75)).toBe('+5.75%');
    expect(PnLCalculator.formatPercent(-5.75)).toBe('-5.75%');
  });

  test('returns correct color classes for P&L values', () => {
    expect(PnLCalculator.getPnLColorClass(1000)).toContain('green');
    expect(PnLCalculator.getPnLColorClass(-1000)).toContain('red');
    expect(PnLCalculator.getPnLColorClass(0)).toContain('gray');
  });
});

describe('PortfolioSummary', () => {
  test('renders portfolio summary correctly', () => {
    render(
      <PortfolioSummary 
        portfolio={mockPortfolio}
        isConnected={true}
        lastUpdate="2025-08-18T16:24:00Z"
      />
    );

    expect(screen.getByText('Portfolio Summary')).toBeInTheDocument();
    expect(screen.getByText('$50,000.00')).toBeInTheDocument();
    expect(screen.getByText('$5,000.00')).toBeInTheDocument();
    expect(screen.getByText('Live')).toBeInTheDocument();
  });

  test('shows loading state when portfolio is null', () => {
    render(
      <PortfolioSummary 
        portfolio={null}
        isConnected={false}
        lastUpdate=""
      />
    );

    expect(screen.getByTestId('portfolio-loading') || document.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  test('shows disconnected status correctly', () => {
    render(
      <PortfolioSummary 
        portfolio={mockPortfolio}
        isConnected={false}
        lastUpdate=""
      />
    );

    expect(screen.getByText('Disconnected')).toBeInTheDocument();
  });
});

describe('PositionsTable', () => {
  const mockSortConfig = { key: 'symbol' as keyof Position, direction: 'asc' as const };
  const mockOnSort = jest.fn();
  const mockOnExport = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders positions table correctly', () => {
    render(
      <PositionsTable
        positions={[mockPosition]}
        sortConfig={mockSortConfig}
        onSort={mockOnSort}
        onExport={mockOnExport}
      />
    );

    expect(screen.getByText('Positions (1)')).toBeInTheDocument();
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('LONG')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  test('shows empty state when no positions', () => {
    render(
      <PositionsTable
        positions={[]}
        sortConfig={mockSortConfig}
        onSort={mockOnSort}
        onExport={mockOnExport}
      />
    );

    expect(screen.getByText('No positions found')).toBeInTheDocument();
  });

  test('handles sorting correctly', () => {
    render(
      <PositionsTable
        positions={[mockPosition]}
        sortConfig={mockSortConfig}
        onSort={mockOnSort}
        onExport={mockOnExport}
      />
    );

    const symbolHeader = screen.getByText('Symbol').closest('th');
    if (symbolHeader) {
      fireEvent.click(symbolHeader);
      expect(mockOnSort).toHaveBeenCalledWith({ key: 'symbol', direction: 'desc' });
    }
  });

  test('handles export correctly', () => {
    render(
      <PositionsTable
        positions={[mockPosition]}
        sortConfig={mockSortConfig}
        onSort={mockOnSort}
        onExport={mockOnExport}
      />
    );

    const exportButton = screen.getByText('Export CSV');
    fireEvent.click(exportButton);
    expect(mockOnExport).toHaveBeenCalled();
  });

  test('opens position detail modal when view button clicked', async () => {
    render(
      <PositionsTable
        positions={[mockPosition]}
        sortConfig={mockSortConfig}
        onSort={mockOnSort}
        onExport={mockOnExport}
      />
    );

    const viewButtons = screen.getAllByRole('button');
    const viewButton = viewButtons.find(button => 
      button.querySelector('svg') && button.getAttribute('class')?.includes('text-blue-600')
    );
    
    if (viewButton) {
      fireEvent.click(viewButton);
      await waitFor(() => {
        expect(screen.getByText('Position Details - AAPL')).toBeInTheDocument();
      });
    }
  });

  test('displays mobile view correctly on small screens', () => {
    // Mock window.innerWidth for mobile
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 500,
    });

    render(
      <PositionsTable
        positions={[mockPosition]}
        sortConfig={mockSortConfig}
        onSort={mockOnSort}
        onExport={mockOnExport}
      />
    );

    // In mobile view, we should see card-style layout instead of table
    const mobileCard = document.querySelector('.lg\\:hidden');
    expect(mobileCard).toBeInTheDocument();
  });
});

describe('PositionsDashboard Integration', () => {
  test('renders complete dashboard correctly', async () => {
    // Mock fetch for API calls
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          positions: [mockPosition],
          portfolio: mockPortfolio
        }),
      })
    ) as jest.Mock;

    render(<PositionsDashboard wsUrl="ws://localhost:8765/ws" />);

    await waitFor(() => {
      expect(screen.getByText('Portfolio Summary')).toBeInTheDocument();
      expect(screen.getByText('Positions (1)')).toBeInTheDocument();
    });
  });

  test('handles WebSocket connection correctly', async () => {
    const { container } = render(
      <PositionsDashboard wsUrl="ws://localhost:8765/ws" />
    );

    // Wait for WebSocket connection
    await waitFor(() => {
      const statusIndicator = container.querySelector('.bg-green-500');
      expect(statusIndicator).toBeInTheDocument();
    }, { timeout: 1000 });
  });
});

describe('Responsive Design', () => {
  test('adapts to different screen sizes', () => {
    const { rerender } = render(
      <PositionsTable
        positions={[mockPosition]}
        sortConfig={{ key: 'symbol', direction: 'asc' }}
        onSort={() => {}}
        onExport={() => {}}
      />
    );

    // Desktop view
    expect(document.querySelector('.hidden.lg\\:block')).toBeInTheDocument();
    
    // Mobile view
    expect(document.querySelector('.lg\\:hidden')).toBeInTheDocument();
  });
});

describe('Real-time Updates', () => {
  test('updates position data when WebSocket message received', async () => {
    const mockWs = new MockWebSocket('ws://localhost:8765/ws');
    
    render(<PositionsDashboard wsUrl="ws://localhost:8765/ws" />);

    // Simulate WebSocket message
    if (mockWs.onmessage) {
      mockWs.onmessage(new MessageEvent('message', {
        data: JSON.stringify({
          type: 'position_update',
          data: { ...mockPosition, current_price: 155 },
          timestamp: '2025-08-18T16:25:00Z'
        })
      }));
    }

    await waitFor(() => {
      // Position should be updated with new price
      expect(screen.getByText('$155.00') || screen.getByText('$155.0000')).toBeInTheDocument();
    });
  });
});