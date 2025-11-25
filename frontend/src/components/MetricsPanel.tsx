import React from 'react';
import type { PortfolioMetrics } from '../types/api';

interface MetricsPanelProps {
  metrics: PortfolioMetrics;
  title?: string;
}

const MetricsPanel: React.FC<MetricsPanelProps> = ({ metrics, title = 'Métricas da Carteira' }) => {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-PT', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const getColorClass = (value: number) => {
    return value >= 0 ? 'text-green-600' : 'text-red-600';
  };

  const MetricCard = ({
    label,
    value,
    isPercentage = false,
    isCurrency = false,
    tooltip,
  }: {
    label: string;
    value: number;
    isPercentage?: boolean;
    isCurrency?: boolean;
    tooltip?: string;
  }) => (
    <div className="bg-gray-50 rounded-lg p-4" title={tooltip}>
      <div className="text-sm text-gray-600 mb-1">{label}</div>
      <div className={`text-xl font-bold ${isPercentage ? getColorClass(value) : 'text-gray-900'}`}>
        {isCurrency ? formatCurrency(value) : isPercentage ? formatPercentage(value) : value.toFixed(2)}
      </div>
    </div>
  );

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard
          label="Valor Total"
          value={metrics.total_value}
          isCurrency
          tooltip="Valor atual da carteira"
        />
        <MetricCard
          label="Total Investido"
          value={metrics.total_invested}
          isCurrency
          tooltip="Total de capital investido (inicial + contribuições)"
        />
        <MetricCard
          label="Retorno Total"
          value={metrics.total_return}
          isCurrency
          tooltip="Ganho ou perda absoluta"
        />
        <MetricCard
          label="Retorno %"
          value={metrics.return_percentage}
          isPercentage
          tooltip="Retorno em percentagem do capital investido"
        />
        <MetricCard
          label="CAGR"
          value={metrics.cagr}
          isPercentage
          tooltip="Taxa de crescimento anual composta"
        />
        <MetricCard
          label="Volatilidade"
          value={metrics.volatility}
          isPercentage
          tooltip="Volatilidade anualizada (desvio padrão dos retornos)"
        />
        <MetricCard
          label="Sharpe Ratio"
          value={metrics.sharpe_ratio}
          tooltip="Retorno ajustado ao risco (valores > 1 são bons)"
        />
        <MetricCard
          label="Sortino Ratio"
          value={metrics.sortino_ratio}
          tooltip="Retorno ajustado ao risco negativo (valores > 1 são bons)"
        />
        <MetricCard
          label="Drawdown Máximo"
          value={metrics.max_drawdown}
          isPercentage
          tooltip="Maior queda de pico a vale"
        />
        <MetricCard
          label="Melhor Mês"
          value={metrics.best_month}
          isPercentage
          tooltip="Melhor retorno mensal"
        />
        <MetricCard
          label="Pior Mês"
          value={metrics.worst_month}
          isPercentage
          tooltip="Pior retorno mensal"
        />
      </div>

      <div className="mt-4 p-4 bg-blue-50 rounded-lg">
        <h4 className="text-sm font-semibold text-blue-900 mb-2">Como interpretar estas métricas:</h4>
        <ul className="text-xs text-blue-800 space-y-1">
          <li>
            <strong>CAGR:</strong> Taxa de crescimento anual. Quanto maior, melhor.
          </li>
          <li>
            <strong>Sharpe/Sortino Ratio:</strong> Retorno ajustado ao risco. Valores &gt; 1 são bons,
            &gt; 2 são excelentes.
          </li>
          <li>
            <strong>Volatilidade:</strong> Variação dos retornos. Quanto menor, mais estável.
          </li>
          <li>
            <strong>Max Drawdown:</strong> Maior queda. Indica o pior cenário que já ocorreu.
          </li>
        </ul>
      </div>
    </div>
  );
};

export default MetricsPanel;
