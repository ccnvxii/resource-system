import React from 'react';
import { PlusCircle, RefreshCw, ClipboardList, PackagePlus } from 'lucide-react';

const Header = ({ onOpenForm, onOpenStockIn, onRefresh, onAddResource }) => {
  // Базовий набір стилів для всіх кнопок
  const btnBase = "flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm transition-all active:scale-95 border-2 shadow-sm";

  return (
    <header className="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
      <div className="flex items-center gap-4">
        <div className="hidden sm:flex bg-white p-1 rounded-xl shadow-sm border-2 border-blue-100 items-center justify-center overflow-hidden w-12 h-12 shrink-0">
          <img
            src={process.env.PUBLIC_URL + '/logo.ico'}
            alt="ResQ Logo"
            className="w-full h-full object-contain"
          />
        </div>

        <div>
          <h1 className="text-3xl font-extrabold text-slate-800 tracking-tight">
            <span className="text-blue-600">ResQ</span> System
          </h1>
          <p className="text-slate-500 mt-0.5 font-medium text-xs md:text-sm italic">
            Система гуманітарного розподілу
          </p>
        </div>
      </div>

      <div className="flex flex-wrap justify-center gap-3 mt-6 md:mt-0">
        <button
          onClick={onOpenStockIn}
          className={`${btnBase} bg-emerald-50 text-emerald-700 border-emerald-100 hover:bg-emerald-100 hover:border-emerald-200`}
        >
          <PlusCircle size={18} />
          Поставка
        </button>

        <button
          onClick={onOpenForm}
          className={`${btnBase} bg-blue-50 text-blue-700 border-blue-100 hover:bg-blue-100 hover:border-blue-200`}
        >
          <ClipboardList size={18} />
          Заявка
        </button>

        <button
          onClick={onAddResource}
          className={`${btnBase} bg-indigo-50 text-indigo-700 border-indigo-100 hover:bg-indigo-100 hover:border-indigo-200`}
        >
          <PackagePlus size={18} />
          Ресурси
        </button>

        <button
          onClick={onRefresh}
          className="p-2.5 bg-slate-50 text-slate-500 rounded-xl border-2 border-slate-100 hover:bg-slate-100 hover:border-slate-200 transition-all active:scale-95 shadow-sm shrink-0"
          title="Оновити дані"
        >
          <RefreshCw size={20} />
        </button>
      </div>
    </header>
  );
};

export default Header;