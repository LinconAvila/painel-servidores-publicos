import React, { useState, useMemo } from 'react';
import { Header } from './components/Header';
import { SearchForm } from './components/SearchForm';
import { ResultsArea } from './components/ResultsArea';
import { DetailView } from './components/DetailView';
import { SERVIDORES_MOCK } from './data/servidoresMock';
import './App.css';

const PAGE_SIZE = 5;

function normalizar(str) {
  if (!str) return '';
  return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

function App() {
  const [view, setView] = useState('search');
  const [selectedServidor, setSelectedServidor] = useState(null);

  // Estados dos campos de entrada (o que você digita)
  const [nome, setNome] = useState('');
  const [cargo, setCargo] = useState('');
  const [uf, setUf] = useState('');
  const [orgao, setOrgao] = useState('');
  const [similaridade, setSimilaridade] = useState(false);

  // Filtros aplicados na busca (atualizam APENAS no clique em Buscar)
  const [appliedFilters, setAppliedFilters] = useState(null);
  const [page, setPage] = useState(1);

  const resultados = useMemo(() => {
    if (!appliedFilters) return [];
    const n = normalizar(appliedFilters.nome);
    const c = normalizar(appliedFilters.cargo);
    const o = normalizar(appliedFilters.orgao);

    return SERVIDORES_MOCK.filter((s) => {
      const nomeMatch = n === '' || normalizar(s.nome).includes(n);
      const cargoMatch = c === '' || normalizar(s.cargo).includes(c);
      const ufMatch = appliedFilters.uf === '' || (s.uf || '').toLowerCase() === appliedFilters.uf.toLowerCase();
      const orgaoMatch = o === '' || normalizar(s.orgao).includes(o);
      return nomeMatch && cargoMatch && ufMatch && orgaoMatch;
    });
  }, [appliedFilters]);

  const totalPages = Math.max(1, Math.ceil(resultados.length / PAGE_SIZE));
  const paginatedResultados = resultados.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  // Disparado APENAS ao clicar no botão Buscar ou dar Enter
  const handleBuscar = () => {
    setAppliedFilters({
      nome,
      cargo,
      uf,
      orgao,
      similaridade,
    });
    setPage(1);
  };

  const handleClear = () => {
    setNome('');
    setCargo('');
    setUf('');
    setOrgao('');
    setSimilaridade(false);
    setAppliedFilters(null);
    setPage(1);
  };

  const handleSelectServidor = (servidor) => {
    setSelectedServidor(servidor);
    setView('detail');
  };

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
        />
        <ResultsArea
          resultados={paginatedResultados}
          submitted={Boolean(appliedFilters)}
          page={page}
          totalPages={totalPages}
          onPageChange={setPage}
          onSelectServidor={handleSelectServidor}
          onClear={handleClear}
        />
      </main>
    </div>
  );
}

export default App;