import React from 'react';

interface InvestmentInputsProps {
  initialInvestment: number;
  monthlyContribution: number;
  rebalancingFrequency: 'none' | 'monthly' | 'quarterly' | 'yearly';
  onInitialInvestmentChange: (value: number) => void;
  onMonthlyContributionChange: (value: number) => void;
  onRebalancingFrequencyChange: (value: 'none' | 'monthly' | 'quarterly' | 'yearly') => void;
}

const InvestmentInputs: React.FC<InvestmentInputsProps> = ({
  initialInvestment,
  monthlyContribution,
  rebalancingFrequency,
  onInitialInvestmentChange,
  onMonthlyContributionChange,
  onRebalancingFrequencyChange,
}) => {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-PT', {
      style: 'currency',
      currency: 'EUR',
    }).format(value);
  };

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">Parâmetros de Investimento</h3>

      <div className="space-y-4">
        <div>
          <label className="label">
            Investimento Inicial: {formatCurrency(initialInvestment)}
          </label>
          <input
            type="range"
            min="1000"
            max="50000"
            step="1000"
            value={initialInvestment}
            onChange={(e) => onInitialInvestmentChange(parseFloat(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-bitcoin-500"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>1.000€</span>
            <span>50.000€</span>
          </div>
        </div>

        <div>
          <label className="label">
            Contribuição Mensal: {formatCurrency(monthlyContribution)}
          </label>
          <input
            type="range"
            min="0"
            max="2000"
            step="50"
            value={monthlyContribution}
            onChange={(e) => onMonthlyContributionChange(parseFloat(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-bitcoin-500"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>0€</span>
            <span>2.000€</span>
          </div>
        </div>

        <div>
          <label className="label">Frequência de Rebalanceamento</label>
          <select
            value={rebalancingFrequency}
            onChange={(e) =>
              onRebalancingFrequencyChange(
                e.target.value as 'none' | 'monthly' | 'quarterly' | 'yearly'
              )
            }
            className="input-field"
          >
            <option value="none">Sem Rebalanceamento</option>
            <option value="monthly">Mensal</option>
            <option value="quarterly">Trimestral</option>
            <option value="yearly">Anual</option>
          </select>
          <p className="text-xs text-gray-500 mt-1">
            Rebalancear mantém a alocação alvo ajustando periodicamente a distribuição entre PPR e Bitcoin.
          </p>
        </div>

        <div className="bg-gray-50 p-3 rounded-lg">
          <div className="text-sm text-gray-600">Resumo</div>
          <div className="mt-2 space-y-1 text-sm">
            <div className="flex justify-between">
              <span>Inicial:</span>
              <span className="font-semibold">{formatCurrency(initialInvestment)}</span>
            </div>
            <div className="flex justify-between">
              <span>Mensal:</span>
              <span className="font-semibold">{formatCurrency(monthlyContribution)}</span>
            </div>
            <div className="flex justify-between">
              <span>Anual (contribuições):</span>
              <span className="font-semibold">
                {formatCurrency(monthlyContribution * 12)}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InvestmentInputs;
