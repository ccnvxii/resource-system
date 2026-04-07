import React from 'react';
import {
  CheckCircle2,
  Database,
  User,
  Box,
  Fingerprint,
  PieChart
} from 'lucide-react';

const DistributionPlan = ({ plan, purposeMap }) => (
  <div className="animate-fade-in-up bg-slate-50 rounded-3xl border-2 border-slate-200 p-6 md:p-8 mb-10">
    {/* Заголовок плану */}
    <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
      <div className="flex items-center gap-3">
        <div className="bg-blue-600 p-2.5 rounded-xl shadow-lg shadow-blue-100">
          <PieChart className="text-white" size={24} />
        </div>
        <div>
          <h3 className="text-2xl font-black text-slate-800 tracking-tight">
            Результати оптимізації розподілу
          </h3>
          <p className="text-slate-500 text-xs font-bold uppercase tracking-widest">
            Ресурси розподілено згідно з матрицею пріоритетів
          </p>
        </div>
      </div>
      <span className="flex items-center gap-2 text-sm font-bold bg-white text-slate-700 px-4 py-2 rounded-xl border border-slate-200 shadow-sm">
        <CheckCircle2 size={16} className="text-green-500" />
        {plan.items.length} операцій
      </span>
    </div>

    {/* Сітка результатів */}
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {plan.items.map((item) => {
        const purposeInfo = purposeMap[item.purpose] || { label: item.purpose, icon: '📦', color: 'bg-gray-100' };

        return (
          <div
            key={item.id}
            className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200 hover:border-blue-300 transition-all flex flex-col justify-between group"
          >
            {/* Верхня частина: Ресурс та кількість */}
            <div>
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-1.5 text-slate-400">
                  <Fingerprint size={14} />
                  <span className="text-[10px] font-mono font-bold uppercase">Операція #{item.id}</span>
                </div>
                <div className="bg-blue-50 text-blue-700 px-3 py-1 rounded-lg font-black text-lg border border-blue-100">
                  {Number(item.amount).toFixed(0)}
                </div>
              </div>

              <div className="flex items-center gap-3 mb-6">
                <Box size={20} className="text-blue-500" />
                <h4 className="text-lg font-extrabold text-slate-800 leading-tight">
                  {item.resource_name}
                </h4>
              </div>
            </div>

            {/* Деталі розподілу */}
            <div className="space-y-4 pt-4 border-t border-slate-100">
              {/* Джерело ресурсу */}
              <div className="flex items-start gap-3">
                <div className="mt-1 text-slate-400">
                  <Database size={14} />
                </div>
                <div className="flex flex-col">
                  <span className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter">Джерело (Склад)</span>
                  <span className="font-bold text-slate-700 text-sm">{item.warehouse_name}</span>
                </div>
              </div>

              {/* Отримувач (Заявка) */}
              <div className="flex items-start gap-3">
                <div className="mt-1 text-slate-400">
                  <User size={14} />
                </div>
                <div className="flex flex-col">
                  <span className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter">Призначення (Заявник)</span>
                  <div className="flex flex-col gap-1 mt-0.5">
                    <span className="font-bold text-slate-800 text-sm leading-none">
                      {item.recipient_name}
                    </span>
                    <span className={`text-[9px] font-black px-2 py-0.5 rounded-md w-fit uppercase mt-1 ${purposeInfo.color}`}>
                      {purposeInfo.icon} {purposeInfo.label}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  </div>
);

export default DistributionPlan;