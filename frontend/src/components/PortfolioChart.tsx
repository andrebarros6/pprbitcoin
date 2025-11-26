import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { format, parseISO } from 'date-fns';
import type { HistoricalDataPoint } from '../types/api';

interface PortfolioChartProps {
  data: HistoricalDataPoint[];
  showBreakdown?: boolean;
  title?: string;
}

const PortfolioChart: React.FC<PortfolioChartProps> = ({ data, showBreakdown = false, title = 'Evolução da Carteira' }) => {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-PT', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatDate = (dateStr: string) => {
    try {
      return format(parseISO(dateStr), 'MMM yyyy');
    } catch {
      return dateStr;
    }
  };

  const chartData = data.map((item) => ({
    date: item.data,  // Backend sends 'data' not 'date'
    value: Number(item.portfolio_value),  // Convert Decimal string to number
    ppr: Number(item.ppr_value),  // Convert Decimal string to number
    bitcoin: Number(item.bitcoin_value),  // Convert Decimal string to number
  }));

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            tickFormatter={formatCurrency}
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
          />
          <Tooltip
            formatter={(value: number) => formatCurrency(value)}
            labelFormatter={formatDate}
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
            }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="value"
            name="Valor Total"
            stroke="#f97316"
            strokeWidth={2}
            dot={false}
          />
          {showBreakdown && (
            <>
              <Line
                type="monotone"
                dataKey="ppr"
                name="PPR"
                stroke="#3b82f6"
                strokeWidth={1}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="bitcoin"
                name="Bitcoin"
                stroke="#f59e0b"
                strokeWidth={1}
                dot={false}
              />
            </>
          )}
        </LineChart>
      </ResponsiveContainer>
      <div className="mt-4 flex items-center justify-center gap-4 text-sm text-gray-600">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showBreakdown}
            onChange={() => {}}
            className="h-4 w-4 text-bitcoin-600 focus:ring-bitcoin-500 border-gray-300 rounded"
            disabled
          />
          <span>Mostrar PPR e Bitcoin separadamente</span>
        </label>
      </div>
    </div>
  );
};

export default PortfolioChart;
