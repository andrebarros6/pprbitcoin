import React from 'react';

interface BitcoinSliderProps {
  value: number;
  onChange: (value: number) => void;
}

const BitcoinSlider: React.FC<BitcoinSliderProps> = ({ value, onChange }) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(parseFloat(e.target.value));
  };

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">Alocação Bitcoin</h3>
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600">0%</span>
          <span className="text-2xl font-bold text-bitcoin-600">{value.toFixed(0)}%</span>
          <span className="text-sm text-gray-600">100%</span>
        </div>
        <input
          type="range"
          min="0"
          max="100"
          step="5"
          value={value}
          onChange={handleChange}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-bitcoin-500"
          style={{
            background: `linear-gradient(to right, #f97316 0%, #f97316 ${value}%, #e5e7eb ${value}%, #e5e7eb 100%)`,
          }}
        />
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="text-gray-600">PPR</div>
            <div className="text-lg font-semibold">{(100 - value).toFixed(0)}%</div>
          </div>
          <div className="p-3 bg-bitcoin-50 rounded-lg">
            <div className="text-gray-600">Bitcoin</div>
            <div className="text-lg font-semibold text-bitcoin-600">{value.toFixed(0)}%</div>
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Ajuste a percentagem de Bitcoin na sua carteira. O restante será alocado aos PPRs selecionados.
        </p>
      </div>
    </div>
  );
};

export default BitcoinSlider;
