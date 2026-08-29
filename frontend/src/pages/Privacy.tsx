import { Link } from 'react-router-dom';

/**
 * Privacy policy.
 *
 * The app stores no personal data: portfolio inputs are sent to the API,
 * used to compute a result, and never persisted against a user. Keep this
 * page accurate if that ever changes (accounts, analytics, cookies).
 */
export default function Privacy() {
  return (
    <div className="min-h-screen bg-gray-50">
      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <Link to="/" className="text-sm text-blue-600 hover:underline">
          &larr; Voltar à calculadora
        </Link>

        <h1 className="mt-6 text-3xl font-bold text-gray-900">
          Política de Privacidade
        </h1>
        <p className="mt-2 text-sm text-gray-500">
          Última atualização: 28 de agosto de 2026
        </p>

        <div className="mt-8 space-y-6 text-gray-700">
          <section>
            <h2 className="text-xl font-semibold text-gray-900">
              1. Que dados recolhemos
            </h2>
            <p className="mt-2">
              Não recolhemos dados pessoais. Esta aplicação não tem contas de
              utilizador, não pede o seu nome, email ou quaisquer dados de
              identificação, e não utiliza cookies de rastreamento.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900">
              2. Dados que introduz na calculadora
            </h2>
            <p className="mt-2">
              Os valores que introduz (montante de investimento, alocação em
              Bitcoin, datas, fundos selecionados) são enviados ao nosso
              servidor apenas para calcular o resultado que lhe é apresentado.
              Não são associados a si, não são guardados numa base de dados e
              não são partilhados com terceiros.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900">
              3. Registos técnicos
            </h2>
            <p className="mt-2">
              O servidor mantém registos técnicos temporários (endereço IP,
              data e hora do pedido) para garantir a segurança e o
              funcionamento do serviço, incluindo a limitação do número de
              pedidos. Estes registos não são usados para o identificar nem
              para publicidade.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900">
              4. Dados de mercado
            </h2>
            <p className="mt-2">
              As cotações de fundos PPR e de Bitcoin apresentadas provêm de
              fontes públicas (Optimize Investment Partners, Bitstamp e
              APFIPP). Não são dados pessoais.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900">
              5. Os seus direitos
            </h2>
            <p className="mt-2">
              Uma vez que não guardamos dados pessoais, não há dados sobre si
              para consultar, corrigir ou eliminar. Se tiver dúvidas sobre esta
              política, pode contactar-nos através do endereço indicado nos
              Termos e Condições.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900">
              6. Alterações
            </h2>
            <p className="mt-2">
              Esta política pode ser atualizada. A data da última atualização
              está indicada no topo desta página.
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}
