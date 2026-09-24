import React from 'react';
import { Header } from './components/Header';
import { SearchForm } from './components/SearchForm';
import { ResultsArea } from './components/ResultsArea';
import './App.css';

function App() {
  return (
    <div className="app-layout">
      <Header />
      <div className="content-container">
        <SearchForm />
        <ResultsArea />
      </div>
    </div>
  );
}

export default App;