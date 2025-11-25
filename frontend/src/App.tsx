import { useState } from 'react';
import { format, subYears } from 'date-fns';
import DisclaimerBanner from './components/DisclaimerBanner';
import PPRSelector from './components/PPRSelector';
import BitcoinSlider from './components/BitcoinSlider';
import PeriodSelector from './components/PeriodSelector';
import InvestmentInputs from './components/InvestmentInputs';
import PortfolioChart from './components/PortfolioChart';
import MetricsPanel from './components/MetricsPanel';
import { calculatePortfolio } from './api/client';
import type { PortfolioResponse } from './types/api';

function App() {
  // Portfolio configuration state
  const [selectedPPRIds, setSelectedPPRIds] = useState<string[]>([]);
  const [bitcoinAllocation, setBitcoinAllocation] = useState(10);
  const [initialInvestment, setInitialInvestment] = useState(10000);
  const [monthlyContribution, setMonthlyContribution] = useState(200);
  const [rebalancingFrequency, setRebalancingFrequency] = useState<
    'none' | 'monthly' | 'quarterly' | 'yearly'
  >('quarterly');
  const [startDate, setStartDate] = useState(format(subYears(new Date(), 3), 'yyyy-MM-dd'));
  const [endDate, setEndDate] = useState(format(new Date(), 'yyyy-MM-dd'));

  // Results state
  const [portfolioData, setPortfolioData] = useState<PortfolioResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCalculate = async () => {
    if (selectedPPRIds.length === 0) {
      setError('Por favor, selecione pelo menos um PPR.');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const result = await calculatePortfolio({
        ppr_ids: selectedPPRIds,
        bitcoin_allocation: bitcoinAllocation / 100,
        initial_investment: initialInvestment,
        monthly_contribution: monthlyContribution,
        start_date: startDate,
        end_date: endDate,
        rebalancing_frequency: rebalancingFrequency,
      });

      setPortfolioData(result);
    } catch (err) {
      setError(
        'Erro ao calcular a carteira. Verifique se o backend está a correr e se os parâmetros estão corretos.'
      );
      console.error('Error calculating portfolio:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                PPR + Bitcoin
              </h1>
              <p className="text-gray-600 mt-1">
                Compare carteiras PPR tradicionais com carteiras híbridas PPR+Bitcoin
              </p>
            </div>
            <div className="text-4xl">₿</div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <DisclaimerBanner />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Configuration */}
          <div className="lg:col-span-1 space-y-6">
            <PPRSelector selectedPPRIds={selectedPPRIds} onChange={setSelectedPPRIds} />
            <BitcoinSlider value={bitcoinAllocation} onChange={setBitcoinAllocation} />
            <InvestmentInputs
              initialInvestment={initialInvestment}
              monthlyContribution={monthlyContribution}
              rebalancingFrequency={rebalancingFrequency}
              onInitialInvestmentChange={setInitialInvestment}
              onMonthlyContributionChange={setMonthlyContribution}
              onRebalancingFrequencyChange={setRebalancingFrequency}
            />
            <PeriodSelector
              startDate={startDate}
              endDate={endDate}
              onStartDateChange={setStartDate}
              onEndDateChange={setEndDate}
            />

            {/* Calculate Button */}
            <button
              onClick={handleCalculate}
              disabled={loading || selectedPPRIds.length === 0}
              className={`w-full btn-primary ${
                loading || selectedPPRIds.length === 0
                  ? 'opacity-50 cursor-not-allowed'
                  : ''
              }`}
            >
              {loading ? 'A Calcular...' : 'Calcular Carteira'}
            </button>

            {error && (
              <div className="bg-red-50 border-l-4 border-red-400 p-4">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}
          </div>

          {/* Right Column - Results */}
          <div className="lg:col-span-2 space-y-6">
            {portfolioData ? (
              <>
                <PortfolioChart data={portfolioData.time_series} />
                <MetricsPanel metrics={portfolioData.metrics} />
              </>
            ) : (
              <div className="card text-center py-12">
                <div className="text-6xl mb-4">📊</div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  Configure a sua carteira
                </h3>
                <p className="text-gray-600">
                  Selecione os PPRs, ajuste a alocação Bitcoin e clique em "Calcular Carteira"
                  para ver os resultados.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-sm text-gray-500">
            Desenvolvido para fins educacionais. Não constitui aconselhamento financeiro.
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
