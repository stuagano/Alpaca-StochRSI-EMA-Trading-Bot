# Flask Application Integration Guide

This guide shows how to integrate the new Flask application structure with your existing trading bot codebase.

## Quick Start

### 1. Install Additional Dependencies

Add to your `requirements.txt`:

```
Flask-CORS==4.0.0
Flask-SocketIO==5.3.6
```

Then install:
```bash
pip install Flask-CORS Flask-SocketIO
```

### 2. Run the New Flask App

```bash
# Replace legacy launchers with the unified backend API entrypoint
python backend/api/run.py --host localhost --port 5001 --debug
```

### 3. Test the API

```bash
# Health check
curl http://localhost:5001/health/ping

# Account info
curl http://localhost:5001/api/v1/account

# Configuration
curl http://localhost:5001/admin/config
```

## Integration Examples

### 1. Integrating with Your TradingBot Class

Create a bridge service to connect Flask with your existing `trading_bot.py`:

```python
# app/services/trading_service.py
from app.services.base_service import BaseService
from trading_bot import TradingBot  # Your existing class

class TradingService(BaseService):
    def __init__(self, service_registry):
        super().__init__(service_registry)
        self.trading_bot = None

    def start_trading(self):
        """Start the trading bot."""
        if not self.trading_bot:
            config = self.get_config()
            self.trading_bot = TradingBot(config)

        self.trading_bot.start()
        return {"status": "started", "strategy": self.trading_bot.strategy}

    def stop_trading(self):
        """Stop the trading bot."""
        if self.trading_bot:
            self.trading_bot.stop()
        return {"status": "stopped"}

    def get_trading_status(self):
        """Get current trading status."""
        if not self.trading_bot:
            return {"active": False}

        return {
            "active": self.trading_bot.is_running(),
            "strategy": self.trading_bot.strategy,
            "positions_count": len(self.trading_bot.get_positions())
        }
```

### 2. Integrating with Your Indicator Class

```python
# app/services/signal_service.py
from app.services.base_service import BaseService
from indicator import TradingIndicators  # Your existing class

class SignalService(BaseService):
    def __init__(self, service_registry):
        super().__init__(service_registry)
        self.indicators = TradingIndicators()

    def get_current_signals(self, strategy=None, symbol=None, action=None):
        """Get current trading signals."""
        config = self.get_config()
        symbols = [symbol] if symbol else config.symbols

        signals = []
        for sym in symbols:
            try:
                # Use your existing indicator calculations
                signal_data = self.indicators.calculate_signals(sym)

                if action and signal_data.get('action') != action:
                    continue

                signals.append({
                    'symbol': sym,
                    'action': signal_data.get('action', 'HOLD'),
                    'strength': signal_data.get('strength', 'Medium'),
                    'rsi': signal_data.get('rsi', 50),
                    'stoch_rsi': signal_data.get('stoch_rsi', 50),
                    'timestamp': signal_data.get('timestamp')
                })
            except Exception as e:
                self.log_error(f"Error calculating signal for {sym}", e)

        return signals
```

### 3. Real-time Updates with WebSocket

```python
# app/services/websocket_service.py
from app.extensions import socketio
from app.services.base_service import BaseService

class WebSocketService(BaseService):
    def broadcast_position_update(self, position_data):
        """Broadcast position updates to connected clients."""
        socketio.emit('position_update', position_data, room='positions')

    def broadcast_signal_update(self, signal_data):
        """Broadcast new signals to connected clients."""
        socketio.emit('signal_update', signal_data, room='signals')

    def broadcast_account_update(self, account_data):
        """Broadcast account updates."""
        socketio.emit('account_update', account_data, room='account')
```

### 4. Updating Your Existing app.py Routes

You can keep your existing `app.py` and gradually migrate routes:

```python
# In your existing app.py, add:
from app import create_app as create_new_app

# Create new Flask app instance
new_app = create_new_app()

# Register new app routes with your existing app
@app.route('/api/v2/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_to_new_api(path):
    """Proxy requests to new API structure."""
    # Forward requests to new app
    # This allows gradual migration
    pass
```

## Configuration Integration

The new Flask app uses your existing `config/unified_config.py`:

```python
# The Flask app automatically loads your configuration
config = get_config()

# Access in services
class MyService(BaseService):
    def some_method(self):
        config = self.get_config()
        symbols = config.symbols
        strategy = config.strategy
```

## Database Integration

If you add database models later, integrate with your existing database setup:

```python
# app/models/database.py
from config.unified_config import get_config

def get_database_url():
    config = get_config()
    return config.database.url
```

## Running Both Apps During Migration

During migration, you can run both apps:

```bash
# Terminal 1: Your existing app (legacy runtime)
python backend/api/run.py

# Terminal 2: New Flask app on alternate port
python backend/api/run.py --port 5002
```

Then use a reverse proxy (nginx) or load balancer to route:
- `/api/v1/*` → New Flask app (port 5002)
- Everything else → Existing app (port 5001)

## Frontend Integration

Update your frontend to use the new API endpoints:

```javascript
// Old approach
fetch('/api/account')

// New approach
fetch('/api/v1/account')

// WebSocket connection
const socket = io('http://localhost:5001');
socket.on('position_update', (data) => {
    updatePositionsUI(data);
});
```

## Testing the Integration

Create integration tests:

```python
# tests/test_integration.py
import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client

def test_account_endpoint(client):
    response = client.get('/api/v1/account')
    assert response.status_code == 200

def test_health_check(client):
    response = client.get('/health/ping')
    assert response.status_code == 200
```

## Performance Considerations

1. **Service Caching**: Cache expensive operations in services
2. **Database Pooling**: Use connection pooling for database access
3. **WebSocket Optimization**: Batch updates for real-time data
4. **Error Handling**: Graceful degradation when services are unavailable

## Migration Checklist

- [ ] Install new dependencies
- [ ] Test new Flask app startup
- [ ] Verify configuration loading
- [ ] Test API endpoints
- [ ] Integrate with existing TradingBot
- [ ] Set up WebSocket connections
- [ ] Update frontend API calls
- [ ] Add error handling
- [ ] Performance testing
- [ ] Deploy to production

This integration approach allows you to adopt the new Flask structure incrementally while maintaining your existing functionality.
