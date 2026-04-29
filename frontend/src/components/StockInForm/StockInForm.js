import React, { useState } from 'react';
import { Warehouse, PackagePlus, Hash, Plus, Trash2, Save } from 'lucide-react';

const StockInForm = ({ warehouses, resources, onSubmit, loading, onClose }) => {
  const [warehouse, setWarehouse] = useState('');
  const [rows, setRows] = useState([{ resource: '', amount: '' }]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!warehouse || rows.some(r => !r.resource || !r.amount)) return;

    onSubmit({ warehouse, items: rows });

    // Скидання форми
    setWarehouse('');
    setRows([{ resource: '', amount: '' }]);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Вибір складу */}
      <div className="max-w-xs bg-emerald-50/50 p-4 rounded-2xl border border-emerald-100">
        <label className="flex items-center gap-2 text-[10px] font-black text-emerald-700 mb-1.5 uppercase ml-1 tracking-wider">
          <Warehouse size={12} /> Цільовий Склад
        </label>
        <select
          required
          value={warehouse}
          onChange={(e) => setWarehouse(e.target.value)}
          className="w-full p-3 rounded-xl border border-emerald-200 outline-none focus:ring-2 focus:ring-emerald-500/20 font-bold text-slate-700"
        >
          <option value="">-- Оберіть склад --</option>
          {warehouses.map(w => (
            <option key={w.id} value={w.id}>{w.name}</option>
          ))}
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
                onChange={(e) => {
                  const newRows = [...rows];
                  newRows[index].resource = e.target.value;
                  setRows(newRows);
                }}
                className="w-full p-2.5 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-emerald-500/20 text-sm font-medium"
              >
                <option value="">-- Оберіть тип --</option>
                {resources.map(r => (
                  <option key={r.id} value={r.id}>{r.name} ({r.unit})</option>
                ))}
              </select>
            </div>

            <div className="w-full md:w-40">
              <label className="flex items-center gap-1.5 text-[9px] font-bold text-slate-400 mb-1 uppercase ml-1">
                <Hash size={10} /> Кількість
              </label>
              <input
                required
                type="number"
                min="1"
                value={row.amount}
                onChange={(e) => {
                  const newRows = [...rows];
                  newRows[index].amount = e.target.value;
                  setRows(newRows);
                }}
                className="w-full p-2.5 rounded-xl border border-slate-200 outline-none focus:ring-2 focus:ring-emerald-500/20 text-sm font-black text-slate-800"
                placeholder="0"
              />
            </div>

            {rows.length > 1 && (
              <button
                type="button"
                onClick={() => setRows(rows.filter((_, i) => i !== index))}
                className="p-2.5 text-slate-300 hover:text-red-500 transition-all"
              >
                <Trash2 size={18} />
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Кнопка додавання рядка */}
      <button
        type="button"
        onClick={() => setRows([...rows, { resource: '', amount: '' }])}
        className="flex items-center gap-2 text-emerald-600 font-bold hover:bg-emerald-50 px-6 py-3 rounded-xl border-2 border-dashed border-emerald-200 w-full justify-center transition-all"
      >
        <Plus size={20} /> Додати ще один ресурс
      </button>

      {/* Кнопки дій */}
      <div className="pt-6 flex gap-4 justify-end border-t border-slate-100">
        <button
          type="button"
          onClick={onClose}
          className="px-6 py-3 text-slate-500 font-bold hover:bg-slate-100 rounded-xl transition-colors"
        >
          Скасувати
        </button>
        <button
          type="submit"
          disabled={loading}
          className="flex items-center gap-2 px-10 py-3 bg-emerald-600 text-white font-black rounded-xl hover:bg-emerald-700 shadow-xl disabled:bg-slate-300 transition-all active:scale-95"
        >
          {loading ? (
            "Збереження..."
          ) : (
            <>
              <Save size={20} /> Зарахувати все
            </>
          )}
        </button>
      </div>
    </form>
  );
};

export default StockInForm;