import React, {useState} from 'react';
import {PackageSearch, Filter, ChevronUp, ChevronDown} from 'lucide-react';
import api from '../../../services/api';
import StockRow from './StockRow';
import FilterSelect from '../../UI/FilterSelect';

const StockTable = ({stocks = [], resourcesMap = {}, onRefresh}) => {
    const [filterCategory, setFilterCategory] = useState('all');
    const [filterWarehouse, setFilterWarehouse] = useState('all');
    const [sortOrder, setSortOrder] = useState('none');
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

    const sortedStocks = [...filteredStocks].sort((a, b) => {
        if (sortOrder === 'none') return 0;
        const amountA = Number(a.amount) || 0;
        const amountB = Number(b.amount) || 0;
        return sortOrder === 'asc' ? amountA - amountB : amountB - amountA;
    });

    const toggleSort = () => {
        if (sortOrder === 'none') setSortOrder('desc');
        else if (sortOrder === 'desc') setSortOrder('asc');
        else setSortOrder('none');
    };

    const handleSaveEdit = async (id) => {
        try {
            const roundedValue = Math.round(parseFloat(editValue));
            await api.patch(`/stocks/${id}/update_amount/`, {amount: roundedValue});
            setEditingId(null);
            if (onRefresh) onRefresh();
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <section
            className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-[650px]">
            <div className="p-4 border-b border-slate-100 bg-slate-50/50 space-y-4">
                <div className="flex justify-between items-center h-10">
                    <div className="flex items-center gap-2 text-slate-800">
                        <PackageSearch size={22} className="text-blue-600"/>
                        <h2 className="text-lg font-bold">Запаси на складах</h2>
                    </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-200/60">
                    <div className="flex items-center gap-1 text-[10px] font-black uppercase text-slate-400 mr-1">
                        <Filter size={12}/> Фільтри:
                    </div>
                    <FilterSelect icon={PackageSearch} value={filterCategory}
                                  onChange={(e) => setFilterCategory(e.target.value)}>
                        <option value="all">Усі категорії</option>
                        {categories.filter(c => c !== 'all' && c).map(cat => <option key={cat}
                                                                                     value={cat}>{cat}</option>)}
                    </FilterSelect>
                    <FilterSelect icon={PackageSearch} value={filterWarehouse}
                                  onChange={(e) => setFilterWarehouse(e.target.value)}>
                        <option value="all">Усі склади</option>
                        {warehouses.filter(w => w !== 'all' && w).map(wh => <option key={wh} value={wh}>{wh}</option>)}
                    </FilterSelect>
                </div>
            </div>

            <div className="overflow-y-auto flex-1 custom-scrollbar pr-1">
                <table className="w-full text-sm text-left">
                    <thead className="bg-slate-50 sticky top-0 uppercase text-[10px] font-bold text-slate-400">
                    <tr>
                        <th className="px-6 py-4">Склад</th>
                        <th className="px-6 py-4">Ресурс</th>
                        <th className="px-6 py-4 text-right">
                            <button
                                onClick={toggleSort}
                                className="inline-flex items-center gap-1.5 ml-auto hover:text-blue-600 transition-colors uppercase cursor-pointer select-none group"
                            >
                                <span>Кількість</span>
                                <span className="flex flex-col text-slate-400 group-hover:text-blue-600">
                                    <ChevronUp size={10}
                                               className={`-mb-1 ${sortOrder === 'asc' ? 'text-blue-600 stroke-[3]' : ''}`}/>
                                    <ChevronDown size={10}
                                                 className={`${sortOrder === 'desc' ? 'text-blue-600 stroke-[3]' : ''}`}/>
                                </span>
                            </button>
                        </th>
                    </tr>
                    </thead>
                    <tbody>
                    {sortedStocks.map((stock) => (
                        <StockRow
                            key={stock.id}
                            stock={stock}
                            resource={resourcesMap[stock.resource] || {
                                name: '...',
                                category_name: '...',
                                unit_name: '?'
                            }}
                            isEditing={editingId === stock.id}
                            editValue={editValue}
                            setEditValue={setEditValue}
                            onStartEdit={(id, val) => {
                                setEditingId(id);
                                setEditValue(val);
                            }}
                            onSaveEdit={handleSaveEdit}
                        />
                    ))}
                    </tbody>
                </table>
            </div>
        </section>
    );
};

export default StockTable;