import React, { useState } from 'react';
import { History, Package, Clock, Box, ChevronDown, ChevronUp, Layers } from 'lucide-react';

const AdminLogs = ({ logs = [] }) => {
  // За замовчуванням журнал ПОВНІСТЮ ЗГОРНУТИЙ
  const [isJournalVisible, setIsJournalVisible] = useState(false);
  // За замовчуванням всі плани ЗГОРНУТІ
  const [expandedPlans, setExpandedPlans] = useState({});

  const groupedLogs = logs.reduce((acc, log) => {
    const planId = log.plan_id || 'Невідомий';
    if (!acc[planId]) acc[planId] = [];
    acc[planId].push(log);
    return acc;
  }, {});

  const sortedPlanIds = Object.keys(groupedLogs).sort((a, b) => b - a);

  const togglePlan = (planId, e) => {
    e.stopPropagation();
    setExpandedPlans(prev => ({
      ...prev,
      [planId]: !prev[planId]
    }));
  };

  return (
    <div className="space-y-4 animate-in fade-in duration-500 pb-10">
      {/* ГОЛОВНА ШАПКА ЖУРНАЛУ (Згорнута за замовчуванням) */}
      <div
        onClick={() => setIsJournalVisible(!isJournalVisible)}
        className="flex items-center justify-between px-6 py-4 bg-slate-800 rounded-3xl cursor-pointer hover:bg-slate-900 transition-all shadow-lg border border-slate-700"
      >
        <div className="flex items-center gap-3">
          <div className="bg-blue-500 p-2 rounded-xl text-white shadow-inner">
            <History size={20} />
          </div>
          <div>
            <h3 className="font-black text-white uppercase text-xs tracking-widest leading-none">
              Журнал автоматизованого розподілу
            </h3>
            <p className="text-slate-500 text-[10px] font-black uppercase mt-1">
              Система аудиту та логування сесій
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
            <div className="bg-slate-700/50 text-slate-400 px-3 py-1 rounded-full text-[9px] font-black uppercase border border-slate-600">
                {isJournalVisible ? 'Приховати історію' : 'Показати історію'}
            </div>
            <div className={`transition-transform duration-300 ${isJournalVisible ? 'rotate-180' : ''}`}>
                <ChevronDown className="text-white" size={20} />
            </div>
        </div>
      </div>

      {/* ВМІСТ ЖУРНАЛУ */}
      <div className={`space-y-6 overflow-hidden transition-all duration-500 ease-in-out ${isJournalVisible ? 'max-h-[5000px] opacity-100 mt-6' : 'max-h-0 opacity-0 pointer-events-none'}`}>

        {sortedPlanIds.length === 0 ? (
            <div className="bg-white rounded-[2rem] border-2 border-dashed border-slate-200 p-10 text-center">
                <Layers className="mx-auto text-slate-200 mb-2" size={40} />
                <p className="text-slate-400 font-black text-xs uppercase tracking-widest">Дані про розподіл відсутні</p>
            </div>
        ) : (
            sortedPlanIds.map((planId) => {
                const planItems = groupedLogs[planId];
                const planDate = new Date(planItems[0].timestamp).toLocaleString('uk-UA');
                // Тепер за замовчуванням false (згорнуто)
                const isExpanded = !!expandedPlans[planId];

                return (
                <div key={planId} className="bg-white rounded-[2rem] border-2 border-slate-100 shadow-sm overflow-hidden transition-all hover:border-blue-200">
                    <div
                      onClick={(e) => togglePlan(planId, e)}
                      className="bg-slate-50/50 p-5 border-b border-slate-100 flex justify-between items-center cursor-pointer hover:bg-slate-100/50 transition-colors"
                    >
                        <div className="flex items-center gap-4">
                            <div className="bg-slate-200 p-2.5 rounded-xl text-slate-600 shadow-sm transition-colors group-hover:bg-blue-600 group-hover:text-white">
                                <Box size={18} />
                            </div>
                            <div>
                                <div className="text-[10px] font-black text-slate-400 uppercase tracking-tighter leading-none">План #{planId}</div>
                                <h4 className="font-black text-slate-800 text-lg leading-tight">Результат оптимізації</h4>
                            </div>
                        </div>

                        <div className="flex items-center gap-4">
                            <div className="hidden md:flex flex-col items-end">
                                <div className="flex items-center gap-1.5 text-slate-500 text-xs font-bold">
                                    <Clock size={12} className="text-blue-400" />
                                    {planDate}
                                </div>
                                <div className="text-[10px] font-black text-blue-600 uppercase tracking-widest">{planItems.length} операцій</div>
                            </div>
                            <div className="bg-white p-2 rounded-full border border-slate-200 text-slate-400">
                                {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                            </div>
                        </div>
                    </div>

                    <div className={`transition-all duration-300 overflow-hidden ${isExpanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}`}>
                        <div className="overflow-x-auto">
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="bg-slate-50/30">
                                        <th className="px-6 py-4 text-[10px] font-black uppercase text-slate-400 tracking-widest">Отримувач</th>
                                        <th className="px-6 py-4 text-[10px] font-black uppercase text-slate-400 tracking-widest">Ресурс</th>
                                        <th className="px-6 py-4 text-[10px] font-black uppercase text-slate-400 tracking-widest">Склад</th>
                                        <th className="px-6 py-4 text-[10px] font-black uppercase text-slate-400 tracking-widest text-right">Кількість</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-50">
                                    {planItems.map((log) => (
                                        <tr key={log.id} className="hover:bg-blue-50/20 transition-colors group">
                                            <td className="px-6 py-4">
                                                <span className="text-sm font-bold text-slate-700 group-hover:text-blue-700">{log.user_full_name}</span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-2">
                                                    <Package size={14} className="text-blue-500" />
                                                    <span className="text-sm font-black text-slate-800">{log.resource_name}</span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-tight">{log.warehouse_name}</span>
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                <div className="inline-flex items-center gap-1 bg-blue-50 text-blue-700 px-3 py-1 rounded-lg font-black text-sm border border-blue-100">
                                                    +{Math.round(log.amount)}
                                                    <span className="text-[10px] font-bold uppercase opacity-60 ml-1">{log.unit || 'од.'}</span>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
                );
            })
        )}
      </div>
    </div>
  );
};

export default AdminLogs;