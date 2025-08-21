"""
Unit Tests for Multi-Timeframe Validation Logic

Tests the multi-timeframe signal validation system that confirms signals across:
- Different timeframe combinations (1Min, 5Min, 15Min, 1Hour)
- Signal alignment and consensus mechanisms
- Timeframe weight and priority systems
- Conflict resolution between timeframes
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import os
from typing import Dict, List, Tuple, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from indicators.stoch_rsi_enhanced import StochRSIIndicator
from tests.epic1_signal_quality.test_config import get_epic1_test_config


class MultiTimeframeValidator:
    """Enhanced multi-timeframe signal validation system."""
    
    def __init__(self, config: dict):
        self.primary_timeframe = config.get('primary_timeframe', '5Min')
        self.confirmation_timeframes = config.get('confirmation_timeframes', ['15Min', '1Hour'])
        self.signal_alignment_required = config.get('signal_alignment_required', True)
        self.min_confirmation_percentage = config.get('min_confirmation_percentage', 60)
        
        # Timeframe weights for consensus calculation
        self.timeframe_weights = {
            '1Min': 0.1,
            '5Min': 0.3,
            '15Min': 0.35,
            '1Hour': 0.25
        }
        
        # Signal strength decay factors by timeframe
        self.decay_factors = {
            '1Min': 0.95,   # Fast decay
            '5Min': 0.85,   # Moderate decay
            '15Min': 0.75,  # Slower decay
            '1Hour': 0.65   # Slowest decay
        }
    
    def calculate_timeframe_signals(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, Dict]:
        """Calculate StochRSI signals for all timeframes."""
        timeframe_signals = {}
        
        for timeframe, data in data_dict.items():
            if len(data) < 50:  # Minimum data requirement
                continue
                
            try:
                indicator = StochRSIIndicator(
                    rsi_length=14,
                    stoch_length=14,
                    k_smoothing=3,
                    d_smoothing=3
                )
                
                # Calculate indicators
                indicators = indicator.calculate_full_stoch_rsi(data['close'])
                signals = indicator.generate_signals(
                    indicators['StochRSI_K'], 
                    indicators['StochRSI_D']
                )
                
                # Get current values
                current_signal = signals['signals'].iloc[-1] if len(signals['signals']) > 0 else 0
                current_strength = signals['signal_strength'].iloc[-1] if len(signals['signal_strength']) > 0 else 0
                current_k = indicators['StochRSI_K'].iloc[-1] if len(indicators['StochRSI_K']) > 0 else 50
                current_d = indicators['StochRSI_D'].iloc[-1] if len(indicators['StochRSI_D']) > 0 else 50
                
                timeframe_signals[timeframe] = {
                    'signal': current_signal,
                    'strength': current_strength,
                    'stoch_k': current_k,
                    'stoch_d': current_d,
                    'indicators': indicators,
                    'signals': signals,
                    'timestamp': data.index[-1]
                }
                
            except Exception as e:
                timeframe_signals[timeframe] = {
                    'signal': 0,
                    'strength': 0,
                    'stoch_k': 50,
                    'stoch_d': 50,
                    'error': str(e),
                    'timestamp': data.index[-1] if len(data) > 0 else datetime.now()
                }
        
        return timeframe_signals
    
    def validate_signal_alignment(self, timeframe_signals: Dict[str, Dict]) -> Dict:
        """Validate signal alignment across timeframes."""
        if self.primary_timeframe not in timeframe_signals:
            return {
                'aligned': False,
                'primary_signal': 0,
                'confirmation_signals': {},
                'alignment_score': 0.0,
                'reason': f'Primary timeframe {self.primary_timeframe} not available'
            }
        
        primary_signal = timeframe_signals[self.primary_timeframe]['signal']
        
        if primary_signal == 0:  # No primary signal
            return {
                'aligned': False,
                'primary_signal': 0,
                'confirmation_signals': {},
                'alignment_score': 0.0,
                'reason': 'No primary signal detected'
            }
        
        confirmation_signals = {}
        aligned_confirmations = 0
        total_confirmations = 0
        
        for timeframe in self.confirmation_timeframes:
            if timeframe in timeframe_signals:
                confirmation_signal = timeframe_signals[timeframe]['signal']
                confirmation_signals[timeframe] = confirmation_signal
                total_confirmations += 1
                
                # Check alignment
                if (primary_signal > 0 and confirmation_signal > 0) or \
                   (primary_signal < 0 and confirmation_signal < 0):
                    aligned_confirmations += 1
        
        if total_confirmations == 0:
            alignment_score = 0.5  # Neutral when no confirmations available
            aligned = False
            reason = 'No confirmation timeframes available'
        else:
            alignment_score = aligned_confirmations / total_confirmations
            aligned = alignment_score >= (self.min_confirmation_percentage / 100)
            reason = f'{aligned_confirmations}/{total_confirmations} timeframes aligned'
        
        return {
            'aligned': aligned,
            'primary_signal': primary_signal,
            'confirmation_signals': confirmation_signals,
            'alignment_score': alignment_score,
            'aligned_confirmations': aligned_confirmations,
            'total_confirmations': total_confirmations,
            'reason': reason
        }
    
    def calculate_consensus_signal(self, timeframe_signals: Dict[str, Dict]) -> Dict:
        """Calculate weighted consensus signal across timeframes."""
        weighted_signal = 0.0
        total_weight = 0.0
        timeframe_contributions = {}
        
        for timeframe, signal_data in timeframe_signals.items():
            if timeframe in self.timeframe_weights:
                weight = self.timeframe_weights[timeframe]
                signal = signal_data['signal']
                strength = signal_data.get('strength', 0)
                
                # Apply decay factor based on signal age (simplified)
                decay = self.decay_factors.get(timeframe, 0.8)
                adjusted_strength = strength * decay
                
                contribution = signal * adjusted_strength * weight
                weighted_signal += contribution
                total_weight += weight
                
                timeframe_contributions[timeframe] = {
                    'signal': signal,
                    'strength': strength,
                    'weight': weight,
                    'contribution': contribution,
                    'adjusted_strength': adjusted_strength
                }
        
        if total_weight == 0:
            consensus_signal = 0
            consensus_strength = 0
        else:
            consensus_signal = 1 if weighted_signal > 0.1 else (-1 if weighted_signal < -0.1 else 0)
            consensus_strength = abs(weighted_signal) / total_weight
        
        return {
            'consensus_signal': consensus_signal,
            'consensus_strength': consensus_strength,
            'weighted_score': weighted_signal,
            'total_weight': total_weight,
            'timeframe_contributions': timeframe_contributions
        }
    
    def detect_timeframe_conflicts(self, timeframe_signals: Dict[str, Dict]) -> Dict:
        """Detect and analyze conflicts between timeframes."""
        signals = {tf: data['signal'] for tf, data in timeframe_signals.items() if data['signal'] != 0}
        
        if len(signals) <= 1:
            return {
                'has_conflicts': False,
                'conflict_count': 0,
                'conflicting_timeframes': [],
                'conflict_severity': 0.0
            }
        
        # Check for opposing signals
        buy_signals = [tf for tf, signal in signals.items() if signal > 0]
        sell_signals = [tf for tf, signal in signals.items() if signal < 0]
        
        has_conflicts = len(buy_signals) > 0 and len(sell_signals) > 0
        
        if has_conflicts:
            # Calculate conflict severity based on signal strengths and timeframe weights
            buy_weight = sum(self.timeframe_weights.get(tf, 0.1) * 
                           timeframe_signals[tf].get('strength', 0) for tf in buy_signals)
            sell_weight = sum(self.timeframe_weights.get(tf, 0.1) * 
                            timeframe_signals[tf].get('strength', 0) for tf in sell_signals)
            
            total_weight = buy_weight + sell_weight
            conflict_severity = min(buy_weight, sell_weight) / total_weight if total_weight > 0 else 0
            
            conflicting_timeframes = buy_signals + sell_signals
        else:
            conflict_severity = 0.0
            conflicting_timeframes = []
        
        return {
            'has_conflicts': has_conflicts,
            'conflict_count': len(buy_signals) + len(sell_signals) if has_conflicts else 0,
            'conflicting_timeframes': conflicting_timeframes,
            'conflict_severity': conflict_severity,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals
        }
    
    def resolve_conflicts(self, timeframe_signals: Dict[str, Dict], conflict_info: Dict) -> Dict:
        """Resolve conflicts between timeframes using priority rules."""
        if not conflict_info['has_conflicts']:
            return {
                'resolution_method': 'no_conflict',
                'resolved_signal': 0,
                'confidence': 1.0,
                'reason': 'No conflicts detected'
            }
        
        # Method 1: Primary timeframe override
        if self.primary_timeframe in timeframe_signals:
            primary_signal = timeframe_signals[self.primary_timeframe]['signal']
            if primary_signal != 0:
                return {
                    'resolution_method': 'primary_override',
                    'resolved_signal': primary_signal,
                    'confidence': 0.7,
                    'reason': f'Primary timeframe {self.primary_timeframe} takes precedence'
                }
        
        # Method 2: Weighted consensus with minimum threshold
        consensus = self.calculate_consensus_signal(timeframe_signals)
        if abs(consensus['weighted_score']) > 0.2:  # Strong enough consensus
            return {
                'resolution_method': 'weighted_consensus',
                'resolved_signal': consensus['consensus_signal'],
                'confidence': min(0.9, consensus['consensus_strength']),
                'reason': f'Weighted consensus: {consensus["weighted_score"]:.3f}'
            }
        
        # Method 3: Higher timeframe priority
        higher_timeframes = ['1Hour', '15Min', '5Min', '1Min']
        for timeframe in higher_timeframes:
            if timeframe in timeframe_signals and timeframe_signals[timeframe]['signal'] != 0:
                signal_strength = timeframe_signals[timeframe].get('strength', 0)
                if signal_strength > 0.3:  # Minimum strength requirement
                    return {
                        'resolution_method': 'higher_timeframe_priority',
                        'resolved_signal': timeframe_signals[timeframe]['signal'],
                        'confidence': 0.6,
                        'reason': f'Higher timeframe {timeframe} priority'
                    }
        
        # Method 4: No resolution possible
        return {
            'resolution_method': 'no_resolution',
            'resolved_signal': 0,
            'confidence': 0.0,
            'reason': 'Conflicting signals cannot be resolved'
        }
    
    def validate_multi_timeframe_signal(self, data_dict: Dict[str, pd.DataFrame]) -> Dict:
        """Complete multi-timeframe signal validation."""
        # Calculate signals for all timeframes
        timeframe_signals = self.calculate_timeframe_signals(data_dict)
        
        # Check signal alignment
        alignment_result = self.validate_signal_alignment(timeframe_signals)
        
        # Calculate consensus
        consensus_result = self.calculate_consensus_signal(timeframe_signals)
        
        # Detect conflicts
        conflict_info = self.detect_timeframe_conflicts(timeframe_signals)
        
        # Resolve conflicts if any
        resolution_result = self.resolve_conflicts(timeframe_signals, conflict_info)
        
        # Calculate overall confidence
        confidence_factors = []
        
        if alignment_result['aligned']:
            confidence_factors.append(alignment_result['alignment_score'])
        else:
            confidence_factors.append(0.3)  # Penalty for misalignment
        
        if consensus_result['consensus_strength'] > 0:
            confidence_factors.append(consensus_result['consensus_strength'])
        
        if not conflict_info['has_conflicts']:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(max(0.2, 1.0 - conflict_info['conflict_severity']))
        
        overall_confidence = np.mean(confidence_factors) if confidence_factors else 0.0
        
        # Determine final signal
        if self.signal_alignment_required and not alignment_result['aligned']:
            final_signal = 0
            final_reason = 'Signal alignment required but not achieved'
        elif conflict_info['has_conflicts'] and resolution_result['resolution_method'] == 'no_resolution':
            final_signal = 0
            final_reason = 'Unresolvable conflicts between timeframes'
        else:
            final_signal = resolution_result.get('resolved_signal', alignment_result['primary_signal'])
            final_reason = resolution_result.get('reason', 'Multi-timeframe validation passed')
        
        return {
            'validated': final_signal != 0,
            'final_signal': final_signal,
            'confidence': overall_confidence,
            'reason': final_reason,
            'timeframe_signals': timeframe_signals,
            'alignment_result': alignment_result,
            'consensus_result': consensus_result,
            'conflict_info': conflict_info,
            'resolution_result': resolution_result,
            'validation_timestamp': datetime.now()
        }


class TestMultiTimeframeValidation:
    """Test suite for multi-timeframe validation functionality."""
    
    def test_basic_timeframe_signal_calculation(self, epic1_config, multi_timeframe_data):
        """Test basic signal calculation across timeframes."""
        validator = MultiTimeframeValidator(epic1_config['multi_timeframe'])
        
        timeframe_signals = validator.calculate_timeframe_signals(multi_timeframe_data)
        
        # Should have signals for all provided timeframes
        expected_timeframes = ['1Min', '5Min', '15Min', '1Hour']
        for timeframe in expected_timeframes:
            assert timeframe in timeframe_signals
            
            signal_data = timeframe_signals[timeframe]
            assert 'signal' in signal_data
            assert 'strength' in signal_data
            assert 'stoch_k' in signal_data
            assert 'stoch_d' in signal_data
            assert 'timestamp' in signal_data
            
            # Validate signal values
            assert signal_data['signal'] in [-1, 0, 1]
            assert 0 <= signal_data['strength'] <= 1
            assert 0 <= signal_data['stoch_k'] <= 100
            assert 0 <= signal_data['stoch_d'] <= 100
    
    def test_signal_alignment_validation_aligned(self, epic1_config):
        """Test signal alignment when timeframes are aligned."""
        validator = MultiTimeframeValidator(epic1_config['multi_timeframe'])
        
        # Create aligned signals (all buy)
        timeframe_signals = {
            '5Min': {'signal': 1, 'strength': 0.8, 'stoch_k': 15, 'stoch_d': 18},
            '15Min': {'signal': 1, 'strength': 0.7, 'stoch_k': 18, 'stoch_d': 20},
            '1Hour': {'signal': 1, 'strength': 0.6, 'stoch_k': 22, 'stoch_d': 25}
        }
        
        alignment_result = validator.validate_signal_alignment(timeframe_signals)
        
        assert alignment_result['aligned'] == True
        assert alignment_result['primary_signal'] == 1
        assert alignment_result['alignment_score'] == 1.0
        assert alignment_result['aligned_confirmations'] == 2
        assert alignment_result['total_confirmations'] == 2
    
    def test_signal_alignment_validation_misaligned(self, epic1_config):
        """Test signal alignment when timeframes are misaligned."""
        validator = MultiTimeframeValidator(epic1_config['multi_timeframe'])
        
        # Create misaligned signals (primary buy, confirmations sell)
        timeframe_signals = {
            '5Min': {'signal': 1, 'strength': 0.8, 'stoch_k': 15, 'stoch_d': 18},
            '15Min': {'signal': -1, 'strength': 0.7, 'stoch_k': 85, 'stoch_d': 82},
            '1Hour': {'signal': -1, 'strength': 0.6, 'stoch_k': 88, 'stoch_d': 85}
        }
        
        alignment_result = validator.validate_signal_alignment(timeframe_signals)
        
        assert alignment_result['aligned'] == False
        assert alignment_result['primary_signal'] == 1
        assert alignment_result['alignment_score'] == 0.0
        assert alignment_result['aligned_confirmations'] == 0
        assert alignment_result['total_confirmations'] == 2
    
    def test_signal_alignment_partial(self, epic1_config):
        """Test signal alignment with partial confirmation."""
        validator = MultiTimeframeValidator(epic1_config['multi_timeframe'])
        
        # Partial alignment (60% threshold, 1 of 2 confirmations)
        timeframe_signals = {
            '5Min': {'signal': 1, 'strength': 0.8, 'stoch_k': 15, 'stoch_d': 18},
            '15Min': {'signal': 1, 'strength': 0.7, 'stoch_k': 18, 'stoch_d': 20},
            '1Hour': {'signal': -1, 'strength': 0.6, 'stoch_k': 85, 'stoch_d': 82}
        }
        
        alignment_result = validator.validate_signal_alignment(timeframe_signals)
        
        # 50% alignment (1/2) should fail 60% threshold
        assert alignment_result['aligned'] == False
        assert alignment_result['alignment_score'] == 0.5
    
    def test_weighted_consensus_calculation(self, epic1_config):
        """Test weighted consensus signal calculation."""
        validator = MultiTimeframeValidator(epic1_config['multi_timeframe'])
        
        # Strong consensus (all buy signals with varying strengths)
        timeframe_signals = {
            '1Min': {'signal': 1, 'strength': 0.6},
            '5Min': {'signal': 1, 'strength': 0.8},
            '15Min': {'signal': 1, 'strength': 0.9},
            '1Hour': {'signal': 1, 'strength': 0.7}
        }
        
        consensus_result = validator.calculate_consensus_signal(timeframe_signals)
        
        assert consensus_result['consensus_signal'] == 1
        assert consensus_result['consensus_strength'] > 0.6
        assert consensus_result['weighted_score'] > 0.1
        assert len(consensus_result['timeframe_contributions']) == 4
        
        # Check individual contributions
        for timeframe in timeframe_signals.keys():
            assert timeframe in consensus_result['timeframe_contributions']
            contribution = consensus_result['timeframe_contributions'][timeframe]
            assert 'signal' in contribution
            assert 'strength' in contribution
            assert 'weight' in contribution
            assert 'contribution' in contribution
    
    def test_consensus_with_mixed_signals(self, epic1_config):
        """Test consensus calculation with mixed signals."""
        validator = MultiTimeframeValidator(epic1_config['multi_timeframe'])
        
        # Mixed signals with different weights
        timeframe_signals = {
            '1Min': {'signal': 1, 'strength': 0.5},    # Low weight
            '5Min': {'signal': -1, 'strength': 0.8},   # Medium weight
            '15Min': {'signal': 1, 'strength': 0.9},   # High weight
            '1Hour': {'signal': 1, 'strength': 0.7}    # Medium-high weight
        }
        
        consensus_result = validator.calculate_consensus_signal(timeframe_signals)
        
        # Higher timeframes (15Min + 1Hour) should dominate
        assert consensus_result['consensus_signal'] == 1
        assert consensus_result['weighted_score'] > 0
    
    def test_conflict_detection_no_conflicts(self, epic1_config):
        """Test conflict detection when no conflicts exist."""
        validator = MultiTimeframeValidator(epic1_config['multi_timeframe'])
        
        # All signals aligned
        timeframe_signals = {
            '5Min': {'signal': 1, 'strength': 0.8},
            '15Min': {'signal': 1, 'strength': 0.7},
            '1Hour': {'signal': 1, 'strength': 0.6}
        }
        
        conflict_info = validator.detect_timeframe_conflicts(timeframe_signals)
        
        assert conflict_info['has_conflicts'] == False
        assert conflict_info['conflict_count'] == 0
        assert len(conflict_info['conflicting_timeframes']) == 0
        assert conflict_info['conflict_severity'] == 0.0
    
    def test_conflict_detection_with_conflicts(self, epic1_config):
        """Test conflict detection when conflicts exist."""
        validator = MultiTimeframeValidator(epic1_config['multi_timeframe'])
        
        # Conflicting signals
        timeframe_signals = {
            '5Min': {'signal': 1, 'strength': 0.8},
            '15Min': {'signal': -1, 'strength': 0.7},
            '1Hour': {'signal': 1, 'strength': 0.6}
        }
        
        conflict_info = validator.detect_timeframe_conflicts(timeframe_signals)
        
        assert conflict_info['has_conflicts'] == True
        assert conflict_info['conflict_count'] == 3
        assert len(conflict_info['conflicting_timeframes']) == 3
        assert conflict_info['conflict_severity'] > 0
        assert '15Min' in conflict_info['sell_signals']
        assert '5Min' in conflict_info['buy_signals']
        assert '1Hour' in conflict_info['buy_signals']
    
    def test_conflict_resolution_primary_override(self, epic1_config):
        """Test conflict resolution using primary timeframe override."""
        validator = MultiTimeframeValidator(epic1_config['multi_timeframe'])
        
        timeframe_signals = {
            '5Min': {'signal': 1, 'strength': 0.8},     # Primary timeframe
            '15Min': {'signal': -1, 'strength': 0.7},   # Conflicting
            '1Hour': {'signal': -1, 'strength': 0.6}    # Conflicting
        }
        
        conflict_info = validator.detect_timeframe_conflicts(timeframe_signals)
        resolution_result = validator.resolve_conflicts(timeframe_signals, conflict_info)
        
        assert resolution_result['resolution_method'] == 'primary_override'
        assert resolution_result['resolved_signal'] == 1
        assert resolution_result['confidence'] == 0.7
    
    def test_conflict_resolution_weighted_consensus(self, epic1_config):
        """Test conflict resolution using weighted consensus."""
        validator = MultiTimeframeValidator(epic1_config['multi_timeframe'])
        
        # No primary signal, but strong consensus from other timeframes
        timeframe_signals = {
            '5Min': {'signal': 0, 'strength': 0.0},     # No primary signal
            '15Min': {'signal': 1, 'strength': 0.9},    # Strong signal
            '1Hour': {'signal': 1, 'strength': 0.8}     # Strong signal
        }
        
        conflict_info = validator.detect_timeframe_conflicts(timeframe_signals)
        resolution_result = validator.resolve_conflicts(timeframe_signals, conflict_info)
        
        assert resolution_result['resolution_method'] in ['weighted_consensus', 'higher_timeframe_priority']
        assert resolution_result['resolved_signal'] == 1
    
    def test_conflict_resolution_no_resolution(self, epic1_config):
        """Test conflict resolution when no resolution is possible."""
        validator = MultiTimeframeValidator(epic1_config['multi_timeframe'])
        
        # Weak conflicting signals with no clear winner
        timeframe_signals = {
            '5Min': {'signal': 0, 'strength': 0.0},     # No primary signal
            '15Min': {'signal': 1, 'strength': 0.2},    # Weak signal
            '1Hour': {'signal': -1, 'strength': 0.2}    # Weak opposing signal
        }
        
        conflict_info = validator.detect_timeframe_conflicts(timeframe_signals)
        resolution_result = validator.resolve_conflicts(timeframe_signals, conflict_info)
        
        assert resolution_result['resolution_method'] == 'no_resolution'
        assert resolution_result['resolved_signal'] == 0
        assert resolution_result['confidence'] == 0.0
    
    def test_complete_multi_timeframe_validation_success(self, epic1_config, multi_timeframe_data):
        """Test complete multi-timeframe validation with successful outcome."""
        validator = MultiTimeframeValidator(epic1_config['multi_timeframe'])
        
        validation_result = validator.validate_multi_timeframe_signal(multi_timeframe_data)
        
        # Verify structure
        assert 'validated' in validation_result
        assert 'final_signal' in validation_result
        assert 'confidence' in validation_result
        assert 'reason' in validation_result
        assert 'timeframe_signals' in validation_result
        assert 'alignment_result' in validation_result
        assert 'consensus_result' in validation_result
        assert 'conflict_info' in validation_result
        assert 'resolution_result' in validation_result
        assert 'validation_timestamp' in validation_result
        
        # Verify data types
        assert isinstance(validation_result['validated'], bool)
        assert validation_result['final_signal'] in [-1, 0, 1]
        assert 0.0 <= validation_result['confidence'] <= 1.0
        assert isinstance(validation_result['reason'], str)
    
    def test_insufficient_data_handling(self, epic1_config):
        """Test handling of insufficient data across timeframes."""
        validator = MultiTimeframeValidator(epic1_config['multi_timeframe'])
        
        # Create minimal data sets
        minimal_data = {
            '5Min': pd.DataFrame({
                'open': [150, 151, 149],
                'high': [151, 152, 150],
                'low': [149, 150, 148],
                'close': [150, 151, 149],
                'volume': [1000, 1100, 900]
            }, index=pd.date_range('2024-01-01', periods=3, freq='5min')),
            '15Min': pd.DataFrame({
                'open': [150],
                'high': [151],
                'low': [149],
                'close': [150],
                'volume': [1000]
            }, index=pd.date_range('2024-01-01', periods=1, freq='15min'))
        }
        
        validation_result = validator.validate_multi_timeframe_signal(minimal_data)
        
        # Should handle gracefully
        assert isinstance(validation_result, dict)
        assert 'validated' in validation_result
        # Likely to be invalid due to insufficient data
        assert validation_result['validated'] == False or validation_result['final_signal'] == 0
    
    def test_missing_primary_timeframe(self, epic1_config):
        """Test behavior when primary timeframe is missing."""
        validator = MultiTimeframeValidator(epic1_config['multi_timeframe'])
        
        # Data without primary timeframe (5Min)
        data_without_primary = {
            '15Min': pd.DataFrame({
                'open': [150] * 100,
                'high': [151] * 100,
                'low': [149] * 100,
                'close': [150] * 100,
                'volume': [1000] * 100
            }, index=pd.date_range('2024-01-01', periods=100, freq='15min')),
            '1Hour': pd.DataFrame({
                'open': [150] * 50,
                'high': [151] * 50,
                'low': [149] * 50,
                'close': [150] * 50,
                'volume': [4000] * 50
            }, index=pd.date_range('2024-01-01', periods=50, freq='1h'))
        }
        
        validation_result = validator.validate_multi_timeframe_signal(data_without_primary)
        
        # Should handle missing primary timeframe
        assert 'alignment_result' in validation_result
        assert not validation_result['alignment_result']['aligned']
        assert 'Primary timeframe' in validation_result['alignment_result']['reason']
    
    def test_timeframe_weight_configuration(self, epic1_config):
        """Test different timeframe weight configurations."""
        # Custom weights favoring higher timeframes
        custom_config = epic1_config['multi_timeframe'].copy()
        validator = MultiTimeframeValidator(custom_config)
        
        # Override weights to favor higher timeframes
        validator.timeframe_weights = {
            '1Min': 0.05,
            '5Min': 0.15,
            '15Min': 0.35,
            '1Hour': 0.45
        }
        
        timeframe_signals = {
            '1Min': {'signal': -1, 'strength': 0.9},    # Strong opposite signal
            '5Min': {'signal': -1, 'strength': 0.8},    # Strong opposite signal
            '15Min': {'signal': 1, 'strength': 0.6},    # Moderate signal
            '1Hour': {'signal': 1, 'strength': 0.7}     # Strong signal
        }
        
        consensus_result = validator.calculate_consensus_signal(timeframe_signals)
        
        # Higher timeframes should dominate despite lower individual strengths
        assert consensus_result['consensus_signal'] == 1
        
        # Verify weight application
        contributions = consensus_result['timeframe_contributions']
        hour_contribution = abs(contributions['1Hour']['contribution'])
        min_contribution = abs(contributions['1Min']['contribution'])
        assert hour_contribution > min_contribution
    
    def test_signal_decay_factors(self, epic1_config):
        """Test signal strength decay factors by timeframe."""
        validator = MultiTimeframeValidator(epic1_config['multi_timeframe'])
        
        timeframe_signals = {
            '1Min': {'signal': 1, 'strength': 1.0},
            '5Min': {'signal': 1, 'strength': 1.0},
            '15Min': {'signal': 1, 'strength': 1.0},
            '1Hour': {'signal': 1, 'strength': 1.0}
        }
        
        consensus_result = validator.calculate_consensus_signal(timeframe_signals)
        contributions = consensus_result['timeframe_contributions']
        
        # Verify decay factors are applied
        for timeframe in timeframe_signals.keys():
            expected_decay = validator.decay_factors[timeframe]
            actual_adjusted = contributions[timeframe]['adjusted_strength']
            assert abs(actual_adjusted - expected_decay) < 0.01
    
    @pytest.mark.parametrize("min_confirmation_percentage", [40, 60, 80])
    def test_different_confirmation_thresholds(self, epic1_config, min_confirmation_percentage):
        """Test different minimum confirmation percentage thresholds."""
        config = epic1_config['multi_timeframe'].copy()
        config['min_confirmation_percentage'] = min_confirmation_percentage
        validator = MultiTimeframeValidator(config)
        
        # 50% confirmation scenario (1 out of 2 confirmations)
        timeframe_signals = {
            '5Min': {'signal': 1, 'strength': 0.8},     # Primary
            '15Min': {'signal': 1, 'strength': 0.7},    # Confirming
            '1Hour': {'signal': -1, 'strength': 0.6}    # Conflicting
        }
        
        alignment_result = validator.validate_signal_alignment(timeframe_signals)
        
        # Should pass for 40%, fail for 60% and 80%
        if min_confirmation_percentage <= 50:
            assert alignment_result['aligned'] == True
        else:
            assert alignment_result['aligned'] == False
    
    def test_validation_performance(self, epic1_config, multi_timeframe_data):
        """Test performance of multi-timeframe validation."""
        import time
        
        validator = MultiTimeframeValidator(epic1_config['multi_timeframe'])
        
        # Performance test
        start_time = time.time()
        iterations = 100
        
        for _ in range(iterations):
            validation_result = validator.validate_multi_timeframe_signal(multi_timeframe_data)
        
        elapsed_time = time.time() - start_time
        avg_time = elapsed_time / iterations
        
        # Should be reasonably fast (< 10ms per validation)
        assert avg_time < 0.01, f"Multi-timeframe validation too slow: {avg_time:.4f}s per validation"
    
    def test_real_time_signal_updates(self, epic1_config):
        """Test handling of real-time signal updates across timeframes."""
        validator = MultiTimeframeValidator(epic1_config['multi_timeframe'])
        
        # Simulate real-time updates with different timestamps
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        
        timeframe_signals = {
            '1Min': {
                'signal': 1, 
                'strength': 0.8,
                'timestamp': base_time,
                'stoch_k': 15,
                'stoch_d': 18
            },
            '5Min': {
                'signal': 1, 
                'strength': 0.7,
                'timestamp': base_time - timedelta(minutes=2),  # Slightly older
                'stoch_k': 18,
                'stoch_d': 20
            },
            '15Min': {
                'signal': 0, 
                'strength': 0.0,
                'timestamp': base_time - timedelta(minutes=10),  # Much older
                'stoch_k': 50,
                'stoch_d': 52
            }
        }
        
        # Validation should handle different update frequencies
        alignment_result = validator.validate_signal_alignment(timeframe_signals)
        
        # Should be able to process despite timing differences
        assert isinstance(alignment_result['aligned'], bool)
        assert 'reason' in alignment_result