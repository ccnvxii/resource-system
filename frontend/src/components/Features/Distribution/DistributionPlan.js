import React, { useState, useMemo } from 'react';
import {
  CheckCircle2,
  PieChart,
  Download,
  Zap,
  MapPin,
  Package,
  LayoutGrid
} from '../../UI/icons';
import { exportPlanToExcel } from '../../../utils/excelExport';
import DistributionCard from './DistributionCard';

const DistributionPlan = ({ plan, purposeMap, strategy = 'fairness' }) => {
  // Стан для групування: 'destination' (по поїздці), 'resource' (по ресурсу), 'all' (всі картки)
  const [groupBy, setGroupBy] = useState('destination');

  const groupedData = useMemo(() => {
    if (!plan || !plan.items) return {};
    if (groupBy === 'destination') {
      const groups = {};
      plan.items.forEach(item => {
        const key = item.city || item.warehouse_address || 'Не вказано адресу';
        if (!groups[key]) groups[key] = [];
        groups[key].push(item);
      });
      return groups;
    } else if (groupBy === 'resource') {
      const groups = {};
      plan.items.forEach(item => {
        const key = item.resource_name || 'Невідомий ресурс';
        if (!groups[key]) groups[key] = [];
        groups[key].push(item);
      });
      return groups;
    }
    return {};
  }, [plan, groupBy]);

  if (!plan || !plan.items || plan.items.length === 0) return null;

  // Змінні для динамічного стилювання шапки в залежності від алгоритму
  const isTriage = strategy === 'triage';
  const headerIcon = isTriage ? <Zap className="text-white" size={24} /> : <PieChart className="text-white" size={24} />;
  const headerBgColor = isTriage ? 'bg-red-600 shadow-red-100' : 'bg-blue-600 shadow-blue-100';
  const algorithmName = isTriage ? 'Алгоритм екстреного тріажу (Жорсткий пріоритет)' : 'Алгоритм лексикографічного розподілу (Fairness)';
  const exportBtnColor = isTriage ? 'text-red-600' : 'text-blue-600';

  return (
    <div className={`animate-fade-in-up bg-slate-50 rounded-2xl sm:rounded-3xl border-2 p-4 sm:p-6 md:p-8 mb-10 text-left space-y-6 ${isTriage ? 'border-red-100' : 'border-slate-200'}`}>

      {/* Шапка */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-200 pb-6">
        <div className="flex items-center gap-3">
          <div className={`${headerBgColor} p-2.5 rounded-xl shadow-lg shrink-0`}>
            {headerIcon}
          </div>
          <div>
            <h3 className="text-xl sm:text-2xl font-black text-slate-800 tracking-tight">Результати оптимізації розподілу</h3>
            <p className={`text-xs font-bold uppercase tracking-widest ${isTriage ? 'text-red-500' : 'text-slate-500'}`}>
                {algorithmName}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 sm:gap-3 w-full md:w-auto">
          {/* ВИКЛИК ЗОВНІШНЬОЇ ФУНКЦІЇ ЕКСПОРТУ */}
          <button onClick={() => exportPlanToExcel(plan, strategy)} className="flex items-center justify-center gap-2 px-4 sm:px-5 py-2.5 bg-white border-2 border-slate-200 rounded-xl font-black text-[11px] uppercase text-slate-600 hover:bg-slate-100 hover:border-slate-300 transition-all shadow-sm active:scale-95 flex-1 md:flex-none">
            <Download size={16} className={exportBtnColor} /> Експорт (.xlsx)
          </button>
          <span className="flex items-center justify-center gap-2 text-xs sm:text-sm font-bold bg-white text-slate-700 px-3 sm:px-4 py-2 rounded-xl border border-slate-200 shadow-sm whitespace-nowrap">
            <CheckCircle2 size={16} className="text-green-500" /> {plan.items.length} операцій
          </span>
        </div>
      </div>

      {/*<DistributionChart items={plan.items} />*/}

      {/* ПАНЕЛЬ ПЕРЕМИКАННЯ КНОПОК ГРУПУВАННЯ */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-2 pt-2 border-t border-slate-200">
        <span className="text-xs font-black uppercase tracking-wider text-slate-400">Групувати:</span>

        <div className="grid grid-cols-3 gap-1 bg-slate-200/60 p-1 rounded-xl w-full sm:w-auto">
          <button
            onClick={() => setGroupBy('destination')}
            className={`flex items-center justify-center gap-1.5 px-2.5 sm:px-4 py-1.5 sm:py-2 rounded-lg font-black text-xs uppercase transition-all ${
              groupBy === 'destination'
                ? 'bg-slate-900 text-white shadow-md'
                : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
            }`}
          >
            <MapPin size={13} /> <span className="hidden sm:inline">За напрямком</span><span className="sm:hidden">Місто</span>
          </button>

          <button
            onClick={() => setGroupBy('resource')}
            className={`flex items-center justify-center gap-1.5 px-2.5 sm:px-4 py-1.5 sm:py-2 rounded-lg font-black text-xs uppercase transition-all ${
              groupBy === 'resource'
                ? 'bg-slate-900 text-white shadow-md'
                : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
            }`}
          >
            <Package size={13} /> <span className="hidden sm:inline">За ресурсом</span><span className="sm:hidden">Ресурс</span>
          </button>

          <button
            onClick={() => setGroupBy('all')}
            className={`flex items-center justify-center gap-1.5 px-2.5 sm:px-4 py-1.5 sm:py-2 rounded-lg font-black text-xs uppercase transition-all ${
              groupBy === 'all'
                ? 'bg-slate-900 text-white shadow-md'
                : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
            }`}
          >
            <LayoutGrid size={13} /> <span className="hidden sm:inline">Усі операції</span><span className="sm:hidden">Усі</span>
          </button>
        </div>
      </div>

      {/* ВІДОБРАЖЕННЯ ДАНИХ ЗАЛЕЖНО ВІД ВИБРАНОГО ГРУПУВАННЯ */}
      {groupBy === 'all' ? (
        // Режим: Всі картки підряд
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-6">
          {plan.items.map((item) => (
            <DistributionCard key={item.id} item={item} />
          ))}
        </div>
      ) : (
        // Режим: Згруповані блоки (по напрямку або по ресурсу)
        <div className="space-y-4 sm:space-y-6">
          {Object.entries(groupedData).map(([groupName, items]) => (
            <div key={groupName} className="bg-white rounded-2xl border border-slate-200 p-3.5 sm:p-5 shadow-sm space-y-3 sm:space-y-4">
              {/* Шапка групи */}
              <div className="flex justify-between items-center border-b border-slate-100 pb-2.5 sm:pb-3 gap-2">
                <h4 className="font-black text-slate-800 text-sm sm:text-base flex items-center gap-1.5 sm:gap-2 truncate">
                  {groupBy === 'destination' ? <MapPin size={16} className="text-blue-500 shrink-0" /> : <Package size={16} className="text-indigo-500 shrink-0" />}
                  <span className="truncate">{groupName}</span>
                </h4>
                <span className="text-[11px] sm:text-xs font-bold bg-slate-100 text-slate-600 px-2.5 sm:px-3 py-0.5 sm:py-1 rounded-full shrink-0">
                  {items.length} {items.length === 1 ? 'оп.' : 'оп.'}
                </span>
              </div>

              {/* Сітка карток всередині групи */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
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