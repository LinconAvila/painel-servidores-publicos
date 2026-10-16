import { useState } from 'react';
import { Header } from './components/Header';
import { SearchForm } from './components/SearchForm';
import { ResultsArea } from './components/ResultsArea';
import { DetailView } from './components/DetailView';
import './App.css';

// Tamanho padrão de registros por página da aplicação
const PAGE_SIZE = 5;

// Mesmos valores do backend: padrão quando o limit não é enviado e teto máximo
const LIMITE_SIMILARIDADE_PADRAO = 100;
const LIMITE_SIMILARIDADE_MAX = 500;

function formatarServidor(item, id) {
  return {
    id,
    nome: item.nome,
    cargo: item.cargo,
    uf: item.uf,
    orgao: item.orgao,
    status: 'Ativo',
    matricula: '****' + Math.floor(1000 + Math.random() * 9000),
  };
}

function App() {
  const [view, setView] = useState('search');
  const [selectedServidor, setSelectedServidor] = useState(null);

  // Estados dos campos do formulário
  const [nome, setNome] = useState('');
  const [cargo, setCargo] = useState('');
  const [uf, setUf] = useState('');
  const [orgao, setOrgao] = useState('');
  const [similaridade, setSimilaridade] = useState(false);
  const [limite, setLimite] = useState(String(LIMITE_SIMILARIDADE_PADRAO));

  // Filtros ativos da última busca submetida (para paginação consistente)
  const [filtrosAtivos, setFiltrosAtivos] = useState(null);

  // Estados da resposta da API
  const [resultados, setResultados] = useState([]);
  const [totalResultados, setTotalResultados] = useState(0);
  const [page, setPage] = useState(1);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [erroApi, setErroApi] = useState(null);
  const [mensagemErro, setMensagemErro] = useState('');

  // Indica se os resultados exibidos vieram de uma busca por similaridade
  // (a API devolve tudo de uma vez, então a paginação é feita no front)
  const [buscaSimilar, setBuscaSimilar] = useState(false);

  const limparResultados = () => {
    setResultados([]);
    setTotalResultados(0);
  };

  // Retorna o limite validado, ou null se o valor informado for inválido.
  // Campo vazio usa o padrão de 100.
  const obterLimiteSimilaridade = (valorLimite) => {
    const texto = String(valorLimite ?? limite).trim();
    if (texto === '') return LIMITE_SIMILARIDADE_PADRAO;
    const numero = Number(texto);
    if (!Number.isInteger(numero) || numero < 1 || numero > LIMITE_SIMILARIDADE_MAX) {
      return null;
    }
    return numero;
  };

  const fetchServidores = async (filtros, paginaAtual = 1) => {
    const nomeTrim = (filtros.nome || '').trim();
    const cargoTrim = (filtros.cargo || '').trim();
    const ufTrim = (filtros.uf || '').trim().toUpperCase();
    const orgaoTrim = (filtros.orgao || '').trim();
    const isSimilar = Boolean(filtros.similaridade);

    // Validação para busca padrão: ao menos um dos 4 campos deve estar preenchido
    if (!isSimilar && !nomeTrim && !cargoTrim && !ufTrim && !orgaoTrim) {
      setErroApi('parametro_invalido');
      setMensagemErro('Informe ao menos um parâmetro para realizar a busca (nome, cargo, UF ou órgão).');
      setSubmitted(true);
      limparResultados();
      return;
    }

    // Validação para busca por similaridade: exige o termo de nome
    if (isSimilar && !nomeTrim) {
      setErroApi('parametro_invalido');
      setMensagemErro('Informe o nome para busca por similaridade.');
      setSubmitted(true);
      limparResultados();
      return;
    }

    // Montagem dinâmica dos parâmetros de busca
    const params = new URLSearchParams();

    if (isSimilar) {
      const limiteValido = obterLimiteSimilaridade(filtros.limite);
      if (limiteValido === null) {
        setErroApi('parametro_invalido');
        setMensagemErro(`O limite de resultados deve ser um número inteiro entre 1 e ${LIMITE_SIMILARIDADE_MAX}.`);
        setSubmitted(true);
        limparResultados();
        return;
      }
      params.append('similar', nomeTrim);
      if (cargoTrim) params.append('cargo', cargoTrim);
      if (ufTrim) params.append('uf', ufTrim);
      if (orgaoTrim) params.append('orgao', orgaoTrim);
      params.append('limit', String(limiteValido));
    } else {
      if (nomeTrim) params.append('nome', nomeTrim);
      if (cargoTrim) params.append('cargo', cargoTrim);
      if (ufTrim) params.append('uf', ufTrim);
      if (orgaoTrim) params.append('orgao', orgaoTrim);
      params.append('pagina', String(paginaAtual));
      params.append('limit', String(PAGE_SIZE));
    }

    setLoading(true);
    setErroApi(null);
    setMensagemErro('');
    setSubmitted(true);

    try {
      const url = `/api/servidores?${params.toString()}`;
      const response = await fetch(url);
      const data = await response.json();

      if (response.status === 200) {
        if (isSimilar) {
          // Busca por similaridade: lista completa (até o limite), paginada no front
          const listaCompleta = (data.resultados || []).map((item, idx) =>
            formatarServidor(item, idx + 1)
          );
          setBuscaSimilar(true);
          setResultados(listaCompleta);
          setTotalResultados(data.total ?? listaCompleta.length);
          setPage(1);
          if (listaCompleta.length === 0) {
            setMensagemErro('Nenhum servidor encontrado para os critérios informados.');
          }
        } else if (data.nome && !data.resultados) {
          // Resultado único direto para tela de detalhe (busca por nome que retornou exatamente 1)
          const servidorUnico = formatarServidor(data, 1);
          setBuscaSimilar(false);
          setSelectedServidor(servidorUnico);
          setView('detail');
          setResultados([servidorUnico]);
          setTotalResultados(1);
        } else {
          // Múltiplos resultados com metadados de paginação
          const listaFormatada = (data.resultados || []).map((item, idx) =>
            formatarServidor(item, (paginaAtual - 1) * PAGE_SIZE + idx + 1)
          );
          setBuscaSimilar(false);
          setResultados(listaFormatada);
          setTotalResultados(data.total ?? listaFormatada.length);
          setPage(data.pagina || paginaAtual);
          if (listaFormatada.length === 0) {
            setMensagemErro('Nenhum servidor encontrado para os critérios informados.');
          }
        }
      } else if (response.status === 404) {
        limparResultados();
        setErroApi(null);
        setMensagemErro(data.mensagem || 'Nenhum servidor encontrado para os critérios informados');
      } else if (response.status === 400) {
        setErroApi('parametro_invalido');
        setMensagemErro(data.mensagem || 'Parâmetro de busca inválido.');
        limparResultados();
      } else if (response.status === 504) {
        setErroApi('timeout');
        setMensagemErro(data.mensagem || 'A busca demorou demais.');
        limparResultados();
      } else {
        setErroApi('generico');
        setMensagemErro(data.mensagem || 'Ocorreu um erro ao consultar o servidor.');
        limparResultados();
      }
    } catch {
      setErroApi('conexao');
      setMensagemErro('Não foi possível conectar ao servidor da API.');
      limparResultados();
    } finally {
      setLoading(false);
    }
  };

  // Ao disparar nova busca, salva os filtros ativos e reseta SEMPRE para a página 1
  const handleBuscar = () => {
    const filtros = { nome, cargo, uf, orgao, similaridade, limite };
    setFiltrosAtivos(filtros);
    setPage(1);
    fetchServidores(filtros, 1);
  };

  // Navegação entre páginas reutiliza os filtros ativos da última busca
  const handlePageChange = (novaPagina) => {
    setPage(novaPagina);
    // Na similaridade a lista já está toda carregada: só troca a fatia exibida
    if (!buscaSimilar) {
      const filtros = filtrosAtivos || { nome, cargo, uf, orgao, similaridade, limite };
      fetchServidores(filtros, novaPagina);
    }
  };

  // Ao marcar o checkbox, o limite volta para o padrão (100)
  const handleSimilaridadeChange = (marcado) => {
    setSimilaridade(marcado);
    if (marcado) {
      setLimite(String(LIMITE_SIMILARIDADE_PADRAO));
    }
    setPage(1);
  };

  const handleClear = () => {
    setNome('');
    setCargo('');
    setUf('');
    setOrgao('');
    setSimilaridade(false);
    setLimite(String(LIMITE_SIMILARIDADE_PADRAO));
    setFiltrosAtivos(null);
    setBuscaSimilar(false);
    setSubmitted(false);
    limparResultados();
    setErroApi(null);
    setMensagemErro('');
    setPage(1);
  };

  const handleSelectServidor = (servidor) => {
    setSelectedServidor(servidor);
    setView('detail');
  };

  const totalPages = Math.max(1, Math.ceil(totalResultados / PAGE_SIZE));

  const resultadosVisiveis = buscaSimilar
    ? resultados.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
    : resultados;

  if (view === 'detail' && selectedServidor) {
    return (
      <div className="app-container">
        <Header />
        <DetailView
          servidor={selectedServidor}
          onBack={() => setView('search')}
        />
      </div>
    );
  }

  return (
    <div className="app-container">
      <Header />
      <main className="main-content">
        <SearchForm
          nome={nome} setNome={(v) => { setNome(v); setPage(1); }}
          cargo={cargo} setCargo={(v) => { setCargo(v); setPage(1); }}
          uf={uf} setUf={(v) => { setUf(v); setPage(1); }}
          orgao={orgao} setOrgao={(v) => { setOrgao(v); setPage(1); }}
          similaridade={similaridade} setSimilaridade={handleSimilaridadeChange}
          limite={limite} setLimite={(v) => { setLimite(v); setPage(1); }}
          limiteMaximo={LIMITE_SIMILARIDADE_MAX}
          onBuscar={handleBuscar}
          onClear={handleClear}
          erroApi={erroApi}
          mensagemErro={mensagemErro}
        />
        {!erroApi && (
          <ResultsArea
            resultados={resultadosVisiveis}
            totalResultados={totalResultados}
            submitted={submitted}
            loading={loading}
            page={page}
            totalPages={totalPages}
            onPageChange={handlePageChange}
            onSelectServidor={handleSelectServidor}
            onClear={handleClear}
            mensagemErro={mensagemErro}
          />
        )}
      </main>
    </div>
  );
}

export default App;