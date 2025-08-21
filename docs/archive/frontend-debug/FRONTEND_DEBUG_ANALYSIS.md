# Frontend Position Display Debug Analysis

## Issues Identified

### 1. Data Field Mapping Issues
**Problem**: Data manager returns `avg_entry_price` but frontend expects `avg_cost`
- **File**: `/services/unified_data_manager.py:174`
- **Returns**: `avg_entry_price` 
- **Frontend expects**: `avg_cost` or `avg_cost_per_share`

### 2. Missing WebSocket Position Updates
**Problem**: No `position_update` event emitted in real-time thread
- **File**: `/flask_app.py:508-516`
- **Issue**: Data payload includes positions but no dedicated position_update event

### 3. Chart Connection Issues
**Problem**: Chart connection status not properly managed
- **File**: `/templates/professional_trading_dashboard.html:396-398`
- **Issue**: Connection status shows "Connecting..." indefinitely

### 4. Position Container Not Updating
**Problem**: Position data not reaching frontend properly
- **Root Cause**: Field name mismatch + missing WebSocket events

## Specific Code Issues

### Professional Dashboard (Line 832)
```javascript
// BROKEN: Tries multiple field names but gets undefined
${position.avg_cost || position.avg_cost_per_share || 0}

// SHOULD BE: 
${position.avg_entry_price || 0}
```

### Enhanced Dashboard (Line 1008)
```javascript
// BROKEN: Same field mapping issue
${pos.avg_entry_price.toFixed(2)}
// This field exists but percentage calculation uses wrong field
```

### Flask Real-time Thread (Line 508)
```python
# MISSING: No position_update WebSocket event
data_payload = {
    'positions': positions,  # Data exists but no dedicated event
    # ... other data
}

# SHOULD ADD:
socketio.emit('position_update', {'positions': positions})
```

## Fix Implementation Required

1. **Fix field mapping in templates**
2. **Add position_update WebSocket events**
3. **Fix chart connection status**
4. **Add error handling for missing position data**