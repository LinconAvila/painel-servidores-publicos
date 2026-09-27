import React, { useState } from 'react';
import { Header } from './components/Header';
import { SearchForm } from './components/SearchForm';
import { ResultsArea } from './components/ResultsArea';
import { DetailView } from './components/DetailView';
import './App.css';

const PAGE_SIZE = 5;

function App() {
  const [view, setView] = useState('search'); // 'search' | 'detail'
  const [selectedServidor, setSelectedServidor] = useState(null);

  // Estados dos campos do formulário
  const [nome, setNome] = useState('');
  const [cargo, setCargo] = useState('');
  const [uf, setUf] = useState('');
  const [orgao, setOrgao] = useState('');
  const [similaridade, setSimilaridade] = useState(false);

  // Estados da resposta da API
  const [resultados, setResultados] = useState([]);
  const [totalResultados, setTotalResultados] = useState(0);
  const [page, setPage] = useState(1);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [erroApi, setErroApi] = useState(null); // 'parametro_invalido' | 'timeout' | null
  const [mensagemErro, setMensagemErro] = useState('');

  const fetchServidores = async (nomeParaBuscar, paginaAtual = 1) => {
    if (!nomeParaBuscar || nomeParaBuscar.trim() === '') {
      setErroApi('parametro_invalido');
      setMensagemErro('Informe um nome para realizar a busca.');
      setSubmitted(true);
      setResultados([]);
      return;
    }

    setLoading(true);
    setErroApi(null);
    setMensagemErro('');
    setSubmitted(true);

    try {
      const url = `/api/servidores?nome=${encodeURIComponent(nomeParaBuscar.trim())}&pagina=${paginaAtual}&limit=${PAGE_SIZE}`;
      const response = await fetch(url);
      const data = await response.json();

      if (response.status === 200) {
        // Caso 1: Resultado Único (a API retorna o objeto do servidor diretamente)
        if (data.nome && !data.resultados) {
          const servidorUnico = {
            id: 1,
            nome: data.nome,
            cargo: data.cargo,
            uf: data.uf,
            orgao: data.orgao,
            status: 'Ativo',
            matricula: '****' + Math.floor(1000 + Math.random() * 9000),
          };
          setSelectedServidor(servidorUnico);
          setView('detail');
          setResultados([servidorUnico]);
          setTotalResultados(1);
        } else {
          // Caso 2: Múltiplos Resultados (a API retorna { total, pagina, resultados: [...] })
          const listaFormatada = (data.resultados || []).map((item, idx) => ({
            id: (paginaAtual - 1) * PAGE_SIZE + idx + 1,
            nome: item.nome,
            cargo: item.cargo,
            uf: item.uf,
            orgao: item.orgao,
            status: 'Ativo',
            matricula: '****' + Math.floor(1000 + Math.random() * 9000),
          }));
          setResultados(listaFormatada);
          setTotalResultados(data.total || listaFormatada.length);
          setPage(data.pagina || paginaAtual);
        }
      } else if (response.status === 404) {
        // Nenhum resultado encontrado
        setResultados([]);
        setTotalResultados(0);
      } else if (response.status === 400) {
        // Parâmetro inválido
        setErroApi('parametro_invalido');
        setMensagemErro(data.mensagem || 'Parâmetro de busca inválido.');
        setResultados([]);
      } else if (response.status === 504) {
        // Timeout
        setErroApi('timeout');
        setMensagemErro(data.mensagem || 'A busca demorou demais.');
        setResultados([]);
      } else {
        setErroApi('generico');
        setMensagemErro(data.mensagem || 'Ocorreu um erro ao consultar o servidor.');
        setResultados([]);
      }
    } catch (err) {
      setErroApi('conexao');
      setMensagemErro('Não foi possível conectar ao servidor da API.');
      setResultados([]);
    } finally {
      setLoading(false);
    }
  };

  const handleBuscar = () => {
    setPage(1);
    fetchServidores(nome, 1);
  };

  const handlePageChange = (novaPagina) => {
    setPage(novaPagina);
    fetchServidores(nome, novaPagina);
  };

  const handleClear = () => {
    setNome('');
    setCargo('');
    setUf('');
    setOrgao('');
    setSimilaridade(false);
    setSubmitted(false);
    setResultados([]);
    setTotalResultados(0);
    setErroApi(null);
    setMensagemErro('');
    setPage(1);
  };

  const handleSelectServidor = (servidor) => {
    setSelectedServidor(servidor);
    setView('detail');
  };

  const totalPages = Math.max(1, Math.ceil(totalResultados / PAGE_SIZE));

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
          nome={nome} setNome={setNome}
          cargo={cargo} setCargo={setCargo}
          uf={uf} setUf={setUf}
          orgao={orgao} setOrgao={setOrgao}
          similaridade={similaridade} setSimilaridade={setSimilaridade}
          onBuscar={handleBuscar}
          onClear={handleClear}
          erroApi={erroApi}
          mensagemErro={mensagemErro}
        />
        <ResultsArea
          resultados={resultados}
          submitted={submitted}
          loading={loading}
          page={page}
          totalPages={totalPages}
          onPageChange={handlePageChange}
          onSelectServidor={handleSelectServidor}
          onClear={handleClear}
        />
      </main>
    </div>
  );
}

export default App;