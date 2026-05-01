import React, {useState} from 'react';
import {Filter, Edit3, Check, X, Warehouse as WarehouseIcon, PackageSearch} from 'lucide-react';
import api from '../../services/api';

const StockTable = ({stocks = [], resourcesMap = {}, onRefresh}) => {
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

    const handleSaveEdit = async (id) => {
        try {
            const roundedValue = Math.round(parseFloat(editValue));

            await api.patch(`/stocks/${id}/update_amount/`, {
                amount: roundedValue
            });
            setEditingId(null);
            if (onRefresh) onRefresh();
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <section
            className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-[600px]">
            <div className="p-5 border-b border-slate-100 bg-slate-50/50 space-y-4">
                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-2 text-slate-800">
                        <PackageSearch size={22} className="text-blue-600"/>
                        <h2 className="text-lg font-bold">Запаси на складах</h2>
                    </div>
                </div>
                <div className="flex gap-3">
                    <select value={filterCategory} onChange={(e) => setFilterCategory(e.target.value)}
                            className="flex-1 p-2 rounded-xl border border-slate-200 text-xs">
                        <option value="all">Усі категорії</option>
                        {categories.filter(c => c !== 'all' && c).map(cat => <option key={cat}
                                                                                     value={cat}>{cat}</option>)}
                    </select>
                    <select value={filterWarehouse} onChange={(e) => setFilterWarehouse(e.target.value)}
                            className="flex-1 p-2 rounded-xl border border-slate-200 text-xs">
                        <option value="all">Усі склади</option>
                        {warehouses.filter(w => w !== 'all' && w).map(wh => <option key={wh} value={wh}>{wh}</option>)}
                    </select>
                </div>
            </div>
            <div className="overflow-y-auto flex-1">
                <table className="w-full text-sm text-left">
                    <thead className="bg-slate-50 sticky top-0 uppercase text-[10px] font-bold text-slate-400">
                    <tr>
                        <th className="px-6 py-4">Склад</th>
                        <th className="px-6 py-4">Ресурс</th>
                        <th className="px-6 py-4 text-right">Кількість</th>
                    </tr>
                    </thead>
                    <tbody>
                    {filteredStocks.map((stock) => {
                        const resource = resourcesMap[stock.resource] || {
                            name: '...',
                            category_name: '...',
                            unit_name: '?'
                        };
                        const isEditing = editingId === stock.id;
                        return (
                            <tr key={stock.id} className="border-b border-slate-50 group hover:bg-blue-50/30">
                                <td className="px-6 py-4 italic text-slate-500">{stock.warehouse_name}</td>
                                <td className="px-6 py-4">
                                    <div className="font-bold text-slate-800">{resource.name}</div>
                                    <div
                                        className="text-[10px] text-blue-500 font-bold uppercase">{resource.category_name}</div>
                                </td>
                                <td className="px-6 py-4 text-right">
                                    <div className="relative flex items-center justify-end h-10">
                                        {isEditing ? (
                                            <div
                                                className="flex items-center gap-1 animate-in fade-in zoom-in duration-200">
                                                <input
                                                    type="number"
                                                    step="1" // Тільки цілі числа
                                                    value={editValue}
                                                    onChange={(e) => setEditValue(e.target.value)}
                                                    onBlur={() => handleSaveEdit(stock.id)}
                                                    autoFocus
                                                    className="w-20 border-2 border-blue-500 rounded p-1 text-right"
                                                />
                                                <button onClick={() => handleSaveEdit(stock.id)}
                                                        className="p-1 bg-green-500 text-white rounded-md">
                                                    <Check size={14}/>
                                                </button>
                                            </div>
                                        ) : (
                                            /* group-hover тепер не зсуває текст, а кнопка перекриває його зверху */
                                            <div className="relative flex items-center justify-end w-full h-full">
                                                <div
                                                    className="flex flex-col items-end transition-opacity duration-300 group-hover:opacity-20">
                            <span className="font-mono font-bold text-slate-700">
                              {Number(stock.amount).toFixed(0)}
                            </span>
                                                    <span className="text-[9px] text-slate-400 font-black uppercase">
                              {resource.unit_name}
                            </span>
                                                </div>

                                                <button
                                                    onClick={() => {
                                                        setEditingId(stock.id);
                                                        setEditValue(stock.amount);
                                                    }}
                                                    className="absolute inset-y-0 right-0 opacity-0 group-hover:opacity-100 transition-all p-2 bg-blue-50 text-blue-600 rounded-xl hover:bg-blue-100 flex items-center justify-center"
                                                    title="Редагувати">
                                                    <Edit3 size={16}/>
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