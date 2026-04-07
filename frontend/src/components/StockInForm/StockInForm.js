import React, { useState } from 'react';
import {
  X,
  Warehouse,
  PackagePlus,
  Hash,
  Plus,
  Trash2,
  ArrowDownCircle,
  Loader2,
  Save
} from 'lucide-react';

const StockInForm = ({ isOpen, onClose, warehouses, resources, onSubmit, loading }) => {
  // Тепер стан — це масив рядків (rows)
  const [warehouse, setWarehouse] = useState('');
  const [rows, setRows] = useState([{ resource: '', amount: '' }]);

  if (!isOpen) return null;

  const handleAddRow = () => {
    setRows([...rows, { resource: '', amount: '' }]);
  };

  const handleRemoveRow = (index) => {
    setRows(rows.filter((_, i) => i !== index));
  };

  const handleRowChange = (index, field, value) => {
    const newRows = [...rows];
    newRows[index][field] = value;
    setRows(newRows);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!warehouse || rows.some(r => !r.resource || !r.amount)) return;

    // Передаємо дані у форматі масиву для обробки в App.js
    onSubmit({ warehouse, items: rows });

    // Скидання форми
    setWarehouse('');
    setRows([{ resource: '', amount: '' }]);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm overflow-y-auto p-4">
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-3xl relative animate-scale-up border-t-8 border-emerald-500 overflow-hidden">

        <div className="bg-emerald-50/50 p-6 border-b border-emerald-100 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="bg-emerald-500 p-2 rounded-xl shadow-lg shadow-emerald-100">
              <ArrowDownCircle className="text-white" size={24} />
            </div>
            <div>
              <h2 className="text-xl font-black text-slate-800 tracking-tight">Поповнення складів</h2>
              <p className="text-[10px] text-emerald-600 font-bold uppercase tracking-widest mt-0.5">Масове зарахування ресурсів</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-emerald-100 rounded-full text-emerald-400 transition-colors"><X size={20} /></button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Вибір складу (один для всіх позицій у цій формі) */}
          <div className="max-w-xs">
            <label className="flex items-center gap-2 text-[10px] font-black text-slate-400 mb-1.5 uppercase ml-1 tracking-wider">
              <Warehouse size={12} /> Цільовий Склад
            </label>
            <select
              required
              value={warehouse}
              onChange={(e) => setWarehouse(e.target.value)}
              className="w-full p-3.5 rounded-xl border border-slate-200 bg-white outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 font-bold text-slate-700 transition-all cursor-pointer"
            >
              <option value="">-- Оберіть склад --</option>
              {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
          </div>

          {/* Список ресурсів */}
          <div className="space-y-3 max-h-[40vh] overflow-y-auto pr-2 custom-scrollbar">
            {rows.map((row, index) => (
              <div key={index} className="flex flex-col md:flex-row gap-4 items-end bg-slate-50 p-4 rounded-2xl border border-slate-200 transition-all hover:border-emerald-200 group">
                <div className="flex-1 w-full">
                  <label className="flex items-center gap-1.5 text-[9px] font-bold text-slate-400 mb-1 uppercase ml-1">
                    <PackagePlus size={10} /> Ресурс
                  </label>
                  <select
                    required
                    value={row.resource}
                    onChange={(e) => handleRowChange(index, 'resource', e.target.value)}
                    className="w-full p-2.5 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-emerald-500/20 text-sm font-medium"
                  >
                    <option value="">-- Оберіть тип --</option>
                    {resources.map(r => <option key={r.id} value={r.id}>{r.name} ({r.unit})</option>)}
                  </select>
                </div>

                <div className="w-full md:w-40">
                  <label className="flex items-center gap-1.5 text-[9px] font-bold text-slate-400 mb-1 uppercase ml-1">
                    <Hash size={10} /> Кількість
                  </label>
                  <input
                    required
                    type="number" min="1"
                    value={row.amount}
                    onChange={(e) => handleRowChange(index, 'amount', e.target.value)}
                    className="w-full p-2.5 rounded-xl border border-slate-200 outline-none focus:ring-2 focus:ring-emerald-500/20 text-sm font-black text-slate-800"
                    placeholder="0"
                  />
                </div>

                {rows.length > 1 && (
                  <button
                    type="button"
                    onClick={() => handleRemoveRow(index)}
                    className="p-2.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all"
                  >
                    <Trash2 size={18} />
                  </button>
                )}
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={handleAddRow}
            className="flex items-center gap-2 text-emerald-600 font-bold hover:bg-emerald-50 px-6 py-3 rounded-xl border-2 border-dashed border-emerald-200 w-full justify-center transition-all group"
          >
            <Plus size={20} className="group-hover:rotate-90 transition-transform" />
            Додати ще один ресурс
          </button>

          <div className="pt-6 flex gap-4 justify-end border-t border-slate-100">
            <button type="button" onClick={onClose} className="px-6 py-3 text-slate-500 font-bold hover:bg-slate-100 rounded-xl">Скасувати</button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-10 py-3 bg-emerald-600 text-white font-black rounded-xl hover:bg-emerald-700 shadow-xl shadow-emerald-200 active:scale-95 disabled:bg-slate-300"
            >
              {loading ? <Loader2 size={20} className="animate-spin" /> : <Save size={20} />}
              {loading ? "Збереження..." : "Зарахувати все"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default StockInForm;