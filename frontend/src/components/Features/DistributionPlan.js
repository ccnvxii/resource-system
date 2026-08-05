import React from 'react';
import {
  CheckCircle2,
  PieChart,
  Download,
  Zap
} from 'lucide-react';
import DistributionChart from '../UI/DistributionChart';
import { exportPlanToExcel } from './excelExport';
import DistributionCard from '../UI/DistributionCard';

const DistributionPlan = ({ plan, purposeMap, strategy = 'fairness' }) => {

  if (!plan || !plan.items || plan.items.length === 0) return null;

  // Змінні для динамічного стилювання шапки в залежності від алгоритму
  const isTriage = strategy === 'triage';
  const headerIcon = isTriage ? <Zap className="text-white" size={24} /> : <PieChart className="text-white" size={24} />;
  const headerBgColor = isTriage ? 'bg-red-600 shadow-red-100' : 'bg-blue-600 shadow-blue-100';
  const algorithmName = isTriage ? 'Алгоритм екстреного тріажу (Жорсткий пріоритет)' : 'Алгоритм лексикографічного розподілу (Fairness)';
  const exportBtnColor = isTriage ? 'text-red-600' : 'text-blue-600';

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

      {/* Картки */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {plan.items.map((item) => (
          <DistributionCard key={item.id} item={item} />
        ))}
      </div>
    </div>
  );
};

export default DistributionPlan;