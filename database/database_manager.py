import sqlite3
import pandas as pd
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path='database/trading_data.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historical_data (
                timestamp DATETIME,
                symbol TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                timeframe TEXT,
                PRIMARY KEY (timestamp, symbol, timeframe)
            )
        ''')
        self.conn.commit()

    def store_historical_data(self, symbol, timeframe, df):
        if df.empty:
            return
            
        df['symbol'] = symbol
        df['timeframe'] = timeframe
        df.to_sql('historical_data', self.conn, if_exists='append', index=True, index_label='timestamp')

    def get_historical_data(self, symbol, timeframe, start_date, end_date):
        query = """
            SELECT * FROM historical_data 
            WHERE symbol = ? AND timeframe = ? AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp
        """
        try:
            df = pd.read_sql_query(query, self.conn, params=(symbol, timeframe, start_date, end_date), index_col='timestamp')
            # Drop duplicate columns that might have been created
            df = df.loc[:,~df.columns.duplicated()]
            return df
        except Exception as e:
            print(f"Error reading from database: {e}")
            return pd.DataFrame()

    def get_latest_timestamp(self, symbol, timeframe):
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(timestamp) FROM historical_data WHERE symbol = ? AND timeframe = ?", (symbol, timeframe))
        result = cursor.fetchone()[0]
        if result:
            return pd.to_datetime(result)
        return None

    def close(self):
        self.conn.close()
