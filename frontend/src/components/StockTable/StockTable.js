import React, { useState } from 'react';
import axios from 'axios';
import {
  Search,
  Filter,
  Edit3,
  Check,
  X,
  Warehouse as WarehouseIcon,
  PackageSearch
} from 'lucide-react';

const StockTable = ({ stocks, resourcesMap, onRefresh }) => {
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterWarehouse, setFilterWarehouse] = useState('all');
  const [editingId, setEditingId] = useState(null);
  const [editValue, setEditValue] = useState("");

  const categories = ['all', ...new Set(Object.values(resourcesMap).map(r => r.category_name))];
  const warehouses = ['all', ...new Set(stocks.map(s => s.warehouse_name))];

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
      await axios.patch(`/api/stocks/${id}/update_amount/`, { amount: editValue });
      setEditingId(null);
      onRefresh();
    } catch (e) {
      alert("Помилка при оновленні");
    }
  };

  return (
    <section className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-[600px] transition-all hover:shadow-md">
      {/* Header Section */}
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

        {/* Filter Controls */}
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Filter size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="w-full text-xs pl-9 pr-3 py-2.5 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500/20 appearance-none cursor-pointer font-medium text-slate-600"
            >
              <option value="all">Усі категорії</option>
              {categories.filter(c => c !== 'all').map(cat => <option key={cat} value={cat}>{cat}</option>)}
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
              {warehouses.filter(w => w !== 'all').map(wh => <option key={wh} value={wh}>{wh}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Table Section */}
      <div className="overflow-y-auto flex-1 custom-scrollbar">
        <table className="w-full text-sm text-left">
          <thead className="bg-slate-50 text-slate-400 uppercase text-[10px] font-bold sticky top-0 z-10">
            <tr>
              <th className="px-6 py-4">Склад</th>
              <th className="px-6 py-4">Ресурс</th>
              <th className="px-6 py-4 text-right">Кількість</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {filteredStocks.map((stock) => {
              const resource = resourcesMap[stock.resource] || { name: '...', category_name: '...', unit: '' };
              const isEditing = editingId === stock.id;

              return (
                <tr key={stock.id} className="hover:bg-blue-50/30 transition-colors group">
                  <td className="px-6 py-4 font-medium text-slate-600 italic">
                    {stock.warehouse_name}
                  </td>
                  <td className="px-6 py-4">
                    <div className="font-bold text-slate-800">{resource.name}</div>
                    <div className="text-[10px] text-blue-500 font-bold uppercase tracking-tight">{resource.category_name}</div>
                  </td>
                  <td className="px-6 py-4">
                    {isEditing ? (
                      <div className="flex items-center justify-end gap-2">
                        <input
                          autoFocus
                          type="number"
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          className="w-20 p-1.5 border-2 border-blue-500 rounded-lg text-right font-mono text-sm outline-none shadow-sm"
                        />
                        <button onClick={() => handleSaveEdit(stock.id)} className="p-1.5 bg-green-500 text-white rounded-md hover:bg-green-600 transition-colors">
                          <Check size={14} />
                        </button>
                        <button onClick={() => setEditingId(null)} className="p-1.5 bg-slate-200 text-slate-600 rounded-md hover:bg-slate-300 transition-colors">
                          <X size={14} />
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center justify-end gap-3">
                        <div className="flex flex-col items-end">
                          <span className="font-mono font-bold text-slate-700 bg-slate-100 px-2.5 py-1 rounded-lg border border-slate-200">
                            {Number(stock.amount).toFixed(0)}
                          </span>
                          <span className="text-[9px] text-slate-400 font-bold uppercase mt-1">{resource.unit}</span>
                        </div>
                        <button
                          onClick={() => handleStartEdit(stock)}
                          className="opacity-0 group-hover:opacity-100 p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-100 rounded-lg transition-all"
                        >
                          <Edit3 size={16} />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {filteredStocks.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 space-y-4 py-20">
            <Search size={48} strokeWidth={1} />
            <p className="italic text-sm">Запаси відсутні або приховані фільтрами</p>
          </div>
        )}
      </div>
    </section>
  );
};

export default StockTable;