import React from 'react';
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

const DistributionChart = ({ items = [] }) => {
  // Форматуємо дані для відображення на графіку
  const chartData = items.map(item => ({
    name: item.resource_name.length > 12 ? `${item.resource_name.substring(0, 10)}...` : item.resource_name,
    fullName: item.resource_name,
    'Запитувано (Треба)': item.quantity_requested ? Math.round(item.quantity_requested) : Math.round(item.amount),
    'Виділено (Дали)': Math.round(item.amount),
    'Пріоритет заявки': item.priority ? parseFloat(Number(item.priority).toFixed(1)) : 0.0,
    recipient: item.recipient_name,
    id: item.id
  }));

  // Кастомний красивий тултип при наведенні на елементи графіка
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-slate-900 text-white p-3 rounded-xl border border-slate-700 shadow-xl text-xs font-sans space-y-1">
          <p className="font-black text-blue-400 uppercase tracking-wider">Операція #{data.id}</p>
          <p className="font-bold text-slate-200">Ресурс: {data.fullName}</p>
          <p className="font-medium text-slate-400">Отримувач: {data.recipient}</p>
          <hr className="border-slate-700 my-1" />
          <p className="text-slate-300">Запитувана потреба: <span className="font-mono font-bold text-white">{data['Запитувано (Треба)']} од.</span></p>
          <p className="text-blue-300">Реально виділено: <span className="font-mono font-bold text-blue-400">{data['Виділено (Дали)']} од.</span></p>
          <p className="text-amber-300">Індекс пріоритету: <span className="font-mono font-bold text-amber-400">{data['Пріоритет заявки']} / 10</span></p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-inner space-y-2">
      <div className="flex justify-between items-center px-2">
        <span className="text-[10px] font-black uppercase text-slate-400 tracking-wider">
          Аналітичний зріз операцій розподілу хабів
        </span>
        <div className="flex gap-4 text-[9px] font-bold uppercase tracking-tight">
          <span className="flex items-center gap-1"><span className="w-2 h-2 bg-slate-200 rounded-sm"></span>Запитувано</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 bg-blue-600 rounded-sm"></span>Виділено</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 bg-rose-500 rounded-full"></span>Пріоритет (0-10)</span>
        </div>
      </div>

      <div className="w-full h-72">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 20, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />

            <XAxis
              dataKey="name"
              stroke="#64748b"
              fontSize={10}
              fontWeight="bold"
              tickLine={false}
            />

            <YAxis
              yAxisId="left"
              stroke="#64748b"
              fontSize={10}
              fontWeight="bold"
              tickLine={false}
            />

            <YAxis
              yAxisId="right"
              orientation="right"
              stroke="#f43f5e"
              fontSize={10}
              fontWeight="black"
              domain={[0, 10]}
              tickLine={false}
            />

            <Tooltip content={<CustomTooltip />} />

            <Bar
              yAxisId="left"
              dataKey="Запитувано (Треба)"
              fill="#e2e8f0"
              radius={[6, 6, 0, 0]}
              barSize={28}
            />

            <Bar
              yAxisId="left"
              dataKey="Виділено (Дали)"
              fill="#2563eb"
              radius={[6, 6, 0, 0]}
              barSize={18}
              style={{ transform: 'translateX(5px)' }}
            />

            <Line
              yAxisId="right"
              type="monotone"
              dataKey="Пріоритет заявки"
              stroke="#f43f5e"
              strokeWidth={3}
              dot={{ fill: '#f43f5e', strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6, strokeWidth: 0 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default DistributionChart;