import React, { useState } from 'react';
import { History, Package, Clock, Box, ChevronDown, ChevronUp, Layers, Download, MapPin, Home, ArrowRight } from '../../UI/icons';
import Modal from '../../UI/Modal';
import { exportLogPlanToExcel } from '../../../utils/excelExport';

const AdminLogs = ({ logs = [] }) => {
  // За замовчуванням журнал ПОВНІСТЮ ЗГОРНУТИЙ
  const [isJournalVisible, setIsJournalVisible] = useState(false);
  // За замовчуванням всі плани ЗГОРНУТІ
  const [expandedPlans, setExpandedPlans] = useState({});
  const [selectedLog, setSelectedLog] = useState(null);

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
        className="flex items-center justify-between p-3.5 sm:px-6 sm:py-4 bg-slate-800 rounded-2xl sm:rounded-3xl cursor-pointer hover:bg-slate-900 transition-all shadow-lg border border-slate-700 gap-2"
      >
        <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
          <div className="bg-blue-500 p-2 rounded-xl text-white shadow-inner shrink-0">
            <History size={18} />
          </div>
          <div className="min-w-0 text-left">
            <h3 className="font-black text-white uppercase text-xs tracking-wider leading-tight truncate">
              Журнал розподілу
            </h3>
            <p className="text-slate-400 text-[10px] font-bold uppercase mt-0.5 truncate">
              Система аудиту та логування
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
            <div className="hidden sm:block bg-slate-700/50 text-slate-400 px-3 py-1 rounded-full text-[9px] font-black uppercase border border-slate-600">
                {isJournalVisible ? 'Приховати історію' : 'Показати історію'}
            </div>
            <div className={`transition-transform duration-300 text-white p-1 rounded-lg ${isJournalVisible ? 'rotate-180' : ''}`}>
                <ChevronDown size={18} />
            </div>
        </div>
      </div>

      {/* ВМІСТ ЖУРНАЛУ */}
      <div className={`space-y-4 sm:space-y-6 overflow-hidden transition-all duration-500 ease-in-out ${isJournalVisible ? 'max-h-[5000px] opacity-100 mt-4 sm:mt-6' : 'max-h-0 opacity-0 pointer-events-none'}`}>

        {sortedPlanIds.length === 0 ? (
            <div className="bg-white rounded-2xl sm:rounded-[2rem] border-2 border-dashed border-slate-200 p-8 sm:p-10 text-center">
                <Layers className="mx-auto text-slate-200 mb-2" size={36} />
                <p className="text-slate-400 font-black text-xs uppercase tracking-widest">Дані про розподіл відсутні</p>
            </div>
        ) : (
            sortedPlanIds.map((planId) => {
                const planItems = groupedLogs[planId];
                const planDate = new Date(planItems[0].timestamp).toLocaleString('uk-UA');
                // Тепер за замовчуванням false (згорнуто)
                const isExpanded = !!expandedPlans[planId];

                return (
                <div key={planId} className="bg-white rounded-2xl sm:rounded-[2rem] border-2 border-slate-100 shadow-sm overflow-hidden transition-all hover:border-blue-200">
                    <div
                      onClick={(e) => togglePlan(planId, e)}
                      className="bg-slate-50/50 p-3.5 sm:p-5 border-b border-slate-100 flex justify-between items-center cursor-pointer hover:bg-slate-100/50 transition-colors gap-2"
                    >
                        <div className="flex items-center gap-2.5 sm:gap-4 min-w-0">
                            <div className="bg-slate-200 p-2 sm:p-2.5 rounded-xl text-slate-600 shadow-sm shrink-0">
                                <Box size={16} />
                            </div>
                            <div className="min-w-0 text-left">
                                <div className="flex items-center gap-2">
                                    <span className="text-[10px] font-black text-slate-400 uppercase tracking-tighter">План #{planId}</span>
                                    <span className="text-[10px] font-bold text-blue-600 md:hidden">• {planItems.length} оп.</span>
                                </div>
                                <h4 className="font-black text-slate-800 text-sm sm:text-base leading-tight truncate">Результат оптимізації</h4>
                                <div className="text-[10px] text-slate-400 md:hidden mt-0.5">{planDate}</div>
                            </div>
                        </div>

                        <div className="flex items-center gap-3 shrink-0">
                            <div className="hidden md:flex flex-col items-end">
                                <div className="flex items-center gap-1.5 text-slate-500 text-xs font-bold">
                                    <Clock size={12} className="text-blue-400" />
                                    {planDate}
                                </div>
                                <div className="text-[10px] font-black text-blue-600 uppercase tracking-widest">{planItems.length} операцій</div>
                            </div>
                            <button
                                onClick={(e) => { e.stopPropagation(); exportLogPlanToExcel(planId, planItems); }}
                                className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-xl text-xs font-medium bg-white border border-slate-200 text-slate-600 hover:text-blue-600 shadow-sm transition-colors active:scale-95"
                                title="Завантажити звіт розподілу (Excel)"
                                aria-label="Завантажити звіт розподілу"
                            >
                                <Download size={14} />
                                <span className="hidden sm:inline">Звіт</span>
                            </button>
                            <div className="bg-white p-1.5 sm:p-2 rounded-full border border-slate-200 text-slate-400">
                                {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                            </div>
                        </div>
                    </div>

                    <div className={`transition-all duration-300 overflow-hidden ${isExpanded ? 'max-h-[3000px] opacity-100' : 'max-h-0 opacity-0'}`}>
                        {/* 1. Мобільний вигляд (акуратні картки для < md) */}
                        <div className="block md:hidden p-3 space-y-2 bg-slate-50/30">
                            {planItems.map((log) => (
                                <div key={log.id} onClick={() => setSelectedLog(log)} className="bg-white p-3 rounded-xl border border-slate-200 shadow-2xs text-left space-y-1.5 cursor-pointer active:bg-slate-50">
                                    <div className="flex items-center justify-between gap-2">
                                        <div className="flex items-center gap-1.5 min-w-0">
                                            <Package size={14} className="text-blue-500 shrink-0" />
                                            <span className="text-xs font-black text-slate-800 truncate">{log.resource_name}</span>
                                        </div>
                                        <span className="inline-flex items-center gap-0.5 bg-blue-50 text-blue-700 px-2 py-0.5 rounded-md font-black text-xs border border-blue-100 shrink-0">
                                            +{Math.round(log.amount)} {log.unit || 'од.'}
                                        </span>
                                    </div>
                                    <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-100">
                                        <span className="font-bold text-slate-700 truncate max-w-[150px]">{log.user_full_name}</span>
                                        <span className="text-slate-400 text-[10px] uppercase font-bold truncate max-w-[120px]">{log.warehouse_name}</span>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* 2. Десктопний вигляд (таблиця для >= md) */}
                        <div className="hidden md:block overflow-x-auto">
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
                                        <tr key={log.id} onClick={() => setSelectedLog(log)} className="hover:bg-blue-50/20 transition-colors group cursor-pointer">
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

      <Modal
        isOpen={!!selectedLog}
        onClose={() => setSelectedLog(null)}
        title={selectedLog ? selectedLog.resource_name : ''}
        subtitle={selectedLog ? `План #${selectedLog.plan_id} • Операція #${selectedLog.id}` : ''}
        icon={Package}
        maxWidth="max-w-lg"
      >
        {selectedLog && (
          <div className="space-y-4 text-left">
            <div className="flex items-center justify-between bg-blue-50 border border-blue-100 rounded-2xl p-4">
              <span className="text-xs font-medium text-blue-600 uppercase">Виділено</span>
              <span className="text-xl font-bold text-blue-700">
                {Math.round(selectedLog.amount)} {selectedLog.unit || 'од.'}
                {selectedLog.quantity_requested ? (
                  <span className="text-xs font-medium text-slate-400"> з {selectedLog.quantity_requested}</span>
                ) : null}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto_1fr] items-stretch gap-3">
              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 space-y-1">
                <div className="flex items-center gap-1.5 text-[10px] font-medium uppercase text-slate-400">
                  <Home size={12} /> Звідки (склад)
                </div>
                <p className="font-bold text-slate-800 text-sm">{selectedLog.warehouse_name}</p>
                {selectedLog.warehouse_location && (
                  <p className="text-xs text-slate-500">{selectedLog.warehouse_location}</p>
                )}
              </div>
              <div className="hidden sm:flex items-center text-slate-300"><ArrowRight size={20} /></div>
              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 space-y-1">
                <div className="flex items-center gap-1.5 text-[10px] font-medium uppercase text-slate-400">
                  <MapPin size={12} /> Куди (отримувач)
                </div>
                <p className="font-bold text-slate-800 text-sm">{selectedLog.user_full_name}</p>
                <p className="text-xs text-slate-500">
                  {[selectedLog.city, selectedLog.warehouse_address].filter(Boolean).join(', ') || 'Адресна доставка'}
                </p>
              </div>
            </div>

            <dl className="text-sm divide-y divide-slate-100 border border-slate-200 rounded-2xl px-4">
              {[
                ['Призначення', selectedLog.purpose_name],
                ['Граничний термін', selectedLog.due_date],
                ['Дата плану', selectedLog.timestamp ? new Date(selectedLog.timestamp).toLocaleString('uk-UA') : null],
                ['Користувач', selectedLog.username],
              ].filter(([, v]) => v).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-3 py-2.5">
                  <dt className="text-slate-400 font-medium">{k}</dt>
                  <dd className="text-slate-700 font-semibold text-right">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default AdminLogs;