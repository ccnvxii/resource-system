import React, { useState } from 'react';
import {
  CheckCircle2,
  PieChart,
  Download,
  Zap,
  MapPin,
  Package,
  LayoutGrid
} from 'lucide-react';
import DistributionChart from './DistributionChart';
import { exportPlanToExcel } from '../../../utils/excelExport';
import DistributionCard from './DistributionCard';

const DistributionPlan = ({ plan, purposeMap, strategy = 'fairness' }) => {
  // Стан для групування: 'destination' (по поїздці), 'resource' (по ресурсу), 'all' (всі картки)
  const [groupBy, setGroupBy] = useState('destination');

  if (!plan || !plan.items || plan.items.length === 0) return null;

  // Змінні для динамічного стилювання шапки в залежності від алгоритму
  const isTriage = strategy === 'triage';
  const headerIcon = isTriage ? <Zap className="text-white" size={24} /> : <PieChart className="text-white" size={24} />;
  const headerBgColor = isTriage ? 'bg-red-600 shadow-red-100' : 'bg-blue-600 shadow-blue-100';
  const algorithmName = isTriage ? 'Алгоритм екстреного тріажу (Жорсткий пріоритет)' : 'Алгоритм лексикографічного розподілу (Fairness)';
  const exportBtnColor = isTriage ? 'text-red-600' : 'text-blue-600';

  // --- ЛОГІКА ГРУПУВАННЯ ---
  const getGroupedItems = () => {
    if (groupBy === 'destination') {
      // Групуємо по місту / адресі доставки (куди їде)
      const groups = {};
      plan.items.forEach(item => {
        const key = item.city || item.warehouse_address || 'Не вказано адресу';
        if (!groups[key]) groups[key] = [];
        groups[key].push(item);
      });
      return groups;
    } else if (groupBy === 'resource') {
      // Групуємо по назві ресурсу
      const groups = {};
      plan.items.forEach(item => {
        const key = item.resource_name || 'Невідомий ресурс';
        if (!groups[key]) groups[key] = [];
        groups[key].push(item);
      });
      return groups;
    }
    return null;
  };

  const groupedData = getGroupedItems();

  return (
    <div className={`animate-fade-in-up bg-slate-50 rounded-3xl border-2 p-6 md:p-8 mb-10 text-left space-y-6 ${isTriage ? 'border-red-100' : 'border-slate-200'}`}>

      {/* Шапка */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-200 pb-6">
        <div className="flex items-center gap-3">
          <div className={`${headerBgColor} p-2.5 rounded-xl shadow-lg`}>
            {headerIcon}
          </div>
          <div>
            <h3 className="text-2xl font-black text-slate-800 tracking-tight">Результати оптимізації розподілу</h3>
            <p className={`text-xs font-bold uppercase tracking-widest ${isTriage ? 'text-red-500' : 'text-slate-500'}`}>
                {algorithmName}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          {/* ВИКЛИК ЗОВНІШНЬОЇ ФУНКЦІЇ ЕКСПОРТУ */}
          <button onClick={() => exportPlanToExcel(plan, strategy)} className="flex items-center justify-center gap-2 px-5 py-2.5 bg-white border-2 border-slate-200 rounded-xl font-black text-[11px] uppercase text-slate-600 hover:bg-slate-100 hover:border-slate-300 transition-all shadow-sm active:scale-95 flex-1 md:flex-none">
            <Download size={16} className={exportBtnColor} /> Експорт (.xlsx)
          </button>
          <span className="flex items-center gap-2 text-sm font-bold bg-white text-slate-700 px-4 py-2 rounded-xl border border-slate-200 shadow-sm whitespace-nowrap">
            <CheckCircle2 size={16} className="text-green-500" /> {plan.items.length} операцій
          </span>
        </div>
      </div>

      <DistributionChart items={plan.items} />

      {/* ПАНЕЛЬ ПЕРЕМИКАННЯ КНОПОК ГРУПУВАННЯ */}
      <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-200">
        <span className="text-xs font-black uppercase tracking-wider text-slate-400 mr-2">Групувати:</span>

        <button
          onClick={() => setGroupBy('destination')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl font-black text-xs uppercase transition-all ${
            groupBy === 'destination'
              ? 'bg-slate-900 text-white shadow-md'
              : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-100'
          }`}
        >
          <MapPin size={14} /> За напрямком (куди їде)
        </button>

        <button
          onClick={() => setGroupBy('resource')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl font-black text-xs uppercase transition-all ${
            groupBy === 'resource'
              ? 'bg-slate-900 text-white shadow-md'
              : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-100'
          }`}
        >
          <Package size={14} /> За ресурсом
        </button>

        <button
          onClick={() => setGroupBy('all')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl font-black text-xs uppercase transition-all ${
            groupBy === 'all'
              ? 'bg-slate-900 text-white shadow-md'
              : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-100'
          }`}
        >
          <LayoutGrid size={14} /> Всі операції (списком)
        </button>
      </div>

      {/* ВІДОБРАЖЕННЯ ДАНИХ ЗАЛЕЖНО ВІД ВИБРАНОГО ГРУПУВАННЯ */}
      {groupBy === 'all' ? (
        // Режим: Всі картки підряд
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {plan.items.map((item) => (
            <DistributionCard key={item.id} item={item} />
          ))}
        </div>
      ) : (
        // Режим: Згруповані блоки (по напрямку або по ресурсу)
        <div className="space-y-8">
          {Object.entries(groupedData).map(([groupName, items]) => (
            <div key={groupName} className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
              {/* Шапка групи */}
              <div className="flex justify-between items-center border-b border-slate-100 pb-3">
                <h4 className="font-black text-slate-800 text-base flex items-center gap-2">
                  {groupBy === 'destination' ? <MapPin size={18} className="text-blue-500" /> : <Package size={18} className="text-indigo-500" />}
                  {groupName}
                </h4>
                <span className="text-xs font-bold bg-slate-100 text-slate-600 px-3 py-1 rounded-full">
                  {items.length} {items.length === 1 ? 'операція' : items.length < 5 ? 'операції' : 'операцій'}
                </span>
              </div>

              {/* Сітка карток всередині групи */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {items.map((item) => (
                  <DistributionCard key={item.id} item={item} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

    </div>
  );
};

export default DistributionPlan;