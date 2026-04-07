import React from 'react';
import { PlusCircle, RefreshCw, Truck, ClipboardList } from 'lucide-react';

const Header = ({ onOpenForm, onOpenStockIn, onRefresh }) => (
  <header className="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
    <div>
      <h1 className="text-3xl font-extrabold text-slate-800 tracking-tight"><span className="text-blue-600">ResQ</span> System</h1>
      <p className="text-slate-500 mt-1 font-medium">Система гуманітарного розподілу</p>
    </div>
    <div className="flex gap-3 mt-6 md:mt-0">
      <button
        onClick={onOpenStockIn}
        className="flex items-center gap-2 px-5 py-2.5 bg-emerald-50 text-emerald-700 font-bold rounded-xl hover:bg-emerald-100 transition-all border border-emerald-100"
      >
        <PlusCircle size={18} />
        Поставка
      </button>

      <button
        onClick={onOpenForm}
        className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white font-bold rounded-xl hover:bg-blue-700 shadow-lg shadow-blue-200 transition-all active:scale-95"
      >
        <ClipboardList size={18} />
        Нова заявка
      </button>

      <button
        onClick={onRefresh}
        className="p-2.5 bg-slate-100 text-slate-500 rounded-xl hover:bg-slate-200 transition-all"
        title="Оновити дані"
      >
        <RefreshCw size={20} />
      </button>
    </div>
  </header>
);

export default Header;