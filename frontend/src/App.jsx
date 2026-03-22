import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, Plus, Trash2, Zap, Database } from 'lucide-react';

function App() {
  const [word, setWord] = useState('');
  const [results, setResults] = useState(null);
  const [newWord, setNewWord] = useState('');

  /// folosim clasicul axios pentru api request
  useEffect(() => {
    const timeout = setTimeout(() => {
      if (word.length > 1) fetchAnagrams();
    }, 300);
    return () => clearTimeout(timeout);
  }, [word]);

  const fetchAnagrams = async () => {
    try {
      const res = await axios.get(`/api/anagrams/${word}`);
      setResults(res.data);
    } catch (e) { 
      setResults(null); 
    }
  };

  const addWord = async () => {
    if (!newWord) return;
    try {
      await axios.post('/api/words', { word: newWord });
      alert('Cuvant adaugat: ' + newWord);
      setNewWord('');
    } catch (e) { 
      alert("Eroare la adaugare"); 
    }
  };

  const deleteWord = async (w) => {
    try {
      await axios.delete(`/api/words/${w}`);
      fetchAnagrams(); // Refresh dupa stergere
    } catch (e) { 
      alert("Eroare la stergere"); 
    }
  };

  return (
    <div style={{ background: '#f0f2f5', minHeight: '100vh', padding: '40px', fontFamily: 'Arial, sans-serif' }}>
      <div style={{ maxWidth: '600px', margin: '0 auto', background: '#fff', padding: '30px', borderRadius: '8px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
        
        <h1 style={{ textAlign: 'center', color: '#333', marginBottom: '30px' }}>
           Manager Anagrame
        </h1>

        {/* Sectiune Cautare */}
        <div style={{ position: 'relative', marginBottom: '25px' }}>
          <Search style={{ position: 'absolute', left: '12px', top: '12px', color: '#999' }} size={20} />
          <input 
            style={{ width: '100%', padding: '12px 12px 12px 45px', borderRadius: '4px', border: '1px solid #ccc', boxSizing: 'border-box', fontSize: '16px' }}
            placeholder="Cauta anagrame"
            value={word}
            onChange={(e) => setWord(e.target.value)}
          />
        </div>

        {/* Afisare Rezultate */}
        {results && (
          <div style={{ background: '#fafafa', padding: '15px', borderRadius: '4px', border: '1px solid #eee' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px', fontSize: '14px' }}>
              <span>Anagrame gasite: <strong>{results.count}</strong></span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '5px', color: results.cached ? '#2ecc71' : '#7f8c8d' }}>
                {results.cached ? <Zap size={14} /> : <Database size={14} />}
                {results.cached ? 'Din Cache' : 'Din Baza de Date'}
              </span>
            </div>
            
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {results.anagrams.map(a => (
                <div key={a} style={{ background: '#fff', padding: '6px 12px', borderRadius: '4px', border: '1px solid #ddd', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {a}
                  <Trash2 size={14} color="#e74c3c" style={{ cursor: 'pointer' }} onClick={() => deleteWord(a)} />
                </div>
              ))}
            </div>
          </div>
        )}

        <hr style={{ margin: '30px 0', border: '0', borderTop: '1px solid #eee' }} />

        {/* Sectiune Adaugare */}
        <div>
          <h4 style={{ marginBottom: '10px' }}>Adauga cuvant</h4>
          <div style={{ display: 'flex', gap: '10px' }}>
            <input 
              style={{ flex: 1, padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
              value={newWord}
              onChange={(e) => setNewWord(e.target.value)}
              placeholder="Ex: bacalaureat"
            />
            <button 
              onClick={addWord}
              style={{ background: '#3498db', color: '#fff', border: 'none', padding: '10px 20px', borderRadius: '4px', cursor: 'pointer' }}
            >
              Adauga
            </button>
          </div>
        </div> 
      </div>
    </div>
  );
}

export default App;