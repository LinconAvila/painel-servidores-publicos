import React, { useState } from 'react';
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
  const obterLimiteSimilaridade = () => {
    const texto = String(limite).trim();
    if (texto === '') return LIMITE_SIMILARIDADE_PADRAO;
    const numero = Number(texto);
    if (!Number.isInteger(numero) || numero < 1 || numero > LIMITE_SIMILARIDADE_MAX) {
      return null;
    }
    return numero;
  };

  const fetchServidores = async (nomeParaBuscar, paginaAtual = 1) => {
    const termo = (nomeParaBuscar || '').trim();

    if (termo === '') {
      setErroApi('parametro_invalido');
      setMensagemErro('Informe um nome para realizar a busca.');
      setSubmitted(true);
      limparResultados();
      return;
    }

    let url;
    if (similaridade) {
      const limiteValido = obterLimiteSimilaridade();
      if (limiteValido === null) {
        setErroApi('parametro_invalido');
        setMensagemErro(`O limite de resultados deve ser um número inteiro entre 1 e ${LIMITE_SIMILARIDADE_MAX}.`);
        setSubmitted(true);
        limparResultados();
        return;
      }
      url = `/api/servidores?similar=${encodeURIComponent(termo)}&limit=${limiteValido}`;
    } else {
      url = `/api/servidores?nome=${encodeURIComponent(termo)}&pagina=${paginaAtual}&limit=${PAGE_SIZE}`;
    }

    setLoading(true);
    setErroApi(null);
    setMensagemErro('');
    setSubmitted(true);

    try {
      const response = await fetch(url);
      const data = await response.json();

      if (response.status === 200) {
        if (similaridade) {
          // Busca por similaridade: lista completa (até o limite), paginada no front
          const listaCompleta = (data.resultados || []).map((item, idx) =>
            formatarServidor(item, idx + 1)
          );
          setBuscaSimilar(true);
          setResultados(listaCompleta);
          setTotalResultados(data.total ?? listaCompleta.length);
          setPage(1);
        } else if (data.nome && !data.resultados) {
          // Resultado único direto para tela de detalhe
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
          setTotalResultados(data.total || listaFormatada.length);
          setPage(data.pagina || paginaAtual);
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

  // Ao disparar nova busca, reseta SEMPRE para a página 1
  const handleBuscar = () => {
    setPage(1);
    fetchServidores(nome, 1);
  };

  // Navegação entre páginas
  const handlePageChange = (novaPagina) => {
    setPage(novaPagina);
    // Na similaridade a lista já está toda carregada: só troca a fatia exibida
    if (!buscaSimilar) {
      fetchServidores(nome, novaPagina);
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