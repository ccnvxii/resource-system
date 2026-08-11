import React from 'react';
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell
} from 'recharts';

const DistributionChart = ({ items = [] }) => {
  // Функція для визначення кольору залежно від рівня пріоритету (для групування)
  const getColorByPriority = (priority) => {
    if (priority >= 8.5) return '#ef4444'; // Критичний (Червоний - Військові)
    if (priority >= 7.0) return '#3b82f6'; // Високий (Синій - Лікарні)
    return '#f59e0b'; // Середній/Низький (Бурштиновий - ВПО)
  };

  const chartData = items.map(item => {
    let warehouseCity = '';
    if (item.warehouse_name) {
      const match = item.warehouse_name.match(/\((.*?)\)/);
      warehouseCity = match ? match[1] : item.warehouse_name.split(' ').pop();
    } else {
      warehouseCity = 'Склад';
    }

    const uniqueKey = `${item.resource_name} (##${item.id})`;

    const shortResource = item.resource_name.length > 12
      ? `${item.resource_name.substring(0, 10)}...`
      : item.resource_name;
    const axisDisplayName = `${shortResource} (${warehouseCity})`;
    const priorityVal = item.priority ? parseFloat(Number(item.priority).toFixed(1)) : 0.0;

    return {
      id: item.id,
      key: uniqueKey,
      displayName: axisDisplayName,
      fullName: item.resource_name,
      warehouse: item.warehouse_name || 'Не вказано',
      destination: item.city || 'Адресна доставка',
      'Запитувано (Треба)': item.quantity_requested ? Math.round(item.quantity_requested) : Math.round(item.amount),
      'Виділено (Дали)': Math.round(item.amount),
      'Пріоритет заявки': priorityVal,
      colorGroup: getColorByPriority(priorityVal), // Колір групи на основі пріоритету
      recipient: item.recipient_name
    };
  });

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-slate-900 text-white p-4 rounded-xl border border-slate-700 shadow-xl text-xs font-sans space-y-1.5 z-50 min-w-[220px]">
          <div className="flex justify-between items-center border-b border-slate-700 pb-1.5 mb-1.5">
            <span className="font-black text-blue-400 uppercase tracking-wider">Операція #{data.id}</span>
            <span
              className="font-black px-1.5 py-0.5 rounded text-[10px]"
              style={{ backgroundColor: `${data.colorGroup}20`, color: data.colorGroup }}
            >
              Пріоритет: {data['Пріоритет заявки']}
            </span>
          </div>
          <p className="font-bold text-slate-200">Ресурс: <span className="font-medium text-white">{data.fullName}</span></p>
          <p className="text-slate-400 font-medium">Джерело: <span className="text-slate-300">{data.warehouse}</span></p>
          <p className="text-slate-400 font-medium">Куди: <span className="text-blue-300 font-bold">{data.destination}</span></p>
          <p className="text-slate-400 font-medium">Отримувач: <span className="text-slate-300 font-mono">{data.recipient}</span></p>
          <hr className="border-slate-800 my-1.5" />
          <div className="space-y-1 font-sans">
            <div className="flex justify-between text-slate-300">
              <span>Запитувана потреба:</span>
              <span className="font-mono font-bold text-white">{data['Запитувано (Треба)']} од.</span>
            </div>
            <div className="flex justify-between text-blue-300">
              <span>Реально виділено:</span>
              <span className="font-mono font-black" style={{ color: data.colorGroup }}>{data['Виділено (Дали)']} од.</span>
            </div>
          </div>
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
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 bg-slate-200 rounded-sm"></span>Запитувано
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 bg-blue-600 rounded-sm"></span>Виділено (Колір групи)
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 bg-rose-500 rounded-full"></span>Пріоритет (0-10)
          </span>
        </div>
      </div>

      <div className="w-full h-72">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} barGap={4} margin={{ top: 20, right: 10, left: -20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />

            <XAxis
              dataKey="key"
              stroke="#64748b"
              fontSize={9}
              fontWeight="bold"
              tickLine={false}
              tickFormatter={(value) => {
                const found = chartData.find(d => d.key === value);
                return found ? found.displayName : value;
              }}
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

            <Tooltip content={<CustomTooltip />} cursor={{ fill: '#f8fafc', opacity: 0.5 }} />

            {/* Стовпчик "Запитувано" - стабільний фоновий сірий колір */}
            <Bar
              yAxisId="left"
              dataKey="Запитувано (Треба)"
              fill="#e2e8f0"
              radius={[4, 4, 0, 0]}
              barSize={14}
            />

            {/* Стовпчик "Виділено" - колір визначається динамічно для кожної комірки (Cell) */}
            <Bar
              yAxisId="left"
              dataKey="Виділено (Дали)"
              radius={[4, 4, 0, 0]}
              barSize={14}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.colorGroup} />
              ))}
            </Bar>

            {/* Лінія індексу пріоритету */}
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