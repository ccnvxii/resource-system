import React, { useState } from 'react';
import {
  Filter,
  Edit3,
  Check,
  X,
  Warehouse as WarehouseIcon,
  PackageSearch
} from 'lucide-react';
// Імпортуємо ваш сервіс замість стандартного axios
import api from '../../services/api';

const StockTable = ({ stocks, resourcesMap, onRefresh }) => {
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterWarehouse, setFilterWarehouse] = useState('all');
  const [editingId, setEditingId] = useState(null);
  const [editValue, setEditValue] = useState("");

  // Отримання унікальних значень для фільтрів
  const categories = ['all', ...new Set(Object.values(resourcesMap).map(r => r.category_name))];
  const warehouses = ['all', ...new Set(stocks.map(s => s.warehouse_name))];

  // Логіка фільтрації
  const filteredStocks = stocks.filter(stock => {
    const resource = resourcesMap[stock.resource];
    const isPositive = Number(stock.amount) > 0;
    const matchCategory = filterCategory === 'all' || resource?.category_name === filterCategory;
    const matchWarehouse = filterWarehouse === 'all' || stock.warehouse_name === filterWarehouse;
    return isPositive && matchCategory && matchWarehouse;
  });

  const handleStartEdit = (stock) => {
    setEditingId(stock.id);
    setEditValue(Number(stock.amount).toString());
  };

  const handleSaveEdit = async (id) => {
    try {
      // Використовуємо api.patch. Шлях відносний, бо baseURL вже містить /api
      await api.patch(`/stocks/${id}/update_amount/`, {
        amount: parseFloat(editValue)
      });

      setEditingId(null);
      // Оновлюємо дані у батьківському компоненті
      if (onRefresh) onRefresh();
    } catch (e) {
      // Помилка автоматично обробиться інтерцептором в api.js (виведе toast)
      console.error("Failed to update stock amount:", e);
    }
  };

  return (
    <section className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-[600px] transition-all hover:shadow-md">
      {/* Header & Filters */}
      <div className="p-5 border-b border-slate-100 bg-slate-50/50 space-y-4">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2 text-slate-800">
            <PackageSearch size={22} className="text-blue-600" />
            <h2 className="text-lg font-bold">Запаси на складах</h2>
          </div>
          <span className="text-[10px] font-bold bg-blue-100 text-blue-600 px-2.5 py-1 rounded-full uppercase tracking-wider">
            {filteredStocks.length} позицій
          </span>
        </div>

        <div className="flex gap-3">
          <div className="relative flex-1">
            <Filter size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="w-full text-xs pl-9 pr-3 py-2.5 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500/20 appearance-none cursor-pointer font-medium text-slate-600"
            >
              <option value="all">Усі категорії</option>
              {categories.filter(c => c !== 'all').map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>

          <div className="relative flex-1">
            <WarehouseIcon size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <select
              value={filterWarehouse}
              onChange={(e) => setFilterWarehouse(e.target.value)}
              className="w-full text-xs pl-9 pr-3 py-2.5 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500/20 appearance-none cursor-pointer font-medium text-slate-600"
            >
              <option value="all">Усі склади</option>
              {warehouses.filter(w => w !== 'all').map(wh => (
                <option key={wh} value={wh}>{wh}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Table Content */}
      <div className="overflow-y-auto flex-1 custom-scrollbar">
        <table className="w-full text-sm text-left table-fixed">
          <thead className="bg-slate-50 text-slate-400 uppercase text-[10px] font-bold sticky top-0 z-10">
            <tr>
              <th className="px-6 py-4 w-[35%]">Склад</th>
              <th className="px-6 py-4 w-[45%]">Ресурс</th>
              <th className="px-6 py-4 w-[20%] text-right">Кількість</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {filteredStocks.map((stock) => {
              const resource = resourcesMap[stock.resource] || { name: '...', category_name: '...', unit: '' };
              const isEditing = editingId === stock.id;

              return (
                <tr key={stock.id} className="hover:bg-blue-50/30 transition-colors group">
                  <td className="px-6 py-4 font-medium text-slate-600 italic truncate">
                    {stock.warehouse_name}
                  </td>
                  <td className="px-6 py-4">
                    <div className="font-bold text-slate-800 truncate">{resource.name}</div>
                    <div className="text-[10px] text-blue-500 font-bold uppercase tracking-tight truncate">
                      {resource.category_name}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="relative flex items-center justify-end h-10">
                      {isEditing ? (
                        <div className="flex items-center gap-1 animate-in fade-in zoom-in duration-200">
                          <input
                            autoFocus
                            type="number"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSaveEdit(stock.id)}
                            className="w-20 p-1 border-2 border-blue-500 rounded-lg text-right font-mono text-sm outline-none shadow-sm"
                          />
                          <button
                            onClick={() => handleSaveEdit(stock.id)}
                            className="p-1 bg-green-500 text-white rounded-md hover:bg-green-600 transition-colors"
                          >
                            <Check size={14} />
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            className="p-1 bg-slate-200 text-slate-600 rounded-md hover:bg-slate-300 transition-colors"
                          >
                            <X size={14} />
                          </button>
                        </div>
                      ) : (
                        <div className="relative flex items-center justify-end w-full group-hover:pr-10 transition-all duration-300">
                          <div className="flex flex-col items-end">
                            <span className="bg-slate-100 px-3 py-1 rounded-xl font-mono font-bold text-slate-700">
                              {Number(stock.amount).toFixed(0)}
                            </span>
                            <span className="text-[9px] text-slate-400 font-black uppercase mt-0.5 mr-1">
                              {resource.unit}
                            </span>
                          </div>

                          <button
                            onClick={() => handleStartEdit(stock)}
                            className="absolute right-0 opacity-0 group-hover:opacity-100 transition-all p-2 bg-blue-50 text-blue-600 rounded-xl hover:bg-blue-100 active:scale-90"
                            title="Редагувати"
                          >
                            <Edit3 size={16} />
                          </button>
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
};

export default StockTable;