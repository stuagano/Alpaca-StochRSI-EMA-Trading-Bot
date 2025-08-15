import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from backtesting.backtesting_engine import BacktestResult

class BacktestVisualizer:
    """
    Comprehensive visualization for backtesting results
    """
    
    def __init__(self, theme: str = "plotly_dark"):
        self.theme = theme
        self.logger = logging.getLogger('backtesting.visualizer')
        
        # Color schemes
        self.colors = {
            'primary': '#1f77b4',
            'success': '#2ca02c', 
            'danger': '#d62728',
            'warning': '#ff7f0e',
            'info': '#17becf',
            'light': '#7f7f7f',
            'dark': '#2f2f2f'
        }
    
    def create_performance_dashboard(self, result: BacktestResult, 
                                  market_data: pd.DataFrame = None) -> go.Figure:
        """
        Create comprehensive performance dashboard
        """
        
        # Create subplots
        fig = make_subplots(
            rows=4, cols=2,
            subplot_titles=[
                'Portfolio Value Over Time',
                'Drawdown Analysis', 
                'Monthly Returns Heatmap',
                'Trade Distribution',
                'Rolling Sharpe Ratio',
                'Risk-Return Scatter',
                'Trade Timeline',
                'Performance Metrics'
            ],
            specs=[
                [{'colspan': 2}, None],
                [{'type': 'heatmap'}, {'type': 'histogram'}],
                [{'type': 'scatter'}, {'type': 'scatter'}],
                [{'colspan': 2}, None]
            ],
            vertical_spacing=0.08,
            horizontal_spacing=0.1
        )
        
        # 1. Portfolio Value Over Time
        if result.portfolio_value and result.timestamps:
            timestamps = pd.to_datetime(result.timestamps)
            portfolio_values = result.portfolio_value
            
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=portfolio_values,
                    mode='lines',
                    name='Portfolio Value',
                    line=dict(color=self.colors['primary'], width=2),
                    hovertemplate='Date: %{x}<br>Value: $%{y:,.2f}<extra></extra>'
                ),
                row=1, col=1
            )
            
            # Add benchmark if market data provided
            if market_data is not None:
                benchmark_returns = market_data['close'].pct_change().fillna(0)
                benchmark_value = (1 + benchmark_returns).cumprod() * result.portfolio_value[0]
                
                fig.add_trace(
                    go.Scatter(
                        x=market_data.index,
                        y=benchmark_value,
                        mode='lines',
                        name='Buy & Hold',
                        line=dict(color=self.colors['light'], width=1, dash='dash'),
                        hovertemplate='Date: %{x}<br>Value: $%{y:,.2f}<extra></extra>'
                    ),
                    row=1, col=1
                )
        
        # 2. Drawdown Analysis
        if result.portfolio_value:
            portfolio_values = np.array(result.portfolio_value)
            running_max = np.maximum.accumulate(portfolio_values)
            drawdown = (portfolio_values - running_max) / running_max * 100
            
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=drawdown,
                    mode='lines',
                    name='Drawdown',
                    line=dict(color=self.colors['danger'], width=1),
                    fill='tonexty',
                    fillcolor='rgba(214, 39, 40, 0.3)',
                    hovertemplate='Date: %{x}<br>Drawdown: %{y:.2f}%<extra></extra>'
                ),
                row=2, col=1
            )
        
        # 3. Trade Distribution (Histogram)
        if result.trades:
            pnl_values = [trade['pnl'] for trade in result.trades]
            
            fig.add_trace(
                go.Histogram(
                    x=pnl_values,
                    nbinsx=20,
                    name='Trade P&L',
                    marker_color=self.colors['info'],
                    opacity=0.7,
                    hovertemplate='P&L Range: %{x}<br>Count: %{y}<extra></extra>'
                ),
                row=2, col=2
            )
        
        # 4. Rolling Sharpe Ratio (if enough data)
        if len(result.portfolio_value) > 50:
            returns = pd.Series(result.portfolio_value).pct_change().dropna()
            rolling_sharpe = returns.rolling(window=30).apply(
                lambda x: x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0
            )
            
            fig.add_trace(
                go.Scatter(
                    x=timestamps[30:],
                    y=rolling_sharpe[30:],
                    mode='lines',
                    name='30-Day Sharpe',
                    line=dict(color=self.colors['success'], width=1),
                    hovertemplate='Date: %{x}<br>Sharpe: %{y:.2f}<extra></extra>'
                ),
                row=3, col=1
            )
        
        # 5. Risk-Return Scatter (placeholder - would need multiple strategies)
        fig.add_trace(
            go.Scatter(
                x=[result.volatility],
                y=[result.total_return_pct],
                mode='markers',
                name=result.strategy_name,
                marker=dict(
                    size=15,
                    color=self.colors['primary'],
                    symbol='diamond'
                ),
                hovertemplate='Volatility: %{x:.2f}%<br>Return: %{y:.2f}%<extra></extra>'
            ),
            row=3, col=2
        )
        
        # 6. Trade Timeline
        if result.trades:
            trade_times = [pd.to_datetime(trade['entry_time']) for trade in result.trades]
            trade_pnl = [trade['pnl'] for trade in result.trades]
            
            colors = [self.colors['success'] if pnl > 0 else self.colors['danger'] for pnl in trade_pnl]
            
            fig.add_trace(
                go.Scatter(
                    x=trade_times,
                    y=trade_pnl,
                    mode='markers',
                    name='Individual Trades',
                    marker=dict(
                        size=8,
                        color=colors,
                        symbol='circle'
                    ),
                    hovertemplate='Date: %{x}<br>P&L: $%{y:.2f}<extra></extra>'
                ),
                row=4, col=1
            )
        
        # Update layout
        fig.update_layout(
            template=self.theme,
            title=dict(
                text=f"Backtesting Dashboard: {result.strategy_name}",
                x=0.5,
                font=dict(size=20)
            ),
            showlegend=True,
            height=1200,
            hovermode='x unified'
        )
        
        # Update axes labels
        fig.update_xaxes(title_text="Date", row=1, col=1)
        fig.update_yaxes(title_text="Portfolio Value ($)", row=1, col=1)
        
        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_yaxes(title_text="Drawdown (%)", row=2, col=1)
        
        fig.update_xaxes(title_text="Trade P&L ($)", row=2, col=2)
        fig.update_yaxes(title_text="Frequency", row=2, col=2)
        
        fig.update_xaxes(title_text="Date", row=3, col=1)
        fig.update_yaxes(title_text="Rolling Sharpe Ratio", row=3, col=1)
        
        fig.update_xaxes(title_text="Volatility (%)", row=3, col=2)
        fig.update_yaxes(title_text="Return (%)", row=3, col=2)
        
        fig.update_xaxes(title_text="Date", row=4, col=1)
        fig.update_yaxes(title_text="Trade P&L ($)", row=4, col=1)
        
        return fig
    
    def create_strategy_comparison(self, results: List[BacktestResult]) -> go.Figure:
        """
        Compare multiple strategy results
        """
        
        if not results:
            return go.Figure()
        
        # Create comparison metrics
        strategies = [result.strategy_name for result in results]
        returns = [result.total_return_pct for result in results]
        sharpe_ratios = [result.sharpe_ratio for result in results]
        max_drawdowns = [result.max_drawdown_pct for result in results]
        win_rates = [result.win_rate for result in results]
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=[
                'Total Returns Comparison',
                'Risk-Return Scatter',
                'Sharpe Ratio Comparison', 
                'Maximum Drawdown Comparison'
            ]
        )
        
        # 1. Total Returns Bar Chart
        fig.add_trace(
            go.Bar(
                x=strategies,
                y=returns,
                name='Total Return (%)',
                marker_color=self.colors['primary'],
                hovertemplate='Strategy: %{x}<br>Return: %{y:.2f}%<extra></extra>'
            ),
            row=1, col=1
        )
        
        # 2. Risk-Return Scatter
        volatilities = [result.volatility for result in results]
        
        fig.add_trace(
            go.Scatter(
                x=volatilities,
                y=returns,
                mode='markers+text',
                text=strategies,
                textposition='top center',
                name='Risk-Return',
                marker=dict(
                    size=15,
                    color=sharpe_ratios,
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="Sharpe Ratio")
                ),
                hovertemplate='Strategy: %{text}<br>Volatility: %{x:.2f}%<br>Return: %{y:.2f}%<extra></extra>'
            ),
            row=1, col=2
        )
        
        # 3. Sharpe Ratio Comparison
        fig.add_trace(
            go.Bar(
                x=strategies,
                y=sharpe_ratios,
                name='Sharpe Ratio',
                marker_color=self.colors['success'],
                hovertemplate='Strategy: %{x}<br>Sharpe: %{y:.2f}<extra></extra>'
            ),
            row=2, col=1
        )
        
        # 4. Max Drawdown Comparison
        fig.add_trace(
            go.Bar(
                x=strategies,
                y=[-dd for dd in max_drawdowns],  # Negative for better visualization
                name='Max Drawdown (%)',
                marker_color=self.colors['danger'],
                hovertemplate='Strategy: %{x}<br>Max DD: %{y:.2f}%<extra></extra>'
            ),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            template=self.theme,
            title=dict(
                text="Strategy Performance Comparison",
                x=0.5,
                font=dict(size=20)
            ),
            showlegend=False,
            height=800
        )
        
        # Update axes
        fig.update_xaxes(title_text="Strategy", row=1, col=1)
        fig.update_yaxes(title_text="Return (%)", row=1, col=1)
        
        fig.update_xaxes(title_text="Volatility (%)", row=1, col=2)
        fig.update_yaxes(title_text="Return (%)", row=1, col=2)
        
        fig.update_xaxes(title_text="Strategy", row=2, col=1)
        fig.update_yaxes(title_text="Sharpe Ratio", row=2, col=1)
        
        fig.update_xaxes(title_text="Strategy", row=2, col=2)
        fig.update_yaxes(title_text="Max Drawdown (%)", row=2, col=2)
        
        return fig
    
    def create_monte_carlo_analysis(self, mc_results: Dict[str, Any]) -> go.Figure:
        """
        Create Monte Carlo analysis visualization
        """
        
        if 'error' in mc_results:
            return go.Figure()
        
        # Create distribution plots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=[
                'Total Return Distribution',
                'Maximum Drawdown Distribution',
                'Final Portfolio Value Distribution',
                'Confidence Intervals Summary'
            ]
        )
        
        # Since we don't have the raw simulation data, create conceptual distributions
        # In a real implementation, you'd store the simulation results
        
        return_data = mc_results['total_return']
        dd_data = mc_results['max_drawdown']
        value_data = mc_results['final_portfolio_value']
        
        # Create normal distributions approximations for visualization
        x_return = np.linspace(
            return_data['min'], 
            return_data['max'], 
            100
        )
        y_return = np.exp(-0.5 * ((x_return - return_data['mean']) / return_data['std']) ** 2)
        
        fig.add_trace(
            go.Scatter(
                x=x_return,
                y=y_return,
                mode='lines',
                name='Return Distribution',
                fill='tonexty',
                line=dict(color=self.colors['primary'])
            ),
            row=1, col=1
        )
        
        # Add confidence intervals
        fig.add_vline(
            x=return_data['percentile_5'],
            line_dash="dash",
            line_color=self.colors['danger'],
            annotation_text=f"5th percentile: ${return_data['percentile_5']:,.0f}",
            row=1, col=1
        )
        
        fig.add_vline(
            x=return_data['percentile_95'],
            line_dash="dash", 
            line_color=self.colors['success'],
            annotation_text=f"95th percentile: ${return_data['percentile_95']:,.0f}",
            row=1, col=1
        )
        
        # Summary metrics table
        summary_text = f"""
        <b>Monte Carlo Analysis Summary</b><br>
        Simulations: {mc_results['num_simulations']:,}<br>
        Confidence Level: {mc_results['confidence_level'] * 100:.0f}%<br><br>
        
        <b>Probability of Profit:</b> {mc_results['probability_of_profit']:.1f}%<br><br>
        
        <b>Expected Return:</b> ${return_data['mean']:,.0f}<br>
        <b>Worst Case (5%):</b> ${return_data['percentile_5']:,.0f}<br>
        <b>Best Case (95%):</b> ${return_data['percentile_95']:,.0f}<br><br>
        
        <b>Expected Max DD:</b> ${dd_data['mean']:,.0f}<br>
        <b>Worst DD (95%):</b> ${dd_data['percentile_95']:,.0f}<br>
        """
        
        fig.add_annotation(
            x=0.5, y=0.5,
            xref='x4', yref='y4',
            text=summary_text,
            showarrow=False,
            font=dict(size=12),
            align='left',
            bgcolor='rgba(255,255,255,0.1)',
            bordercolor='rgba(255,255,255,0.3)',
            borderwidth=1
        )
        
        fig.update_layout(
            template=self.theme,
            title=dict(
                text="Monte Carlo Analysis Results",
                x=0.5,
                font=dict(size=20)
            ),
            showlegend=False,
            height=800
        )
        
        return fig
    
    def create_walk_forward_analysis(self, wfa_results: List[BacktestResult]) -> go.Figure:
        """
        Create walk-forward analysis visualization
        """
        
        if not wfa_results:
            return go.Figure()
        
        # Extract metrics from walk-forward results
        periods = [f"Period {i+1}" for i in range(len(wfa_results))]
        returns = [result.total_return_pct for result in wfa_results]
        sharpe_ratios = [result.sharpe_ratio for result in wfa_results]
        win_rates = [result.win_rate for result in wfa_results]
        max_drawdowns = [result.max_drawdown_pct for result in wfa_results]
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=[
                'Period Returns',
                'Period Sharpe Ratios',
                'Period Win Rates',
                'Period Max Drawdowns'
            ]
        )
        
        # 1. Period Returns
        fig.add_trace(
            go.Bar(
                x=periods,
                y=returns,
                name='Returns (%)',
                marker_color=[self.colors['success'] if r > 0 else self.colors['danger'] for r in returns],
                hovertemplate='Period: %{x}<br>Return: %{y:.2f}%<extra></extra>'
            ),
            row=1, col=1
        )
        
        # 2. Sharpe Ratios
        fig.add_trace(
            go.Scatter(
                x=periods,
                y=sharpe_ratios,
                mode='lines+markers',
                name='Sharpe Ratio',
                line=dict(color=self.colors['primary']),
                hovertemplate='Period: %{x}<br>Sharpe: %{y:.2f}<extra></extra>'
            ),
            row=1, col=2
        )
        
        # 3. Win Rates
        fig.add_trace(
            go.Scatter(
                x=periods,
                y=win_rates,
                mode='lines+markers',
                name='Win Rate (%)',
                line=dict(color=self.colors['info']),
                hovertemplate='Period: %{x}<br>Win Rate: %{y:.1f}%<extra></extra>'
            ),
            row=2, col=1
        )
        
        # 4. Max Drawdowns
        fig.add_trace(
            go.Bar(
                x=periods,
                y=max_drawdowns,
                name='Max DD (%)',
                marker_color=self.colors['warning'],
                hovertemplate='Period: %{x}<br>Max DD: %{y:.2f}%<extra></extra>'
            ),
            row=2, col=2
        )
        
        # Add mean lines
        fig.add_hline(
            y=np.mean(returns),
            line_dash="dash",
            line_color=self.colors['light'],
            annotation_text=f"Mean Return: {np.mean(returns):.2f}%",
            row=1, col=1
        )
        
        fig.add_hline(
            y=np.mean(sharpe_ratios),
            line_dash="dash",
            line_color=self.colors['light'],
            annotation_text=f"Mean Sharpe: {np.mean(sharpe_ratios):.2f}",
            row=1, col=2
        )
        
        fig.update_layout(
            template=self.theme,
            title=dict(
                text="Walk-Forward Analysis Results",
                x=0.5,
                font=dict(size=20)
            ),
            showlegend=False,
            height=800
        )
        
        # Update axes
        fig.update_xaxes(title_text="Period", row=1, col=1)
        fig.update_yaxes(title_text="Return (%)", row=1, col=1)
        
        fig.update_xaxes(title_text="Period", row=1, col=2)
        fig.update_yaxes(title_text="Sharpe Ratio", row=1, col=2)
        
        fig.update_xaxes(title_text="Period", row=2, col=1)
        fig.update_yaxes(title_text="Win Rate (%)", row=2, col=1)
        
        fig.update_xaxes(title_text="Period", row=2, col=2)
        fig.update_yaxes(title_text="Max Drawdown (%)", row=2, col=2)
        
        return fig
    
    def export_charts(self, figures: List[go.Figure], 
                     filenames: List[str], 
                     output_dir: str = "backtest_reports") -> List[str]:
        """
        Export charts to files
        """
        
        import os
        
        os.makedirs(output_dir, exist_ok=True)
        
        exported_files = []
        
        for fig, filename in zip(figures, filenames):
            # Export as HTML
            html_path = os.path.join(output_dir, f"{filename}.html")
            fig.write_html(html_path)
            exported_files.append(html_path)
            
            # Export as PNG (requires kaleido)
            try:
                png_path = os.path.join(output_dir, f"{filename}.png")
                fig.write_image(png_path, width=1200, height=800, scale=2)
                exported_files.append(png_path)
            except Exception as e:
                self.logger.warning(f"Could not export PNG for {filename}: {e}")
        
        self.logger.info(f"Exported {len(exported_files)} chart files to {output_dir}")
        
        return exported_files