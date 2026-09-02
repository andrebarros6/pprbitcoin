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
              <div className="font-medium text-gray-900 flex items-center gap-2">
                <span>{ppr.nome}</span>
                {/* Market position by assets under management. Shown only for
                    the top 10, since a rank is the quickest signal of whether
                    this is a fund the reader is likely to already hold. */}
                {ppr.market_rank && (
                  <span
                    className="text-xs font-semibold text-bitcoin-700 bg-bitcoin-100 rounded px-1.5 py-0.5"
                    title={`${ppr.market_rank}.º maior PPR português por ativos sob gestão`}
                  >
                    #{ppr.market_rank}
                  </span>
                )}
              </div>
              <div className="text-sm text-gray-500">
                {/* TEC (Taxa de Encargos Correntes) as published by the CMVM
                    register. It is the ongoing charges figure -- management,
                    depositary, audit and supervision combined -- not a
                    management fee alone, so it is labelled TEC rather than
                    TER. The NAV series already reflect it, so it is shown for
                    comparison and never applied to returns. Still omitted
                    entirely when unknown, rather than shown as "N/A%". */}
                {ppr.gestor}
                {ppr.taxa_gestao
                  ? ` • TEC: ${Number(ppr.taxa_gestao).toFixed(2)}%`
                  : ''}
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
