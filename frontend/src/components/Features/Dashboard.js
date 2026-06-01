// src/components/Features/Dashboard.js
import React, { useMemo, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts';
import { TrendingDown, Package, Download, BarChart3, ChevronDown, AlertTriangle } from 'lucide-react';
import * as XLSX from 'xlsx';

const Dashboard = ({ stocks = [], requests = [], resourcesMap = {} }) => {
  const [isVisible, setIsVisible] = useState(false);

  // БЕЗПЕЧНИЙ розрахунок залишків на складах (з урахуванням нульових позицій)
  const stockData = useMemo(() => {
    const totals = {};

    if (resourcesMap) {
      Object.keys(resourcesMap).forEach(id => {
        totals[id] = 0;
      });
    }

    if (Array.isArray(stocks)) {
      stocks.forEach(s => {
        if (!s || !s.resource) return;
        const amountVal = s.amount ? parseFloat(s.amount) : 0;
        totals[s.resource] = (totals[s.resource] || 0) + (isNaN(amountVal) ? 0 : amountVal);
      });
    }

    return Object.entries(totals).map(([id, val]) => {
      const resName = resourcesMap && resourcesMap[id] ? resourcesMap[id].name : `Ресурс ID ${id}`;
      const roundedVal = Math.round(val);
      return {
        name: resName,
        amount: roundedVal,
        displayAmount: roundedVal === 0 ? 0.4 : roundedVal,
        isZero: roundedVal === 0
      };
    })
    .sort((a, b) => b.amount - a.amount)
    .slice(0, 6);
  }, [stocks, resourcesMap]);

  // БЕЗПЕЧНИЙ розрахунок дефіциту ресурсів
  const deficitData = useMemo(() => {
    if (!Array.isArray(requests) || !Array.isArray(stocks) || !requests.length) return [];

    try {
      const requested = requests.reduce((acc, r) => {
        if (!r || !r.resource) return acc;
        const reqVal = r.quantity_requested ? parseFloat(r.quantity_requested) : 0;
        acc[r.resource] = (acc[r.resource] || 0) + (isNaN(reqVal) ? 0 : reqVal);
        return acc;
      }, {});

      const available = stocks.reduce((acc, s) => {
        if (!s || !s.resource) return acc;
        const stockVal = s.amount ? parseFloat(s.amount) : 0;
        acc[s.resource] = (acc[s.resource] || 0) + (isNaN(stockVal) ? 0 : stockVal);
        return acc;
      }, {});

      return Object.keys(requested).map(id => {
        const diff = (requested[id] || 0) - (available[id] || 0);
        const resName = resourcesMap && resourcesMap[id] ? resourcesMap[id].name : `Ресурс ID ${id}`;
        return {
          name: resName,
          deficit: diff > 0 ? Math.round(diff) : 0
        };
      }).filter(item => item.deficit > 0)
        .sort((a, b) => b.deficit - a.deficit)
        .slice(0, 5);
    } catch (e) {
      console.error("Помилка обробки deficitData в дашборді:", e);
      return [];
    }
  }, [requests, stocks, resourcesMap]);

  const exportToExcel = () => {
    if (!Array.isArray(requests) || !requests.length) return;
    const ws = XLSX.utils.json_to_sheet(requests);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Звіт");
    XLSX.writeFile(wb, "ResQ_Report.xlsx");
  };

  // КАСТОМНИЙ КОМПОНЕНТ ДЛЯ ПІДПИСУ ОСІ X З ІКОНКОЮ З LUCIDE-REACT
  const CustomXAxisTick = ({ x, y, payload }) => {
    const itemData = stockData.find(d => d.name === payload.value);
    const isZero = itemData ? itemData.isZero : false;

    const text = payload.value.length > 11 ? `${payload.value.substring(0, 9)}...` : payload.value;

    return (
      <g transform={`translate(${x},${y})`}>
        {/* Якщо нуль, посуваємо текст трохи вбік, щоб звільнити місце для іконки */}
        <text
          x={isZero ? -6 : 0}
          y={0}
          dy={12}
          textAnchor="middle"
          fill={isZero ? "#ef4444" : "#64748b"}
          fontSize={10}
          fontWeight={isZero ? "900" : "bold"}
          className={isZero ? "animate-pulse" : ""}
        >
          {text}
        </text>

        {/* Інтегруємо іконку AlertTriangle з lucide за допомогою SVG-контейнера foreignObject */}
        {isZero && (
          <foreignObject
            x={22}
            y={1}
            width={14}
            height={14}
            className="animate-pulse"
          >
            <AlertTriangle size={12} className="text-red-500" strokeWidth={3} />
          </foreignObject>
        )}
      </g>
    );
  };

  // КАСТОМНИЙ ТУЛТИП ДЛЯ ЗАПАСІВ
  const CustomStockTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-slate-900 text-white p-3 rounded-xl border border-slate-700 shadow-xl text-xs font-sans space-y-1">
          <p className="font-bold text-slate-200">{data.name}</p>
          <hr className="border-slate-800 my-1" />
          {data.isZero ? (
            <p className="text-red-400 font-black flex items-center gap-1">
              <span>● Кількість:</span>
              <span className="bg-red-500/20 px-1.5 py-0.5 rounded text-white font-mono">0 од. (НЕМАЄ)</span>
            </p>
          ) : (
            <p className="text-blue-400 font-bold">
              Поточний запас: <span className="font-mono text-white font-black">{data.amount} од.</span>
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-4 animate-in fade-in duration-500 text-left">

      {/* Кнопка експорту повного звіту */}
        <div className="flex justify-end">
          <button
            onClick={exportToExcel}
            className="flex items-center gap-2 px-6 py-3 bg-white border border-slate-200 rounded-2xl font-black text-[10px] uppercase text-slate-600 hover:bg-slate-50 transition-all shadow-sm active:scale-95"
          >
            <Download size={14} /> Експорт повного звіту у Excel
          </button>
        </div>

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
      <div className={`space-y-6 overflow-hidden transition-all duration-500 ease-in-out ${isVisible ? 'max-h-[1000px] opacity-100 mt-2' : 'max-h-0 opacity-0 pointer-events-none'}`}>

        {stockData.length === 0 && deficitData.length === 0 ? (
          <div className="bg-white p-8 rounded-[2rem] border border-slate-200 shadow-sm text-center">
            <p className="text-slate-400 text-xs font-bold uppercase tracking-wider">Немає достатньо даних для побудови графіків</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

            {/* Графік залишків */}
            <div className="bg-white p-6 rounded-[2rem] border border-slate-200 shadow-sm">
              <div className="flex items-center gap-2 mb-6">
                <Package className="text-blue-600" size={20} />
                <h3 className="font-black text-slate-800 uppercase text-[10px] tracking-widest">Запаси на складах</h3>
              </div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={stockData} margin={{ bottom: 15 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />

                    <XAxis
                      dataKey="name"
                      axisLine={false}
                      tickLine={false}
                      tick={<CustomXAxisTick />}
                    />

                    <YAxis fontSize={10} axisLine={false} tickLine={false} />

                    <Tooltip content={<CustomStockTooltip />} cursor={{fill: '#f8fafc'}} />

                    <Bar dataKey="displayAmount" radius={[4, 4, 0, 0]} barSize={24}>
                      {stockData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={entry.isZero ? '#ef4444' : '#3b82f6'}
                        />
                      ))}
                    </Bar>
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

                    <Tooltip
                      cursor={{fill: '#fef2f2'}}
                      contentStyle={{borderRadius: '12px', border: 'none', backgroundColor: '#0f172a', color: '#fff', fontSize: '12px'}}
                      itemStyle={{color: '#f87171'}}
                      formatter={(value) => [`${value} од.`, 'Нестача (Дефіцит)']}
                    />

                    <Bar dataKey="deficit" radius={[0, 4, 4, 0]} barSize={14}>
                      {deficitData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={index === 0 ? '#ef4444' : '#f87171'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

          </div>
        )}

      </div>
    </div>
  );
};

export default Dashboard;