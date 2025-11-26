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

interface ComparisonChartProps {
  data100PPR: HistoricalDataPoint[];
  dataPPRBTC: HistoricalDataPoint[];
  bitcoinAllocation: number;
}

const ComparisonChart: React.FC<ComparisonChartProps> = ({
  data100PPR,
  dataPPRBTC,
  bitcoinAllocation
}) => {
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

  // Merge both datasets by date
  const chartData = data100PPR.map((item, index) => ({
    date: item.data,
    ppr100: Number(item.portfolio_value),
    pprBtc: Number(dataPPRBTC[index]?.portfolio_value || 0),
  }));

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">Comparação da Evolução das Carteiras</h3>
      <ResponsiveContainer width="100%" height={500}>
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
            dataKey="ppr100"
            name="100% PPR"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="pprBtc"
            name={`${100 - bitcoinAllocation}% PPR + ${bitcoinAllocation}% BTC`}
            stroke="#f97316"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ComparisonChart;
