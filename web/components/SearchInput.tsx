'use client';

import { useEffect, useRef, useState } from 'react';

interface SearchInputProps {
  placeholder: string;
  onSearch: (query: string) => void;
  debounceMs?: number;
}

export function SearchInput({ placeholder, onSearch, debounceMs = 400 }: SearchInputProps) {
  const [query, setQuery] = useState('');
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    return () => clearTimeout(debounceTimer.current);
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => onSearch(value), debounceMs);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      clearTimeout(debounceTimer.current);
      onSearch(query);
    }
  };

  return (
    <div style={{ display: 'flex', width: '100%', maxWidth: '600px', margin: '0 auto' }}>
      <input
        type="text"
        placeholder={placeholder}
        value={query}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        style={{
          flex: 1,
          padding: '16px 24px',
          background: 'rgba(255,255,255,.05)',
          border: '1px solid rgba(255,255,255,.14)',
          borderRadius: '8px',
          color: '#e7f0ee',
          fontSize: '16px',
          fontFamily: "'Manrope', sans-serif",
          outline: 'none',
          transition: 'border-color 0.2s',
        }}
        onFocus={(e) => {
          e.currentTarget.style.borderColor = 'rgba(74,214,176,.5)';
        }}
        onBlur={(e) => {
          e.currentTarget.style.borderColor = 'rgba(255,255,255,.14)';
        }}
      />
    </div>
  );
}
