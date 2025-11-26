import React from 'react';
import type { PortfolioMetrics } from '../types/api';

interface MetricsComparisonTableProps {
  metrics100PPR: PortfolioMetrics;
  metricsPPRBTC: PortfolioMetrics;
  bitcoinAllocation: number;
}

const MetricsComparisonTable: React.FC<MetricsComparisonTableProps> = ({
  metrics100PPR,
  metricsPPRBTC,
  bitcoinAllocation
}) => {
  const formatCurrency = (value: string) => {
    return new Intl.NumberFormat('pt-PT', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(Number(value));
  };

  const formatPercentage = (value: string) => {
    const num = Number(value);
    return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`;
  };

  const formatNumber = (value: string) => {
    return Number(value).toFixed(2);
  };

  const getBetterClass = (val1: string, val2: string, higherIsBetter: boolean = true) => {
    const num1 = Number(val1);
    const num2 = Number(val2);

    if (higherIsBetter) {
      if (num1 > num2) return 'bg-green-50 font-semibold text-green-700';
      if (num2 > num1) return '';
    } else {
      if (num1 < num2) return 'bg-green-50 font-semibold text-green-700';
      if (num2 < num1) return '';
    }
    return '';
  };

  const metrics = [
    {
      label: 'Valor Final',
      ppr: formatCurrency(metrics100PPR.final_value),
      btc: formatCurrency(metricsPPRBTC.final_value),
      higherIsBetter: true,
      tooltip: 'Valor da carteira no final do período',
    },
    {
      label: 'Retorno Total',
      ppr: formatCurrency(metrics100PPR.total_return),
      btc: formatCurrency(metricsPPRBTC.total_return),
      higherIsBetter: true,
      tooltip: 'Ganho ou perda absoluta em EUR',
    },
    {
      label: 'Retorno %',
      ppr: formatPercentage(metrics100PPR.total_return_percentage),
      btc: formatPercentage(metricsPPRBTC.total_return_percentage),
      higherIsBetter: true,
      tooltip: 'Retorno percentual do investimento',
    },
    {
      label: 'CAGR',
      ppr: formatPercentage(metrics100PPR.cagr),
      btc: formatPercentage(metricsPPRBTC.cagr),
      higherIsBetter: true,
      tooltip: 'Taxa de crescimento anual composta',
    },
    {
      label: 'Volatilidade',
      ppr: formatPercentage(metrics100PPR.volatility),
      btc: formatPercentage(metricsPPRBTC.volatility),
      higherIsBetter: false,
      tooltip: 'Volatilidade anualizada (menor é melhor)',
    },
    {
      label: 'Sharpe Ratio',
      ppr: formatNumber(metrics100PPR.sharpe_ratio),
      btc: formatNumber(metricsPPRBTC.sharpe_ratio),
      higherIsBetter: true,
      tooltip: 'Retorno ajustado ao risco (>1 é bom, >2 é excelente)',
    },
    {
      label: 'Sortino Ratio',
      ppr: formatNumber(metrics100PPR.sortino_ratio),
      btc: formatNumber(metricsPPRBTC.sortino_ratio),
      higherIsBetter: true,
      tooltip: 'Retorno ajustado ao risco negativo',
    },
    {
      label: 'Max Drawdown',
      ppr: formatPercentage(metrics100PPR.max_drawdown),
      btc: formatPercentage(metricsPPRBTC.max_drawdown),
      higherIsBetter: false,
      tooltip: 'Maior queda de pico a vale (mais próximo de 0 é melhor)',
    },
    {
      label: 'Melhor Mês',
      ppr: formatPercentage(metrics100PPR.best_month),
      btc: formatPercentage(metricsPPRBTC.best_month),
      higherIsBetter: true,
      tooltip: 'Melhor retorno mensal',
    },
    {
      label: 'Pior Mês',
      ppr: formatPercentage(metrics100PPR.worst_month),
      btc: formatPercentage(metricsPPRBTC.worst_month),
      higherIsBetter: false,
      tooltip: 'Pior retorno mensal (mais próximo de 0 é melhor)',
    },
  ];

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">Comparação de Métricas</h3>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b-2 border-gray-300">
              <th className="text-left py-3 px-4 font-semibold text-gray-700">Métrica</th>
              <th className="text-right py-3 px-4 font-semibold text-blue-700">100% PPR</th>
              <th className="text-right py-3 px-4 font-semibold text-orange-700">
                {100 - bitcoinAllocation}% PPR + {bitcoinAllocation}% BTC
              </th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((metric, index) => (
              <tr
                key={metric.label}
                className={`border-b border-gray-200 hover:bg-gray-50 ${
                  index % 2 === 0 ? 'bg-white' : 'bg-gray-50'
                }`}
                title={metric.tooltip}
              >
                <td className="py-3 px-4 font-medium text-gray-900">{metric.label}</td>
                <td
                  className={`py-3 px-4 text-right ${getBetterClass(
                    metric.ppr.replace(/[^0-9.-]/g, ''),
                    metric.btc.replace(/[^0-9.-]/g, ''),
                    metric.higherIsBetter
                  )}`}
                >
                  {metric.ppr}
                </td>
                <td
                  className={`py-3 px-4 text-right ${getBetterClass(
                    metric.btc.replace(/[^0-9.-]/g, ''),
                    metric.ppr.replace(/[^0-9.-]/g, ''),
                    metric.higherIsBetter
                  )}`}
                >
                  {metric.btc}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 p-4 bg-blue-50 rounded-lg">
        <h4 className="text-sm font-semibold text-blue-900 mb-2">
          💡 Como interpretar:
        </h4>
        <ul className="text-xs text-blue-800 space-y-1">
          <li>
            <strong>Valores em verde</strong> indicam o melhor desempenho naquela métrica
          </li>
          <li>
            <strong>CAGR:</strong> Taxa de crescimento anual. Quanto maior, melhor.
          </li>
          <li>
            <strong>Sharpe/Sortino:</strong> Retorno ajustado ao risco. Valores &gt; 1 são bons, &gt; 2 são excelentes.
          </li>
          <li>
            <strong>Volatilidade:</strong> Variação dos retornos. Quanto menor, mais estável.
          </li>
          <li>
            <strong>Max Drawdown:</strong> Maior queda. Indica o pior cenário que ocorreu.
          </li>
        </ul>
      </div>
    </div>
  );
};

export default MetricsComparisonTable;
