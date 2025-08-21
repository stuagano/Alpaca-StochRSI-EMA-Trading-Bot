"""
Unit Tests for Signal Quality Metrics Tracking

Tests the comprehensive signal quality metrics system that tracks:
- Signal accuracy and reliability scores
- False positive/negative rates
- Signal confidence metrics
- Performance over time analytics
- Quality score calculations
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import sys
import os
from typing import Dict, List, Tuple, Optional
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from tests.epic1_signal_quality.fixtures.epic1_test_fixtures import (
    epic1_config, signal_quality_test_scenarios
)


class SignalQualityMetrics:
    """Comprehensive signal quality metrics tracking system."""
    
    def __init__(self, config: dict):
        self.track_metrics = config.get('track_metrics', True)
        self.confidence_threshold = config.get('confidence_threshold', 0.7)
        self.false_positive_penalty = config.get('false_positive_penalty', 0.2)
        self.trend_alignment_bonus = config.get('trend_alignment_bonus', 0.1)
        
        # Metrics storage
        self.signal_history = []
        self.performance_history = []
        self.quality_scores = []
        
        # Tracking windows
        self.short_term_window = 20   # signals
        self.medium_term_window = 100 # signals
        self.long_term_window = 500   # signals
    
    def record_signal(self, signal_data: Dict) -> None:
        """Record a new signal with metadata."""
        signal_record = {
            'timestamp': signal_data.get('timestamp', datetime.now()),
            'signal_type': signal_data.get('signal_type', 'NEUTRAL'),
            'signal_strength': signal_data.get('signal_strength', 0.0),
            'confidence_score': signal_data.get('confidence_score', 0.0),
            'volume_confirmed': signal_data.get('volume_confirmed', False),
            'multi_timeframe_aligned': signal_data.get('multi_timeframe_aligned', False),
            'dynamic_bands_used': signal_data.get('dynamic_bands_used', False),
            'market_conditions': signal_data.get('market_conditions', {}),
            'signal_id': signal_data.get('signal_id', len(self.signal_history))
        }
        
        self.signal_history.append(signal_record)
    
    def record_outcome(self, signal_id: int, outcome_data: Dict) -> None:
        """Record the outcome of a previously generated signal."""
        outcome_record = {
            'signal_id': signal_id,
            'timestamp': outcome_data.get('timestamp', datetime.now()),
            'outcome': outcome_data.get('outcome', 'unknown'),  # 'profit', 'loss', 'neutral', 'timeout'
            'profit_loss': outcome_data.get('profit_loss', 0.0),
            'holding_period': outcome_data.get('holding_period', 0),  # minutes
            'exit_reason': outcome_data.get('exit_reason', 'unknown'),
            'max_favorable_excursion': outcome_data.get('max_favorable_excursion', 0.0),
            'max_adverse_excursion': outcome_data.get('max_adverse_excursion', 0.0)
        }
        
        self.performance_history.append(outcome_record)
        self._update_quality_scores()
    
    def calculate_accuracy_metrics(self, window_size: Optional[int] = None) -> Dict:
        """Calculate signal accuracy metrics over specified window."""
        if not self.performance_history:
            return self._empty_accuracy_metrics()
        
        # Determine window
        if window_size is None:
            outcomes = self.performance_history
        else:
            outcomes = self.performance_history[-window_size:]
        
        if not outcomes:
            return self._empty_accuracy_metrics()
        
        # Calculate basic accuracy metrics
        total_signals = len(outcomes)
        profitable_signals = sum(1 for o in outcomes if o['profit_loss'] > 0)
        losing_signals = sum(1 for o in outcomes if o['profit_loss'] < 0)
        neutral_signals = sum(1 for o in outcomes if o['profit_loss'] == 0)
        
        accuracy_rate = profitable_signals / total_signals if total_signals > 0 else 0
        loss_rate = losing_signals / total_signals if total_signals > 0 else 0
        
        # Calculate false positive/negative rates
        false_positives = sum(1 for o in outcomes 
                            if self._get_signal_type(o['signal_id']) == 'BUY' and o['profit_loss'] < 0)
        false_negatives = sum(1 for o in outcomes 
                            if self._get_signal_type(o['signal_id']) == 'SELL' and o['profit_loss'] < 0)
        
        buy_signals = sum(1 for o in outcomes if self._get_signal_type(o['signal_id']) == 'BUY')
        sell_signals = sum(1 for o in outcomes if self._get_signal_type(o['signal_id']) == 'SELL')
        
        false_positive_rate = false_positives / buy_signals if buy_signals > 0 else 0
        false_negative_rate = false_negatives / sell_signals if sell_signals > 0 else 0
        
        # Calculate profit metrics
        total_profit = sum(o['profit_loss'] for o in outcomes)
        avg_profit_per_signal = total_profit / total_signals if total_signals > 0 else 0
        
        profitable_outcomes = [o for o in outcomes if o['profit_loss'] > 0]
        losing_outcomes = [o for o in outcomes if o['profit_loss'] < 0]
        
        avg_win = np.mean([o['profit_loss'] for o in profitable_outcomes]) if profitable_outcomes else 0
        avg_loss = np.mean([o['profit_loss'] for o in losing_outcomes]) if losing_outcomes else 0
        
        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        
        # Calculate holding period metrics
        avg_holding_period = np.mean([o['holding_period'] for o in outcomes]) if outcomes else 0
        
        return {
            'total_signals': total_signals,
            'accuracy_rate': accuracy_rate,
            'loss_rate': loss_rate,
            'false_positive_rate': false_positive_rate,
            'false_negative_rate': false_negative_rate,
            'total_profit': total_profit,
            'avg_profit_per_signal': avg_profit_per_signal,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'win_loss_ratio': win_loss_ratio,
            'avg_holding_period': avg_holding_period,
            'profitable_signals': profitable_signals,
            'losing_signals': losing_signals,
            'neutral_signals': neutral_signals
        }
    
    def calculate_confidence_metrics(self, window_size: Optional[int] = None) -> Dict:
        """Calculate confidence-related metrics."""
        if not self.signal_history:
            return self._empty_confidence_metrics()
        
        # Determine window
        if window_size is None:
            signals = self.signal_history
        else:
            signals = self.signal_history[-window_size:]
        
        if not signals:
            return self._empty_confidence_metrics()
        
        # Basic confidence statistics
        confidence_scores = [s['confidence_score'] for s in signals]
        avg_confidence = np.mean(confidence_scores)
        confidence_std = np.std(confidence_scores)
        
        # High confidence signals
        high_confidence_signals = [s for s in signals if s['confidence_score'] >= self.confidence_threshold]
        high_confidence_rate = len(high_confidence_signals) / len(signals)
        
        # Confidence vs Performance correlation
        correlation_data = self._calculate_confidence_performance_correlation(signals)
        
        # Volume confirmation rate
        volume_confirmed_rate = sum(1 for s in signals if s['volume_confirmed']) / len(signals)
        
        # Multi-timeframe alignment rate
        mtf_aligned_rate = sum(1 for s in signals if s['multi_timeframe_aligned']) / len(signals)
        
        # Dynamic bands usage rate
        dynamic_bands_rate = sum(1 for s in signals if s['dynamic_bands_used']) / len(signals)
        
        return {
            'avg_confidence': avg_confidence,
            'confidence_std': confidence_std,
            'high_confidence_rate': high_confidence_rate,
            'confidence_threshold': self.confidence_threshold,
            'volume_confirmed_rate': volume_confirmed_rate,
            'mtf_aligned_rate': mtf_aligned_rate,
            'dynamic_bands_rate': dynamic_bands_rate,
            'confidence_performance_correlation': correlation_data
        }
    
    def calculate_quality_score(self, window_size: Optional[int] = None) -> Dict:
        """Calculate comprehensive quality score."""
        accuracy_metrics = self.calculate_accuracy_metrics(window_size)
        confidence_metrics = self.calculate_confidence_metrics(window_size)
        
        if accuracy_metrics['total_signals'] == 0:
            return {
                'overall_quality_score': 0.0,
                'accuracy_component': 0.0,
                'confidence_component': 0.0,
                'reliability_component': 0.0,
                'enhancement_component': 0.0,
                'grade': 'N/A'
            }
        
        # Accuracy component (40% weight)
        accuracy_component = (
            accuracy_metrics['accuracy_rate'] * 0.6 +
            (1 - accuracy_metrics['false_positive_rate']) * 0.2 +
            (1 - accuracy_metrics['false_negative_rate']) * 0.2
        ) * 0.4
        
        # Confidence component (25% weight)
        confidence_component = (
            confidence_metrics['avg_confidence'] * 0.5 +
            confidence_metrics['high_confidence_rate'] * 0.3 +
            confidence_metrics['confidence_performance_correlation']['correlation'] * 0.2
        ) * 0.25
        
        # Reliability component (20% weight)
        reliability_component = (
            min(1.0, accuracy_metrics['win_loss_ratio'] / 2.0) * 0.4 +
            (1 - min(1.0, accuracy_metrics['loss_rate'] * 2)) * 0.3 +
            min(1.0, accuracy_metrics['total_signals'] / 50) * 0.3  # Sample size factor
        ) * 0.20
        
        # Enhancement component (15% weight) - Epic 1 features
        enhancement_component = (
            confidence_metrics['volume_confirmed_rate'] * 0.4 +
            confidence_metrics['mtf_aligned_rate'] * 0.3 +
            confidence_metrics['dynamic_bands_rate'] * 0.3
        ) * 0.15
        
        # Calculate overall score
        overall_score = (
            accuracy_component + 
            confidence_component + 
            reliability_component + 
            enhancement_component
        )
        
        # Apply penalties
        if accuracy_metrics['false_positive_rate'] > 0.3:
            overall_score *= (1 - self.false_positive_penalty)
        
        # Apply bonuses
        if confidence_metrics['mtf_aligned_rate'] > 0.8:
            overall_score *= (1 + self.trend_alignment_bonus)
        
        overall_score = min(1.0, max(0.0, overall_score))
        
        # Assign grade
        if overall_score >= 0.9:
            grade = 'A+'
        elif overall_score >= 0.8:
            grade = 'A'
        elif overall_score >= 0.7:
            grade = 'B+'
        elif overall_score >= 0.6:
            grade = 'B'
        elif overall_score >= 0.5:
            grade = 'C+'
        elif overall_score >= 0.4:
            grade = 'C'
        elif overall_score >= 0.3:
            grade = 'D'
        else:
            grade = 'F'
        
        return {
            'overall_quality_score': overall_score,
            'accuracy_component': accuracy_component,
            'confidence_component': confidence_component,
            'reliability_component': reliability_component,
            'enhancement_component': enhancement_component,
            'grade': grade
        }
    
    def get_performance_analytics(self) -> Dict:
        """Get comprehensive performance analytics."""
        # Calculate metrics for different time windows
        short_term = self.calculate_quality_score(self.short_term_window)
        medium_term = self.calculate_quality_score(self.medium_term_window)
        long_term = self.calculate_quality_score(self.long_term_window)
        overall = self.calculate_quality_score()
        
        # Trend analysis
        trend_analysis = self._calculate_performance_trends()
        
        # Feature effectiveness
        feature_effectiveness = self._analyze_feature_effectiveness()
        
        return {
            'quality_scores': {
                'short_term': short_term,
                'medium_term': medium_term,
                'long_term': long_term,
                'overall': overall
            },
            'trend_analysis': trend_analysis,
            'feature_effectiveness': feature_effectiveness,
            'summary_stats': {
                'total_signals_tracked': len(self.signal_history),
                'total_outcomes_recorded': len(self.performance_history),
                'tracking_period_days': self._get_tracking_period_days(),
                'data_completeness': len(self.performance_history) / len(self.signal_history) if self.signal_history else 0
            }
        }
    
    def export_metrics_report(self, format: str = 'json') -> str:
        """Export comprehensive metrics report."""
        analytics = self.get_performance_analytics()
        
        report = {
            'report_generated': datetime.now().isoformat(),
            'epic1_signal_quality_metrics': analytics,
            'configuration': {
                'confidence_threshold': self.confidence_threshold,
                'false_positive_penalty': self.false_positive_penalty,
                'trend_alignment_bonus': self.trend_alignment_bonus
            }
        }
        
        if format == 'json':
            return json.dumps(report, indent=2, default=str)
        else:
            # Could implement CSV, HTML, etc.
            return str(report)
    
    def _get_signal_type(self, signal_id: int) -> str:
        """Get signal type for given signal ID."""
        for signal in self.signal_history:
            if signal['signal_id'] == signal_id:
                return signal['signal_type']
        return 'UNKNOWN'
    
    def _update_quality_scores(self):
        """Update quality scores after new outcome data."""
        if len(self.performance_history) % 10 == 0:  # Update every 10 outcomes
            quality_score = self.calculate_quality_score()
            self.quality_scores.append({
                'timestamp': datetime.now(),
                'score': quality_score['overall_quality_score'],
                'grade': quality_score['grade']
            })
    
    def _calculate_confidence_performance_correlation(self, signals: List[Dict]) -> Dict:
        """Calculate correlation between confidence and performance."""
        if not signals or not self.performance_history:
            return {'correlation': 0.0, 'sample_size': 0}
        
        # Match signals with outcomes
        confidence_performance_pairs = []
        for signal in signals:
            for outcome in self.performance_history:
                if outcome['signal_id'] == signal['signal_id']:
                    confidence_performance_pairs.append({
                        'confidence': signal['confidence_score'],
                        'performance': 1 if outcome['profit_loss'] > 0 else 0
                    })
                    break
        
        if len(confidence_performance_pairs) < 2:
            return {'correlation': 0.0, 'sample_size': len(confidence_performance_pairs)}
        
        confidences = [p['confidence'] for p in confidence_performance_pairs]
        performances = [p['performance'] for p in confidence_performance_pairs]
        
        correlation = np.corrcoef(confidences, performances)[0, 1]
        correlation = 0.0 if np.isnan(correlation) else correlation
        
        return {
            'correlation': correlation,
            'sample_size': len(confidence_performance_pairs)
        }
    
    def _calculate_performance_trends(self) -> Dict:
        """Calculate performance trends over time."""
        if len(self.quality_scores) < 3:
            return {'trend': 'insufficient_data', 'trend_strength': 0.0}
        
        # Analyze quality score trend
        recent_scores = [s['score'] for s in self.quality_scores[-10:]]
        x = np.arange(len(recent_scores))
        
        if len(recent_scores) > 1:
            trend_slope = np.polyfit(x, recent_scores, 1)[0]
            
            if trend_slope > 0.01:
                trend = 'improving'
            elif trend_slope < -0.01:
                trend = 'declining'
            else:
                trend = 'stable'
            
            trend_strength = abs(trend_slope)
        else:
            trend = 'stable'
            trend_strength = 0.0
        
        return {
            'trend': trend,
            'trend_strength': trend_strength,
            'recent_scores': recent_scores
        }
    
    def _analyze_feature_effectiveness(self) -> Dict:
        """Analyze effectiveness of Epic 1 features."""
        if not self.signal_history or not self.performance_history:
            return {}
        
        # Volume confirmation effectiveness
        volume_confirmed_outcomes = self._get_outcomes_by_feature('volume_confirmed', True)
        volume_not_confirmed_outcomes = self._get_outcomes_by_feature('volume_confirmed', False)
        
        volume_effectiveness = self._compare_feature_outcomes(
            volume_confirmed_outcomes, 
            volume_not_confirmed_outcomes
        )
        
        # Multi-timeframe alignment effectiveness
        mtf_aligned_outcomes = self._get_outcomes_by_feature('multi_timeframe_aligned', True)
        mtf_not_aligned_outcomes = self._get_outcomes_by_feature('multi_timeframe_aligned', False)
        
        mtf_effectiveness = self._compare_feature_outcomes(
            mtf_aligned_outcomes,
            mtf_not_aligned_outcomes
        )
        
        # Dynamic bands effectiveness
        dynamic_bands_outcomes = self._get_outcomes_by_feature('dynamic_bands_used', True)
        static_bands_outcomes = self._get_outcomes_by_feature('dynamic_bands_used', False)
        
        dynamic_effectiveness = self._compare_feature_outcomes(
            dynamic_bands_outcomes,
            static_bands_outcomes
        )
        
        return {
            'volume_confirmation': volume_effectiveness,
            'multi_timeframe_alignment': mtf_effectiveness,
            'dynamic_bands': dynamic_effectiveness
        }
    
    def _get_outcomes_by_feature(self, feature: str, value: bool) -> List[Dict]:
        """Get outcomes for signals with specific feature value."""
        matching_outcomes = []
        for outcome in self.performance_history:
            signal = next((s for s in self.signal_history if s['signal_id'] == outcome['signal_id']), None)
            if signal and signal.get(feature) == value:
                matching_outcomes.append(outcome)
        return matching_outcomes
    
    def _compare_feature_outcomes(self, feature_outcomes: List[Dict], 
                                 baseline_outcomes: List[Dict]) -> Dict:
        """Compare outcomes between feature-enabled and baseline signals."""
        if not feature_outcomes and not baseline_outcomes:
            return {'effectiveness': 'no_data'}
        
        feature_accuracy = sum(1 for o in feature_outcomes if o['profit_loss'] > 0) / len(feature_outcomes) if feature_outcomes else 0
        baseline_accuracy = sum(1 for o in baseline_outcomes if o['profit_loss'] > 0) / len(baseline_outcomes) if baseline_outcomes else 0
        
        feature_avg_profit = np.mean([o['profit_loss'] for o in feature_outcomes]) if feature_outcomes else 0
        baseline_avg_profit = np.mean([o['profit_loss'] for o in baseline_outcomes]) if baseline_outcomes else 0
        
        accuracy_improvement = feature_accuracy - baseline_accuracy
        profit_improvement = feature_avg_profit - baseline_avg_profit
        
        return {
            'feature_accuracy': feature_accuracy,
            'baseline_accuracy': baseline_accuracy,
            'accuracy_improvement': accuracy_improvement,
            'feature_avg_profit': feature_avg_profit,
            'baseline_avg_profit': baseline_avg_profit,
            'profit_improvement': profit_improvement,
            'feature_sample_size': len(feature_outcomes),
            'baseline_sample_size': len(baseline_outcomes)
        }
    
    def _get_tracking_period_days(self) -> float:
        """Get tracking period in days."""
        if not self.signal_history:
            return 0.0
        
        start_time = min(s['timestamp'] for s in self.signal_history)
        end_time = max(s['timestamp'] for s in self.signal_history)
        
        return (end_time - start_time).total_seconds() / 86400
    
    def _empty_accuracy_metrics(self) -> Dict:
        """Return empty accuracy metrics structure."""
        return {
            'total_signals': 0,
            'accuracy_rate': 0.0,
            'loss_rate': 0.0,
            'false_positive_rate': 0.0,
            'false_negative_rate': 0.0,
            'total_profit': 0.0,
            'avg_profit_per_signal': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'win_loss_ratio': 0.0,
            'avg_holding_period': 0.0,
            'profitable_signals': 0,
            'losing_signals': 0,
            'neutral_signals': 0
        }
    
    def _empty_confidence_metrics(self) -> Dict:
        """Return empty confidence metrics structure."""
        return {
            'avg_confidence': 0.0,
            'confidence_std': 0.0,
            'high_confidence_rate': 0.0,
            'confidence_threshold': self.confidence_threshold,
            'volume_confirmed_rate': 0.0,
            'mtf_aligned_rate': 0.0,
            'dynamic_bands_rate': 0.0,
            'confidence_performance_correlation': {'correlation': 0.0, 'sample_size': 0}
        }


class TestSignalQualityMetrics:
    """Test suite for signal quality metrics tracking."""
    
    def test_signal_recording(self, epic1_config):
        """Test recording of signal data."""
        metrics = SignalQualityMetrics(epic1_config['signal_quality'])
        
        # Record test signal
        signal_data = {
            'timestamp': datetime.now(),
            'signal_type': 'BUY',
            'signal_strength': 0.8,
            'confidence_score': 0.75,
            'volume_confirmed': True,
            'multi_timeframe_aligned': True,
            'dynamic_bands_used': True,
            'market_conditions': {'volatility': 'medium', 'trend': 'upward'}
        }
        
        metrics.record_signal(signal_data)
        
        # Verify recording
        assert len(metrics.signal_history) == 1
        recorded_signal = metrics.signal_history[0]
        
        assert recorded_signal['signal_type'] == 'BUY'
        assert recorded_signal['signal_strength'] == 0.8
        assert recorded_signal['confidence_score'] == 0.75
        assert recorded_signal['volume_confirmed'] == True
        assert recorded_signal['multi_timeframe_aligned'] == True
        assert recorded_signal['dynamic_bands_used'] == True
        assert 'signal_id' in recorded_signal
    
    def test_outcome_recording(self, epic1_config):
        """Test recording of signal outcomes."""
        metrics = SignalQualityMetrics(epic1_config['signal_quality'])
        
        # Record signal first
        signal_data = {
            'signal_type': 'BUY',
            'signal_strength': 0.8,
            'confidence_score': 0.75
        }
        metrics.record_signal(signal_data)
        signal_id = metrics.signal_history[0]['signal_id']
        
        # Record outcome
        outcome_data = {
            'outcome': 'profit',
            'profit_loss': 15.50,
            'holding_period': 45,
            'exit_reason': 'target_reached',
            'max_favorable_excursion': 20.00,
            'max_adverse_excursion': -2.00
        }
        
        metrics.record_outcome(signal_id, outcome_data)
        
        # Verify recording
        assert len(metrics.performance_history) == 1
        recorded_outcome = metrics.performance_history[0]
        
        assert recorded_outcome['signal_id'] == signal_id
        assert recorded_outcome['outcome'] == 'profit'
        assert recorded_outcome['profit_loss'] == 15.50
        assert recorded_outcome['holding_period'] == 45
        assert recorded_outcome['exit_reason'] == 'target_reached'
    
    def test_accuracy_metrics_calculation(self, epic1_config):
        """Test calculation of accuracy metrics."""
        metrics = SignalQualityMetrics(epic1_config['signal_quality'])
        
        # Create test data with known outcomes
        test_signals = [
            {'signal_type': 'BUY', 'confidence_score': 0.8},
            {'signal_type': 'BUY', 'confidence_score': 0.7},
            {'signal_type': 'SELL', 'confidence_score': 0.9},
            {'signal_type': 'BUY', 'confidence_score': 0.6},
            {'signal_type': 'SELL', 'confidence_score': 0.8}
        ]
        
        test_outcomes = [
            {'profit_loss': 10.0, 'holding_period': 30},  # Profitable BUY
            {'profit_loss': -5.0, 'holding_period': 25},  # Losing BUY (false positive)
            {'profit_loss': 8.0, 'holding_period': 40},   # Profitable SELL
            {'profit_loss': 12.0, 'holding_period': 35},  # Profitable BUY
            {'profit_loss': -3.0, 'holding_period': 20}   # Losing SELL (false negative)
        ]
        
        # Record signals and outcomes
        for i, (signal, outcome) in enumerate(zip(test_signals, test_outcomes)):
            metrics.record_signal(signal)
            metrics.record_outcome(i, outcome)
        
        # Calculate accuracy metrics
        accuracy = metrics.calculate_accuracy_metrics()
        
        # Verify calculations
        assert accuracy['total_signals'] == 5
        assert accuracy['accuracy_rate'] == 0.6  # 3 out of 5 profitable
        assert accuracy['profitable_signals'] == 3
        assert accuracy['losing_signals'] == 2
        assert accuracy['total_profit'] == 22.0  # 10 - 5 + 8 + 12 - 3
        assert accuracy['avg_profit_per_signal'] == 4.4  # 22 / 5
        
        # Check false positive rate (BUY signals that lost money)
        assert accuracy['false_positive_rate'] == 1/3  # 1 out of 3 BUY signals
    
    def test_confidence_metrics_calculation(self, epic1_config):
        """Test calculation of confidence metrics."""
        metrics = SignalQualityMetrics(epic1_config['signal_quality'])
        
        # Create signals with varying confidence and features
        test_signals = [
            {
                'confidence_score': 0.9,
                'volume_confirmed': True,
                'multi_timeframe_aligned': True,
                'dynamic_bands_used': True
            },
            {
                'confidence_score': 0.5,
                'volume_confirmed': False,
                'multi_timeframe_aligned': False,
                'dynamic_bands_used': False
            },
            {
                'confidence_score': 0.8,
                'volume_confirmed': True,
                'multi_timeframe_aligned': True,
                'dynamic_bands_used': False
            },
            {
                'confidence_score': 0.3,
                'volume_confirmed': False,
                'multi_timeframe_aligned': False,
                'dynamic_bands_used': True
            }
        ]
        
        for signal in test_signals:
            metrics.record_signal(signal)
        
        confidence = metrics.calculate_confidence_metrics()
        
        # Verify calculations
        assert confidence['avg_confidence'] == 0.625  # (0.9 + 0.5 + 0.8 + 0.3) / 4
        assert confidence['high_confidence_rate'] == 0.5  # 2 out of 4 above 0.7 threshold
        assert confidence['volume_confirmed_rate'] == 0.5  # 2 out of 4
        assert confidence['mtf_aligned_rate'] == 0.5  # 2 out of 4
        assert confidence['dynamic_bands_rate'] == 0.5  # 2 out of 4
    
    def test_quality_score_calculation(self, epic1_config):
        """Test comprehensive quality score calculation."""
        metrics = SignalQualityMetrics(epic1_config['signal_quality'])
        
        # Create high-quality signals scenario
        high_quality_signals = [
            {
                'signal_type': 'BUY',
                'confidence_score': 0.9,
                'volume_confirmed': True,
                'multi_timeframe_aligned': True,
                'dynamic_bands_used': True
            },
            {
                'signal_type': 'SELL',
                'confidence_score': 0.85,
                'volume_confirmed': True,
                'multi_timeframe_aligned': True,
                'dynamic_bands_used': True
            },
            {
                'signal_type': 'BUY',
                'confidence_score': 0.8,
                'volume_confirmed': True,
                'multi_timeframe_aligned': True,
                'dynamic_bands_used': True
            }
        ]
        
        high_quality_outcomes = [
            {'profit_loss': 15.0, 'holding_period': 30},
            {'profit_loss': 12.0, 'holding_period': 25},
            {'profit_loss': 18.0, 'holding_period': 35}
        ]
        
        # Record high-quality scenario
        for i, (signal, outcome) in enumerate(zip(high_quality_signals, high_quality_outcomes)):
            metrics.record_signal(signal)
            metrics.record_outcome(i, outcome)
        
        quality_score = metrics.calculate_quality_score()
        
        # Verify high quality score
        assert quality_score['overall_quality_score'] > 0.8
        assert quality_score['grade'] in ['A+', 'A']
        assert quality_score['accuracy_component'] > 0.35  # Should be high
        assert quality_score['enhancement_component'] > 0.12  # All Epic 1 features used
        
        # Test low-quality scenario
        metrics_low = SignalQualityMetrics(epic1_config['signal_quality'])
        
        low_quality_signals = [
            {
                'signal_type': 'BUY',
                'confidence_score': 0.3,
                'volume_confirmed': False,
                'multi_timeframe_aligned': False,
                'dynamic_bands_used': False
            },
            {
                'signal_type': 'SELL',
                'confidence_score': 0.4,
                'volume_confirmed': False,
                'multi_timeframe_aligned': False,
                'dynamic_bands_used': False
            }
        ]
        
        low_quality_outcomes = [
            {'profit_loss': -10.0, 'holding_period': 15},
            {'profit_loss': -8.0, 'holding_period': 20}
        ]
        
        for i, (signal, outcome) in enumerate(zip(low_quality_signals, low_quality_outcomes)):
            metrics_low.record_signal(signal)
            metrics_low.record_outcome(i, outcome)
        
        low_quality_score = metrics_low.calculate_quality_score()
        
        # Verify low quality score
        assert low_quality_score['overall_quality_score'] < 0.3
        assert low_quality_score['grade'] in ['D', 'F']
    
    def test_performance_analytics(self, epic1_config):
        """Test comprehensive performance analytics."""
        metrics = SignalQualityMetrics(epic1_config['signal_quality'])
        
        # Create scenario with enough data for analytics
        for i in range(50):
            signal_data = {
                'signal_type': 'BUY' if i % 2 == 0 else 'SELL',
                'confidence_score': 0.7 + (i % 10) * 0.03,  # Varying confidence
                'volume_confirmed': i % 3 == 0,  # Every 3rd signal
                'multi_timeframe_aligned': i % 4 == 0,  # Every 4th signal
                'dynamic_bands_used': i % 2 == 0  # Every other signal
            }
            
            outcome_data = {
                'profit_loss': 10.0 if i % 3 != 0 else -5.0,  # 67% accuracy
                'holding_period': 30 + (i % 20)
            }
            
            metrics.record_signal(signal_data)
            metrics.record_outcome(i, outcome_data)
        
        analytics = metrics.get_performance_analytics()
        
        # Verify analytics structure
        assert 'quality_scores' in analytics
        assert 'trend_analysis' in analytics
        assert 'feature_effectiveness' in analytics
        assert 'summary_stats' in analytics
        
        # Verify quality scores for different windows
        quality_scores = analytics['quality_scores']
        assert 'short_term' in quality_scores
        assert 'medium_term' in quality_scores
        assert 'overall' in quality_scores
        
        # Verify summary stats
        summary = analytics['summary_stats']
        assert summary['total_signals_tracked'] == 50
        assert summary['total_outcomes_recorded'] == 50
        assert summary['data_completeness'] == 1.0
    
    def test_feature_effectiveness_analysis(self, epic1_config):
        """Test analysis of Epic 1 feature effectiveness."""
        metrics = SignalQualityMetrics(epic1_config['signal_quality'])
        
        # Create scenario where volume confirmation improves results
        volume_confirmed_signals = [
            {'volume_confirmed': True, 'signal_type': 'BUY'},
            {'volume_confirmed': True, 'signal_type': 'BUY'},
            {'volume_confirmed': True, 'signal_type': 'BUY'}
        ]
        
        volume_not_confirmed_signals = [
            {'volume_confirmed': False, 'signal_type': 'BUY'},
            {'volume_confirmed': False, 'signal_type': 'BUY'}
        ]
        
        # Volume confirmed outcomes (better results)
        volume_confirmed_outcomes = [
            {'profit_loss': 15.0},
            {'profit_loss': 12.0},
            {'profit_loss': 18.0}
        ]
        
        # Not volume confirmed outcomes (worse results)
        volume_not_confirmed_outcomes = [
            {'profit_loss': -5.0},
            {'profit_loss': 3.0}
        ]
        
        # Record all signals and outcomes
        signal_id = 0
        for signal, outcome in zip(volume_confirmed_signals + volume_not_confirmed_signals,
                                 volume_confirmed_outcomes + volume_not_confirmed_outcomes):
            metrics.record_signal(signal)
            metrics.record_outcome(signal_id, outcome)
            signal_id += 1
        
        analytics = metrics.get_performance_analytics()
        feature_effectiveness = analytics['feature_effectiveness']
        
        # Verify volume confirmation effectiveness
        volume_effectiveness = feature_effectiveness['volume_confirmation']
        assert volume_effectiveness['feature_accuracy'] > volume_effectiveness['baseline_accuracy']
        assert volume_effectiveness['accuracy_improvement'] > 0
        assert volume_effectiveness['profit_improvement'] > 0
    
    def test_metrics_export(self, epic1_config):
        """Test metrics report export functionality."""
        metrics = SignalQualityMetrics(epic1_config['signal_quality'])
        
        # Add some test data
        metrics.record_signal({
            'signal_type': 'BUY',
            'confidence_score': 0.8,
            'volume_confirmed': True
        })
        metrics.record_outcome(0, {'profit_loss': 10.0})
        
        # Test JSON export
        json_report = metrics.export_metrics_report('json')
        
        # Verify report structure
        assert isinstance(json_report, str)
        report_data = json.loads(json_report)
        
        assert 'report_generated' in report_data
        assert 'epic1_signal_quality_metrics' in report_data
        assert 'configuration' in report_data
        
        # Verify configuration section
        config_section = report_data['configuration']
        assert 'confidence_threshold' in config_section
        assert 'false_positive_penalty' in config_section
        assert 'trend_alignment_bonus' in config_section
    
    def test_confidence_performance_correlation(self, epic1_config):
        """Test confidence-performance correlation calculation."""
        metrics = SignalQualityMetrics(epic1_config['signal_quality'])
        
        # Create signals with varying confidence and corresponding outcomes
        # High confidence should correlate with better outcomes
        test_data = [
            ({'confidence_score': 0.9}, {'profit_loss': 15.0}),
            ({'confidence_score': 0.8}, {'profit_loss': 10.0}),
            ({'confidence_score': 0.7}, {'profit_loss': 5.0}),
            ({'confidence_score': 0.6}, {'profit_loss': -2.0}),
            ({'confidence_score': 0.4}, {'profit_loss': -8.0}),
            ({'confidence_score': 0.3}, {'profit_loss': -12.0})
        ]
        
        for i, (signal, outcome) in enumerate(test_data):
            metrics.record_signal(signal)
            metrics.record_outcome(i, outcome)
        
        confidence_metrics = metrics.calculate_confidence_metrics()
        correlation_data = confidence_metrics['confidence_performance_correlation']
        
        # Should show positive correlation
        assert correlation_data['correlation'] > 0.5
        assert correlation_data['sample_size'] == 6
    
    @pytest.mark.parametrize("window_size", [10, 25, 50, None])
    def test_different_window_sizes(self, epic1_config, window_size):
        """Test metrics calculation with different window sizes."""
        metrics = SignalQualityMetrics(epic1_config['signal_quality'])
        
        # Create 60 signals and outcomes
        for i in range(60):
            signal_data = {
                'signal_type': 'BUY',
                'confidence_score': 0.7,
                'volume_confirmed': True
            }
            outcome_data = {
                'profit_loss': 5.0 if i % 2 == 0 else -3.0  # 50% accuracy
            }
            
            metrics.record_signal(signal_data)
            metrics.record_outcome(i, outcome_data)
        
        # Calculate metrics for specific window
        accuracy = metrics.calculate_accuracy_metrics(window_size)
        confidence = metrics.calculate_confidence_metrics(window_size)
        quality = metrics.calculate_quality_score(window_size)
        
        # Verify metrics are calculated
        if window_size is None:
            expected_signals = 60
        else:
            expected_signals = min(window_size, 60)
        
        # Window size affects the sample size used
        assert accuracy['total_signals'] <= expected_signals
        assert isinstance(confidence['avg_confidence'], float)
        assert isinstance(quality['overall_quality_score'], float)
    
    def test_insufficient_data_handling(self, epic1_config):
        """Test handling of insufficient data scenarios."""
        metrics = SignalQualityMetrics(epic1_config['signal_quality'])
        
        # Test with no data
        accuracy = metrics.calculate_accuracy_metrics()
        confidence = metrics.calculate_confidence_metrics()
        quality = metrics.calculate_quality_score()
        
        assert accuracy['total_signals'] == 0
        assert accuracy['accuracy_rate'] == 0.0
        assert confidence['avg_confidence'] == 0.0
        assert quality['overall_quality_score'] == 0.0
        assert quality['grade'] == 'N/A'
        
        # Test with signals but no outcomes
        metrics.record_signal({'signal_type': 'BUY', 'confidence_score': 0.8})
        
        accuracy_no_outcomes = metrics.calculate_accuracy_metrics()
        assert accuracy_no_outcomes['total_signals'] == 0  # No outcomes recorded
        
        confidence_with_signals = metrics.calculate_confidence_metrics()
        assert confidence_with_signals['avg_confidence'] == 0.8