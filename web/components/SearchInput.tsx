'use client';

import { useEffect, useState } from 'react';

interface SearchInputProps {
  placeholder: string;
  onSearch: (query: string) => void;
  // Populates the box for ?q= deep links / programmatic searches (filters).
  initialValue?: string;
}

// EXPLICIT SUBMIT ONLY. Typing never triggers a search: partial biological
// queries change meaning with every token ("phospho STAT3" vs "phospho STAT3
// Tyr705"), so firing mid-typing showed wrong results and burned the shared
// rate limit. Search runs on Enter or the Search button.
export function SearchInput({ placeholder, onSearch, initialValue = '' }: SearchInputProps) {
  const [query, setQuery] = useState(initialValue);

  // Keep the box in sync when the page sets the query programmatically
  // (?q= auto-load, advanced-filter searches).
  useEffect(() => {
    if (initialValue) setQuery(initialValue);
  }, [initialValue]);

  const submit = () => {
    const q = query.trim();
    if (q) onSearch(q);
  };

  return (
    <div style={{ display: 'flex', width: '100%', maxWidth: '600px', margin: '0 auto', gap: '8px' }}>
      <input
        type="text"
        placeholder={placeholder}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') submit();
        }}
        aria-label="Search query"
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
      <button
        onClick={submit}
        aria-label="Search"
        style={{
          padding: '0 22px',
          background: 'transparent',
          border: '1px solid rgba(74,214,176,.5)',
          borderRadius: '8px',
          color: '#4ad6b0',
          fontSize: '13px',
          fontFamily: '"IBM Plex Mono", monospace',
          fontWeight: 600,
          letterSpacing: '0.5px',
          cursor: 'pointer',
        }}
      >
        SEARCH
      </button>
    </div>
  );
}
