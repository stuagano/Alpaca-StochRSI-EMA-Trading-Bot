# Pine Script Time Handling - COMMITTED TO MEMORY

**Source:** https://www.tradingview.com/pine-script-docs/concepts/time/#introduction

## 📊 Core Time Concepts

### 🕐 Unix Timestamps
- **Format:** Milliseconds since January 1, 1970, 00:00:00 UTC
- **Type:** `int` values (time zone-agnostic)
- **Precision:** Accurate to the millisecond
- **Consistency:** Same value across all time zones

### 🌍 Time Zone Handling

#### **Two Primary Time Zones:**
1. **Exchange Time Zone** - Determined by `syminfo.timezone`
2. **Chart Time Zone** - User's viewing preference

#### **Time Zone Specification:**
```pinescript
// UTC offset notation
"UTC-5", "UTC+9"

// IANA database notation  
"America/New_York", "Asia/Tokyo", "Europe/London"
```

### 📈 Time Variables

#### **Bar-Based Time:**
- `time` - Bar opening timestamp (Unix milliseconds)
- `time_close` - Bar closing timestamp (Unix milliseconds)
- `timenow` - Current script execution time

#### **Calendar Variables:**
- `year`, `month`, `dayofmonth`
- `dayofweek`, `hour`, `minute`, `second`

### 🔧 Key Time Functions

#### **Timestamp Functions:**
```pinescript
// Retrieve bar timestamps
time(timeframe, session, timezone)
time_close(timeframe, session, timezone)

// Calculate Unix timestamps from calendar values
timestamp(timezone, year, month, day, hour, minute, second)

// Convert timestamps to readable strings
str.format_time(time, format, timezone)
```

#### **Calendar Functions:**
```pinescript
year(time, timezone)
month(time, timezone) 
dayofweek(time, timezone)
hour(time, timezone)
minute(time, timezone)
```

### ⚡ Special Behaviors

#### **Chart Type Dependencies:**
- **Time-based charts:** Standard timestamp behavior
- **Non-time-based charts:** Different timestamp handling (Renko, P&F, etc.)

#### **Realtime Bars:**
- **Dynamic timestamps:** Update continuously during bar formation
- **Final timestamp:** Set when bar closes

#### **Session Handling:**
```pinescript
// Session specifications
regular_session = "0930-1600"  
extended_session = "0400-2000"

// Check if time is in session
in_session = not na(time(timeframe.period, regular_session))
```

## 🎯 Implementation for Our Trading System

### 1. **Timestamp Conversion (TradingView Style)**
```python
import datetime
from typing import Union

class TradingViewTimeHandler:
    """Handle time like TradingView Pine Script"""
    
    @staticmethod
    def to_unix_ms(dt: datetime.datetime) -> int:
        """Convert datetime to Unix milliseconds (Pine Script format)"""
        return int(dt.timestamp() * 1000)
    
    @staticmethod
    def from_unix_ms(timestamp_ms: int) -> datetime.datetime:
        """Convert Unix milliseconds to datetime"""
        return datetime.datetime.fromtimestamp(timestamp_ms / 1000)
    
    @staticmethod
    def format_time_tv(timestamp_ms: int, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format timestamp like TradingView str.format_time()"""
        dt = TradingViewTimeHandler.from_unix_ms(timestamp_ms)
        return dt.strftime(format_str)
    
    @staticmethod
    def get_bar_time(bar_datetime: datetime.datetime, timeframe: str) -> int:
        """Get bar opening time like Pine Script 'time' variable"""
        # Align to timeframe boundaries
        if timeframe == "1Min":
            aligned = bar_datetime.replace(second=0, microsecond=0)
        elif timeframe == "5Min":
            minute = (bar_datetime.minute // 5) * 5
            aligned = bar_datetime.replace(minute=minute, second=0, microsecond=0)
        elif timeframe == "15Min":
            minute = (bar_datetime.minute // 15) * 15
            aligned = bar_datetime.replace(minute=minute, second=0, microsecond=0)
        elif timeframe == "1Hour":
            aligned = bar_datetime.replace(minute=0, second=0, microsecond=0)
        else:
            aligned = bar_datetime
        
        return TradingViewTimeHandler.to_unix_ms(aligned)
```

### 2. **Session Detection**
```python
class SessionManager:
    """TradingView-style session management"""
    
    def __init__(self, timezone: str = "America/New_York"):
        self.timezone = timezone
        self.regular_session = (9, 30, 16, 0)  # 9:30 AM - 4:00 PM
        self.extended_session = (4, 0, 20, 0)   # 4:00 AM - 8:00 PM
    
    def is_in_session(self, timestamp_ms: int, extended: bool = False) -> bool:
        """Check if timestamp is within trading session"""
        dt = TradingViewTimeHandler.from_unix_ms(timestamp_ms)
        
        session_start, session_end = (
            self.extended_session if extended else self.regular_session
        )
        
        time_minutes = dt.hour * 60 + dt.minute
        start_minutes = session_start[0] * 60 + session_start[1]
        end_minutes = session_end[0] * 60 + session_end[1]
        
        return start_minutes <= time_minutes <= end_minutes
```

### 3. **Chart Data Time Alignment**
```python
def align_chart_data_timestamps(df, timeframe: str):
    """Align DataFrame timestamps to TradingView format"""
    
    # Convert to Unix milliseconds for consistency
    df['time_unix_ms'] = df.index.map(TradingViewTimeHandler.to_unix_ms)
    
    # Add TradingView-style time variables
    df['year'] = df.index.year
    df['month'] = df.index.month  
    df['dayofweek'] = df.index.dayofweek + 1  # Pine Script: 1=Sunday
    df['hour'] = df.index.hour
    df['minute'] = df.index.minute
    
    # Add session flags
    session_mgr = SessionManager()
    df['in_regular_session'] = df['time_unix_ms'].apply(
        lambda x: session_mgr.is_in_session(x, extended=False)
    )
    df['in_extended_session'] = df['time_unix_ms'].apply(
        lambda x: session_mgr.is_in_session(x, extended=True)
    )
    
    return df
```

### 4. **Real-time Bar Handling**
```python
class RealtimeBarManager:
    """Handle realtime bars like TradingView"""
    
    def __init__(self, timeframe: str):
        self.timeframe = timeframe
        self.current_bar = None
        self.bar_close_time = None
    
    def update_bar(self, price_data: dict) -> dict:
        """Update current bar with new tick data"""
        now = datetime.datetime.now()
        bar_time = TradingViewTimeHandler.get_bar_time(now, self.timeframe)
        
        if self.current_bar is None or bar_time > self.current_bar['time']:
            # New bar starting
            self.current_bar = {
                'time': bar_time,
                'open': price_data['price'],
                'high': price_data['price'],
                'low': price_data['price'],
                'close': price_data['price'],
                'volume': price_data.get('volume', 0)
            }
        else:
            # Update current bar
            self.current_bar['high'] = max(self.current_bar['high'], price_data['price'])
            self.current_bar['low'] = min(self.current_bar['low'], price_data['price'])
            self.current_bar['close'] = price_data['price']
            self.current_bar['volume'] += price_data.get('volume', 0)
        
        return self.current_bar.copy()
```

## 🔗 Integration with Current System

### Dashboard Chart Data Format:
```python
# Convert our Flask data to TradingView timestamp format
def format_for_dashboard(bars_df):
    """Format bar data for TradingView Lightweight Charts"""
    chart_data = []
    
    for timestamp, row in bars_df.iterrows():
        # Use Unix seconds (not milliseconds) for Lightweight Charts
        time_unix_seconds = int(timestamp.timestamp())
        
        chart_data.append({
            'time': time_unix_seconds,  # Lightweight Charts expects seconds
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'volume': int(row['volume'])
        })
    
    return chart_data
```

## 💡 Key Implementation Notes

1. **Milliseconds vs Seconds:** Pine Script uses milliseconds, Lightweight Charts uses seconds
2. **Timezone Awareness:** Always specify timezones explicitly
3. **Session Boundaries:** Critical for strategy timing and backtesting
4. **Realtime Updates:** Handle bar updates dynamically like TradingView
5. **Calendar Functions:** Essential for time-based filtering and analysis

---

**This comprehensive Pine Script time handling knowledge is now committed to memory for TradingView-compatible implementations.**