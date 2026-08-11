import React from 'react';

const FilterSelect = ({ icon: Icon, value, onChange, children, className = "" }) => {
    return (
        <div className={`flex items-center gap-1.5 bg-white border border-slate-200 rounded-xl px-3 py-1 shadow-sm h-8 ${className}`}>
            {Icon && <Icon size={13} className="text-slate-400 shrink-0" />}
            <select
                value={value}
                onChange={onChange}
                className="bg-transparent text-[11px] font-bold text-slate-700 outline-none cursor-pointer w-full"
            >
                {children}
            </select>
        </div>
    );
};

export default FilterSelect;