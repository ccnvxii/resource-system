import React, { useMemo, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts';
import { TrendingDown, Package, Download, BarChart3, ChevronDown } from 'lucide-react';
import * as XLSX from 'xlsx';

const Dashboard = ({ stocks = [], requests = [], resourcesMap = {} }) => {
  // Стан для згортання всього дашборду (за замовчуванням false - згорнуто)
  const [isVisible, setIsVisible] = useState(false);

  // Дані для графіка залишків
  const stockData = useMemo(() => {
    if (!stocks.length) return [];
    const totals = stocks.reduce((acc, s) => {
      acc[s.resource] = (acc[s.resource] || 0) + parseFloat(s.amount);
      return acc;
    }, {});

    return Object.entries(totals).map(([id, val]) => ({
      name: resourcesMap[id]?.name || `ID ${id}`,
      amount: val
    })).sort((a, b) => b.amount - a.amount).slice(0, 6);
  }, [stocks, resourcesMap]);

  // Дані для графіка дефіциту
  const deficitData = useMemo(() => {
    if (!requests.length) return [];
    const requested = requests.reduce((acc, r) => {
      acc[r.resource] = (acc[r.resource] || 0) + parseFloat(r.quantity_requested);
      return acc;
    }, {});

    const available = stocks.reduce((acc, s) => {
      acc[s.resource] = (acc[s.resource] || 0) + parseFloat(s.amount);
      return acc;
    }, {});

    return Object.keys(requested).map(id => {
      const diff = (requested[id] || 0) - (available[id] || 0);
      return {
        name: resourcesMap[id]?.name || `ID ${id}`,
        deficit: diff > 0 ? diff : 0
      };
    }).filter(item => item.deficit > 0)
      .sort((a, b) => b.deficit - a.deficit)
      .slice(0, 5);
  }, [requests, stocks, resourcesMap]);

  const exportToExcel = () => {
    if (!requests.length) return;
    const ws = XLSX.utils.json_to_sheet(requests);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Звіт");
    XLSX.writeFile(wb, "ResQ_Report.xlsx");
  };

  return (
    <div className="space-y-4 animate-in fade-in duration-500">

      {/* ГОЛОВНА ШАПКА ДАШБОРДУ */}
      <div
        onClick={() => setIsVisible(!isVisible)}
        className="flex items-center justify-between px-6 py-4 bg-white rounded-3xl cursor-pointer hover:bg-slate-50 transition-all shadow-sm border border-slate-200"
      >
        <div className="flex items-center gap-3">
          <div className="bg-blue-50 p-2 rounded-xl text-blue-600">
            <BarChart3 size={20} />
          </div>
          <div>
            <h3 className="font-black text-slate-800 uppercase text-xs tracking-widest leading-none">
              Аналітичний дашборд
            </h3>
            <p className="text-slate-400 text-[10px] font-bold uppercase mt-1">
              Моніторинг запасів та дефіциту ресурсів
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
            <div className="hidden sm:block bg-slate-100 text-slate-500 px-3 py-1 rounded-full text-[9px] font-black uppercase">
                {isVisible ? 'Сховати графіки' : 'Показати аналітику'}
            </div>
            <div className={`transition-transform duration-300 ${isVisible ? 'rotate-180' : ''}`}>
                <ChevronDown className="text-slate-400" size={20} />
            </div>
        </div>
      </div>

      {/* КОНТЕНТ ДАШБОРДУ (Згортається) */}
      <div className={`space-y-6 overflow-hidden transition-all duration-500 ease-in-out ${isVisible ? 'max-h-[1000px] opacity-100' : 'max-h-0 opacity-0 pointer-events-none'}`}>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-2">

          {/* Графік залишків */}
          <div className="bg-white p-6 rounded-[2rem] border border-slate-200 shadow-sm">
            <div className="flex items-center gap-2 mb-6">
              <Package className="text-blue-600" size={20} />
              <h3 className="font-black text-slate-800 uppercase text-[10px] tracking-widest">Запаси на складах</h3>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stockData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="name" fontSize={10} fontWeight="bold" axisLine={false} tickLine={false} />
                  <YAxis fontSize={10} axisLine={false} tickLine={false} />
                  <Tooltip cursor={{fill: '#f8fafc'}} contentStyle={{borderRadius: '12px', border: 'none'}} />
                  <Bar dataKey="amount" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Графік дефіциту */}
          <div className="bg-white p-6 rounded-[2rem] border border-slate-200 shadow-sm">
            <div className="flex items-center gap-2 mb-6">
              <TrendingDown className="text-red-500" size={20} />
              <h3 className="font-black text-slate-800 uppercase text-[10px] tracking-widest">Критичний дефіцит</h3>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={deficitData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                  <XAxis type="number" hide />
                  <YAxis dataKey="name" type="category" fontSize={10} width={80} fontWeight="bold" axisLine={false} tickLine={false} />
                  <Tooltip cursor={{fill: '#fef2f2'}} contentStyle={{borderRadius: '12px', border: 'none'}} />
                  <Bar dataKey="deficit" radius={[0, 4, 4, 0]}>
                    {deficitData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={index === 0 ? '#ef4444' : '#f87171'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Кнопка експорту */}
        <div className="flex justify-end">
          <button
            onClick={exportToExcel}
            className="flex items-center gap-2 px-6 py-3 bg-white border border-slate-200 rounded-2xl font-black text-[10px] uppercase text-slate-600 hover:bg-slate-50 transition-all shadow-sm active:scale-95"
          >
            <Download size={14} /> Експорт повного звіту у Excel
          </button>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;