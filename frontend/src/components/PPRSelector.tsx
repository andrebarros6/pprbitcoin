import React, { useState, useEffect } from 'react';
import { getPPRs } from '../api/client';
import type { PPR } from '../types/api';

interface PPRSelectorProps {
  selectedPPRIds: string[];
  onChange: (pprIds: string[]) => void;
}

const PPRSelector: React.FC<PPRSelectorProps> = ({ selectedPPRIds, onChange }) => {
  const [pprs, setPPRs] = useState<PPR[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPPRs = async () => {
      try {
        setLoading(true);
        const data = await getPPRs();
        setPPRs(data);
        setError(null);
      } catch (err) {
        setError('Erro ao carregar PPRs. Verifique se o backend está a correr.');
        console.error('Error fetching PPRs:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchPPRs();
  }, []);

  const handleTogglePPR = (pprId: string) => {
    if (selectedPPRIds.includes(pprId)) {
      onChange(selectedPPRIds.filter(id => id !== pprId));
    } else {
      onChange([...selectedPPRIds, pprId]);
    }
  };

  if (loading) {
    return (
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Selecionar PPRs</h3>
        <p className="text-gray-500">A carregar PPRs...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Selecionar PPRs</h3>
        <p className="text-red-500">{error}</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">Selecionar PPRs</h3>
      <p className="text-sm text-gray-600 mb-4">
        Escolha um ou mais PPRs para incluir na sua carteira (máximo 5)
      </p>
      <div className="space-y-2">
        {pprs.map((ppr) => (
          <label
            key={ppr.id}
            className={`flex items-center p-3 border rounded-lg cursor-pointer transition-colors ${
              selectedPPRIds.includes(ppr.id)
                ? 'border-bitcoin-500 bg-bitcoin-50'
                : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            <input
              type="checkbox"
              checked={selectedPPRIds.includes(ppr.id)}
              onChange={() => handleTogglePPR(ppr.id)}
              disabled={selectedPPRIds.length >= 5 && !selectedPPRIds.includes(ppr.id)}
              className="h-4 w-4 text-bitcoin-600 focus:ring-bitcoin-500 border-gray-300 rounded"
            />
            <div className="ml-3 flex-1">
              <div className="font-medium text-gray-900">{ppr.nome}</div>
              <div className="text-sm text-gray-500">
                {ppr.gestor} • TER: {ppr.taxa_gestao ? Number(ppr.taxa_gestao).toFixed(2) : 'N/A'}%
              </div>
            </div>
          </label>
        ))}
      </div>
      {selectedPPRIds.length > 0 && (
        <p className="mt-4 text-sm text-gray-600">
          {selectedPPRIds.length} PPR{selectedPPRIds.length > 1 ? 's' : ''} selecionado
          {selectedPPRIds.length > 1 ? 's' : ''}
        </p>
      )}
    </div>
  );
};

export default PPRSelector;
