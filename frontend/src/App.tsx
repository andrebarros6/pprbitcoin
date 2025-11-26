import { useState } from 'react';
import { format, subYears } from 'date-fns';
import DisclaimerBanner from './components/DisclaimerBanner';
import PPRSelector from './components/PPRSelector';
import BitcoinSlider from './components/BitcoinSlider';
import PeriodSelector from './components/PeriodSelector';
import InvestmentInputs from './components/InvestmentInputs';
import ComparisonChart from './components/ComparisonChart';
import MetricsComparisonTable from './components/MetricsComparisonTable';
import { comparePortfolios } from './api/client';
import type { CompareResponse } from './types/api';

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
  const [comparisonData, setComparisonData] = useState<CompareResponse | null>(null);
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

      // Portfolio 1: 100% PPR (no Bitcoin)
      const portfolio100PPR = {
        ppr_allocations: selectedPPRIds.map(pprId => ({
          ppr_id: pprId,
          allocation_percentage: 100 / selectedPPRIds.length,
        })),
        bitcoin_percentage: 0,
        initial_investment: initialInvestment,
        start_date: startDate,
        end_date: endDate,
        rebalancing_frequency: rebalancingFrequency,
      };

      // Portfolio 2: PPR + Bitcoin
      const pprPercentage = 100 - bitcoinAllocation;
      const allocationPerPPR = pprPercentage / selectedPPRIds.length;

      const portfolioPPRBitcoin = {
        ppr_allocations: selectedPPRIds.map(pprId => ({
          ppr_id: pprId,
          allocation_percentage: allocationPerPPR,
        })),
        bitcoin_percentage: bitcoinAllocation,
        initial_investment: initialInvestment,
        start_date: startDate,
        end_date: endDate,
        rebalancing_frequency: rebalancingFrequency,
      };

      // Compare both portfolios
      const result = await comparePortfolios({
        portfolios: [portfolio100PPR, portfolioPPRBitcoin],
        portfolio_names: ['100% PPR', `${100 - bitcoinAllocation}% PPR + ${bitcoinAllocation}% BTC`],
      });

      setComparisonData(result);
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
            {comparisonData ? (
              <>
                {/* Combined Chart */}
                <ComparisonChart
                  data100PPR={comparisonData.portfolios[0].historical_data}
                  dataPPRBTC={comparisonData.portfolios[1].historical_data}
                  bitcoinAllocation={bitcoinAllocation}
                />

                {/* Metrics Comparison Table */}
                <MetricsComparisonTable
                  metrics100PPR={comparisonData.portfolios[0].metrics}
                  metricsPPRBTC={comparisonData.portfolios[1].metrics}
                  bitcoinAllocation={bitcoinAllocation}
                />

                {/* Comparison Summary */}
                <div className="card bg-gradient-to-br from-bitcoin-50 to-orange-50 border-2 border-bitcoin-300">
                  <h3 className="text-xl font-bold text-gray-900 mb-4">📊 Resumo da Comparação</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-white rounded-lg p-4">
                      <p className="text-sm text-gray-600 mb-1">Melhor Retorno Total</p>
                      <p className="text-lg font-bold text-bitcoin-600">
                        {comparisonData.comparison_summary.best_return}
                      </p>
                    </div>
                    <div className="bg-white rounded-lg p-4">
                      <p className="text-sm text-gray-600 mb-1">Melhor Sharpe Ratio</p>
                      <p className="text-lg font-bold text-bitcoin-600">
                        {comparisonData.comparison_summary.best_sharpe}
                      </p>
                    </div>
                    <div className="bg-white rounded-lg p-4">
                      <p className="text-sm text-gray-600 mb-1">Menor Volatilidade</p>
                      <p className="text-lg font-bold text-green-600">
                        {comparisonData.comparison_summary.lowest_volatility}
                      </p>
                    </div>
                    <div className="bg-white rounded-lg p-4">
                      <p className="text-sm text-gray-600 mb-1">Menor Drawdown</p>
                      <p className="text-lg font-bold text-green-600">
                        {comparisonData.comparison_summary.lowest_drawdown}
                      </p>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="card text-center py-12">
                <div className="text-6xl mb-4">📊</div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  Configure a sua carteira
                </h3>
                <p className="text-gray-600">
                  Selecione os PPRs, ajuste a alocação Bitcoin e clique em "Calcular Carteira"
                  para ver a comparação entre 100% PPR vs PPR+Bitcoin.
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
