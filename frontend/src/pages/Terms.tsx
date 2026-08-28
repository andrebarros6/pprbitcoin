import { Link } from 'react-router-dom';

/**
 * Terms and conditions.
 *
 * The central point is that this is an educational simulation, not financial
 * advice, and that past performance does not predict future returns.
 */
export default function Terms() {
  return (
    <div className="min-h-screen bg-gray-50">
      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <Link to="/" className="text-sm text-blue-600 hover:underline">
          &larr; Voltar à calculadora
        </Link>

        <h1 className="mt-6 text-3xl font-bold text-gray-900">
          Termos e Condições
        </h1>
        <p className="mt-2 text-sm text-gray-500">
          Última atualização: 28 de agosto de 2026
        </p>

        <div className="mt-8 space-y-6 text-gray-700">
          <section>
            <h2 className="text-xl font-semibold text-gray-900">
              1. Natureza do serviço
            </h2>
            <p className="mt-2">
              Esta aplicação é uma ferramenta educativa que simula, com base em
              dados históricos, como teria evoluído uma carteira composta por
              fundos PPR e Bitcoin. Os resultados são simulações históricas, não
              previsões.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900">
              2. Não é aconselhamento financeiro
            </h2>
            <p className="mt-2">
              Nada nesta aplicação constitui aconselhamento financeiro, fiscal
              ou de investimento, nem uma recomendação de compra ou venda de
              qualquer instrumento financeiro. Não somos intermediários
              financeiros registados. Consulte um profissional qualificado antes
              de tomar decisões de investimento.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900">
              3. Rendibilidade passada
            </h2>
            <p className="mt-2">
              A rendibilidade passada não é indicativa de resultados futuros. O
              Bitcoin é um ativo de elevada volatilidade e pode perder uma parte
              substancial do seu valor. Os fundos PPR estão igualmente sujeitos
              a risco de perda de capital, bem como a condições fiscais e de
              resgate específicas que esta ferramenta não simula.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900">
              4. Limitações dos dados
            </h2>
            <p className="mt-2">
              A ferramenta compara um número limitado de fundos PPR e não
              representa a totalidade do mercado português. As simulações não
              incluem impostos, comissões de subscrição ou de resgate, nem os
              benefícios fiscais associados aos PPR. Os dados provêm de fontes
              públicas que consideramos fiáveis, mas não garantimos a sua
              exatidão, integridade ou atualidade.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900">
              5. Limitação de responsabilidade
            </h2>
            <p className="mt-2">
              O serviço é fornecido tal como está, sem garantias de qualquer
              tipo. Não nos responsabilizamos por quaisquer perdas ou danos
              decorrentes da utilização desta ferramenta ou da confiança
              depositada nos seus resultados.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900">
              6. Contacto
            </h2>
            <p className="mt-2">
              Para questões sobre estes termos, contacte o endereço de email
              indicado no repositório do projeto.
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}
