import React, { useState, useRef, useEffect, useMemo } from 'react';
import { ChevronDown } from './icons';

/**
 * Випадаючий список з пошуком за словами.
 * options: [{ value, label }]
 * onChange отримує value (рядок) — як і звичайний <select>, але не event.
 */
const SearchableSelect = ({
    options = [],
    value = '',
    onChange,
    placeholder = 'Оберіть...',
    disabled = false,
    required = false,
    className = '',
    emptyText = 'Нічого не знайдено',
}) => {
    const [open, setOpen] = useState(false);
    const [query, setQuery] = useState('');
    const [highlight, setHighlight] = useState(0);
    const rootRef = useRef(null);
    const listRef = useRef(null);

    const selected = options.find(o => String(o.value) === String(value));

    const filtered = useMemo(() => {
        const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
        if (!words.length) return options;
        // Кожне введене слово має зустрічатися в назві (в будь-якому порядку)
        return options.filter(o => {
            const label = String(o.label).toLowerCase();
            return words.every(w => label.includes(w));
        });
    }, [options, query]);

    useEffect(() => {
        if (!open) return undefined;
        const onDocClick = (e) => {
            if (rootRef.current && !rootRef.current.contains(e.target)) {
                setOpen(false);
                setQuery('');
            }
        };
        document.addEventListener('mousedown', onDocClick);
        return () => document.removeEventListener('mousedown', onDocClick);
    }, [open]);

    useEffect(() => {
        setHighlight(0);
    }, [query, open]);

    useEffect(() => {
        const el = listRef.current?.children[highlight];
        if (el && el.scrollIntoView) el.scrollIntoView({ block: 'nearest' });
    }, [highlight]);

    const pick = (opt) => {
        onChange && onChange(String(opt.value));
        setOpen(false);
        setQuery('');
    };

    const handleKeyDown = (e) => {
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            setOpen(true);
            setHighlight(h => Math.min(h + 1, filtered.length - 1));
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setHighlight(h => Math.max(h - 1, 0));
        } else if (e.key === 'Enter') {
            if (open) {
                e.preventDefault();
                if (filtered[highlight]) pick(filtered[highlight]);
            }
        } else if (e.key === 'Escape') {
            if (open) {
                e.stopPropagation();
                setOpen(false);
                setQuery('');
            }
        }
    };

    return (
        <div ref={rootRef} className="relative w-full">
            <input
                type="text"
                disabled={disabled}
                value={open ? query : (selected ? selected.label : '')}
                placeholder={open && selected ? selected.label : placeholder}
                onFocus={() => setOpen(true)}
                onClick={() => setOpen(true)}
                onChange={(e) => {
                    setQuery(e.target.value);
                    setOpen(true);
                }}
                onKeyDown={handleKeyDown}
                autoComplete="off"
                role="combobox"
                aria-expanded={open}
                className={`${className} pr-9 truncate disabled:cursor-not-allowed`}
            />
            <ChevronDown
                size={14}
                className={`absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none transition-transform ${open ? 'rotate-180' : ''}`}
            />
            {required && (
                <input
                    tabIndex={-1}
                    aria-hidden="true"
                    required
                    value={value || ''}
                    onChange={() => {}}
                    className="absolute left-0 bottom-0 w-full h-px opacity-0 pointer-events-none"
                />
            )}
            {open && !disabled && (
                <ul
                    ref={listRef}
                    className="absolute left-0 right-0 z-[9999] mt-1 max-h-56 overflow-y-auto bg-white border-2 border-blue-100 rounded-xl shadow-xl py-1 text-left"
                >
                    {filtered.length === 0 ? (
                        <li className="px-4 py-3 text-xs text-slate-400">{emptyText}</li>
                    ) : (
                        filtered.map((o, i) => (
                            <li
                                key={o.value}
                                onMouseDown={(e) => { e.preventDefault(); pick(o); }}
                                onMouseEnter={() => setHighlight(i)}
                                className={`px-4 py-2.5 text-sm cursor-pointer ${
                                    i === highlight ? 'bg-blue-50 text-blue-700' : 'text-slate-700'
                                } ${String(o.value) === String(value) ? 'font-bold' : 'font-medium'}`}
                            >
                                {o.label}
                            </li>
                        ))
                    )}
                </ul>
            )}
        </div>
    );
};

export default SearchableSelect;
