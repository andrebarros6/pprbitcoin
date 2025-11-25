import React from 'react';
import { format, subYears } from 'date-fns';

interface PeriodSelectorProps {
  startDate: string;
  endDate: string;
  onStartDateChange: (date: string) => void;
  onEndDateChange: (date: string) => void;
}

const PeriodSelector: React.FC<PeriodSelectorProps> = ({
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
}) => {
  // Calculate min and max dates
  const today = format(new Date(), 'yyyy-MM-dd');
  const minDate = '2019-01-01'; // Bitcoin historical data available from 2019

  const handleQuickSelect = (years: number) => {
    const newStartDate = format(subYears(new Date(), years), 'yyyy-MM-dd');
    onStartDateChange(newStartDate);
    onEndDateChange(today);
  };

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">Período de Análise</h3>

      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="label">Data de Início</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => onStartDateChange(e.target.value)}
              min={minDate}
              max={endDate}
              className="input-field"
            />
          </div>
          <div>
            <label className="label">Data de Fim</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => onEndDateChange(e.target.value)}
              min={startDate}
              max={today}
              className="input-field"
            />
          </div>
        </div>

        <div>
          <label className="label">Períodos Rápidos</label>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => handleQuickSelect(1)}
              className="btn-secondary text-sm"
            >
              1 Ano
            </button>
            <button
              type="button"
              onClick={() => handleQuickSelect(2)}
              className="btn-secondary text-sm"
            >
              2 Anos
            </button>
            <button
              type="button"
              onClick={() => handleQuickSelect(3)}
              className="btn-secondary text-sm"
            >
              3 Anos
            </button>
            <button
              type="button"
              onClick={() => handleQuickSelect(5)}
              className="btn-secondary text-sm"
            >
              5 Anos
            </button>
          </div>
        </div>

        <p className="text-xs text-gray-500">
          Dados disponíveis a partir de 2019. Períodos mais longos fornecem análises mais precisas.
        </p>
      </div>
    </div>
  );
};

export default PeriodSelector;
