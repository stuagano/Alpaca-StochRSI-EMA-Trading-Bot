# Testing Checklist - What's Preventing Consistent Operation

## 🚨 CRITICAL ISSUES IDENTIFIED

### 1. **Proxy Loop (FIXED)**
- **Problem**: `next.config.js` was proxying `/api/*` to `localhost:9100` (same port as frontend)
- **Result**: Infinite proxy loop causing thousands of "socket hang up" errors
- **Status**: ✅ **FIXED** - Removed proxy configuration

### 2. **Missing Backend Server**
- **Problem**: Frontend expects backend API on port 8000 or different port
- **Current**: No backend server running to handle API requests
- **Required Endpoints**:
  - `/api/account` - Account information
  - `/api/positions` - Trading positions
  - `/api/orders` - Order management  
  - `/api/signals` - Trading signals
  - `/api/crypto/signals` - Crypto-specific signals
  - `/api/strategies` - Strategy management
  - `/api/crypto/market` - Crypto market data
  - `/api/performance` - Performance metrics
  - `/api/risk` - Risk management data
  - WebSocket endpoint for real-time data

### 3. **Chart Disposal Error (Component Lifecycle)**
- **Problem**: TradingView chart throws "Object is disposed" when navigating between pages
- **Location**: `/components/trading/TradingChart.tsx`
- **Fix Needed**: Proper cleanup in useEffect return function
```typescript
useEffect(() => {
  return () => {
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }
  };
}, []);
```

### 4. **WebSocket Authentication**
- **Problem**: WebSocket connections fail with 403 errors
- **Fix Needed**: Implement proper authentication headers

## 📋 COMPREHENSIVE TESTING CHECKLIST

### Backend Infrastructure
- [ ] Backend API server running on port 8000
- [ ] All API endpoints returning valid JSON responses
- [ ] Alpaca API integration working (paper trading)
- [ ] WebSocket server for real-time data streams
- [ ] Database connections (if using database)
- [ ] Error handling for all endpoints

### Frontend Components
- [ ] Chart renders without disposal errors
- [ ] Navigation between pages works smoothly
- [ ] Real-time data updates properly
- [ ] Bot activation/deactivation functions
- [ ] Position display shows correct data
- [ ] Order execution works (paper trading only)

### Data Flow Testing
- [ ] Stock mode only shows stock positions/data
- [ ] Crypto mode only shows crypto positions/data  
- [ ] No cross-contamination between market types
- [ ] Real-time price updates working
- [ ] Performance metrics calculating correctly

### Error Handling
- [ ] Graceful handling of offline backend
- [ ] Proper error messages to user
- [ ] No infinite retry loops
- [ ] Circuit breaker patterns implemented
- [ ] Rate limiting respected

### Security & Authentication  
- [ ] Alpaca API keys secured (never in frontend)
- [ ] WebSocket authentication working
- [ ] CORS headers properly configured
- [ ] No sensitive data in browser console

## 🛠️ IMMEDIATE FIXES NEEDED

1. **Start Backend Server**
   ```bash
   # You need to create/start a backend server on port 8000
   # That handles all the /api/* endpoints
   ```

2. **Fix Chart Component Cleanup**
   ```typescript
   // In TradingChart.tsx useEffect cleanup
   return () => {
     if (chart) {
       chart.remove();
     }
   };
   ```

3. **Update API Client Base URL**
   ```typescript
   // In lib/api/client.ts
   const baseURL = 'http://localhost:8000' // Not 9100
   ```

4. **Implement Circuit Breaker Pattern**
   ```typescript
   // Add retry limits and backoff to prevent infinite API calls
   ```

## 🎯 TESTING FLOW

### Phase 1: Backend Verification
1. Start backend server
2. Test all API endpoints with curl/Postman
3. Verify WebSocket connections
4. Check Alpaca API integration

### Phase 2: Frontend Testing  
1. Start frontend (should have no console errors)
2. Navigate between pages (no chart disposal errors)
3. Test bot activation/deactivation
4. Verify data isolation between markets

### Phase 3: Integration Testing
1. Real-time data flow from backend to frontend
2. Order placement (paper trading)
3. Performance metrics calculation
4. Error scenario handling

## 🔧 ARCHITECTURE CHANGES NEEDED

1. **Backend**: Create Express.js/FastAPI server on port 8000
2. **Frontend**: Update all API calls to use port 8000
3. **WebSocket**: Implement authenticated WebSocket server
4. **Database**: Optional - for storing trade history/performance
5. **Environment**: Separate development/production configurations

## ⚡ QUICK START RECOMMENDATIONS

1. **Create Simple Backend First**:
   - Express.js server with mock data
   - All required endpoints returning sample JSON
   - WebSocket server for price feeds

2. **Fix Frontend Chart Component**:
   - Add proper cleanup in useEffect
   - Handle component unmounting gracefully

3. **Test with Mock Data**:
   - Verify UI works with consistent mock responses
   - Then integrate with real Alpaca API

This checklist identifies exactly what's preventing consistent operation. The primary issue was the proxy loop (now fixed), but you still need a proper backend server to handle API requests.