import React from 'react';
import { usePositions } from '../../hooks/usePositions';
import { ExportManager } from '../../utils/export';
import { PortfolioSummary } from './PortfolioSummary';
import { PositionsTable } from './PositionsTable';
import { ExportData } from '../../types/position';

interface PositionsDashboardProps {
  wsUrl?: string;
  className?: string;
}

export const PositionsDashboard: React.FC<PositionsDashboardProps> = ({
  wsUrl,
  className = ''
}) => {
  const {
    positions,
    portfolio,
    sortConfig,
    isConnected,
    lastUpdate,
    setSortConfig,
    refreshData
  } = usePositions(wsUrl);

  const handleExport = () => {
    if (!portfolio) return;

    const exportData: ExportData = {
      positions,
      portfolio,
      exportDate: new Date().toISOString().split('T')[0]
    };

    ExportManager.exportToCSV(exportData);
  };

  return (
    <div className={`space-y-6 ${className}`}>
      <PortfolioSummary 
        portfolio={portfolio}
        isConnected={isConnected}
        lastUpdate={lastUpdate}
      />
      
      <PositionsTable
        positions={positions}
        sortConfig={sortConfig}
        onSort={setSortConfig}
        onExport={handleExport}
      />
    </div>
  );
};