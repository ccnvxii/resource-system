// src/components/Features/DistributionChart.js
import React, { useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts';
import { BarChart3 } from 'lucide-react';

const DistributionChart = ({ items = [] }) => {
  // Математична агрегація даних: групуємо та підсумовуємо виділені ресурси
  const chartData = useMemo(() => {
    if (!Array.isArray(items) || items.length === 0) return [];

    try {
      const totals = items.reduce((acc, item) => {
        const name = item.resource_name || `Ресурс ID ${item.resource_id}`;
        acc[name] = (acc[name] || 0) + parseFloat(item.amount);
        return acc;
      }, {});

      return Object.entries(totals).map(([name, amount]) => ({
        name: name.length > 20 ? name.substring(0, 18) + '...' : name,
        'Виділено (од.)': Math.round(amount)
      })).sort((a, b) => b['Виділено (од.)'] - a['Виділено (од.)']);
    } catch (e) {
      console.error("Помилка калькуляції даних для гістограми:", e);
      return [];
    }
  }, [items]);

  if (chartData.length === 0) return null;

  return (
    <div className="bg-white p-6 rounded-[2rem] border border-slate-200 shadow-sm animate-in fade-in zoom-in duration-500">
      <div className="flex items-center gap-2 mb-4">
        <BarChart3 className="text-blue-600" size={18} />
        <h4 className="font-black text-slate-800 uppercase text-[10px] tracking-widest">
          Обсяги виділених ресурсів за поточною сесією
        </h4>
      </div>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis dataKey="name" fontSize={10} fontWeight="bold" axisLine={false} tickLine={false} stroke="#64748b" />
            <YAxis fontSize={10} axisLine={false} tickLine={false} stroke="#64748b" />
            <Tooltip
              cursor={{ fill: '#f8fafc' }}
              contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}
            />
            <Bar dataKey="Виділено (од.)" fill="#2563eb" radius={[6, 6, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={index % 2 === 0 ? '#2563eb' : '#3b82f6'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default DistributionChart;