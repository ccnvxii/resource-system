// src/components/Features/DistributionPlan.js
import React from 'react';
import {
  CheckCircle2,
  Database,
  User,
  Box,
  Fingerprint,
  PieChart,
  Download,
  MapPin,
  HelpCircle
} from 'lucide-react';
import * as XLSX from 'xlsx';
import { PURPOSE_MAP } from '../../constants/purposes';
// Імпортуємо новий автономний компонент графіка
import DistributionChart from './DistributionChart';

const DistributionPlan = ({ plan, purposeMap }) => {

  const exportPlanToExcel = () => {
    if (!plan || !plan.items || plan.items.length === 0) return;

    const dataToExport = plan.items.map(item => {
      const purposeKey = item.purpose_code || item.purpose;
      const purposeMeta = PURPOSE_MAP[purposeKey] || { label: item.purpose_name || 'Інше' };

      return {
        "ID Operational": item.id,
        "Пріоритет": item.priority ? Number(item.priority).toFixed(1) : '0.0',
        "Ресурс": item.resource_name,
        "Виділено": Math.round(item.amount),
        "Запитувано": item.quantity_requested ? Math.round(item.quantity_requested) : 0,
        "Одиниця": item.unit_name || 'од.',
        "Склад-джерело": item.warehouse_name,
        "Отримувач": item.recipient_name,
        "Пункт призначення": `${item.city || ''} ${item.warehouse_address || ''}`.trim() || 'Адресна доставка',
        "Призначення": purposeMeta.label
      };
    });

    const ws = XLSX.utils.json_to_sheet(dataToExport);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Результати розподілу");

    const fileName = `Distribution_Plan_${plan.id || 'new'}.xlsx`;
    XLSX.writeFile(wb, fileName);
  };

  if (!plan || !plan.items || plan.items.length === 0) return null;

  return (
    <div className="animate-fade-in-up bg-slate-50 rounded-3xl border-2 border-slate-200 p-6 md:p-8 mb-10 text-left space-y-6">

      {/* Шапка компонента */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-200 pb-6">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 p-2.5 rounded-xl shadow-lg shadow-blue-100">
            <PieChart className="text-white" size={24} />
          </div>
          <div>
            <h3 className="text-2xl font-black text-slate-800 tracking-tight">
              Результати оптимізації розподілу
            </h3>
            <p className="text-slate-500 text-xs font-bold uppercase tracking-widest">
              Алгоритм Weighted Max-Min Fairness за матрицею пріоритетів
            </p>
          </div>
        </div>

        {/* Статистика та Експорт */}
        <div className="flex items-center gap-3 w-full md:w-auto">
          <button
            onClick={exportPlanToExcel}
            className="flex items-center justify-center gap-2 px-5 py-2.5 bg-white border-2 border-slate-200 rounded-xl font-black text-[11px] uppercase text-slate-600 hover:bg-slate-100 hover:border-slate-300 transition-all shadow-sm active:scale-95 flex-1 md:flex-none"
          >
            <Download size={16} className="text-blue-600" />
            Експорт плану (.xlsx)
          </button>
          <span className="flex items-center gap-2 text-sm font-bold bg-white text-slate-700 px-4 py-2 rounded-xl border border-slate-200 shadow-sm whitespace-nowrap">
            <CheckCircle2 size={16} className="text-green-500" />
            {plan.items.length} операцій
          </span>
        </div>
      </div>

      {/* Вбудовуємо автономний графік, передаючи йому масив елементів */}
      <DistributionChart items={plan.items} />

      {/* Сітка з картками розподілу */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {plan.items.map((item) => {
          const isHighPriority = item.priority >= 8;
          const purposeKey = item.purpose_code || item.purpose;
          const purposeData = PURPOSE_MAP[purposeKey] || {
            label: item.purpose_name || 'Інше',
            icon: <HelpCircle size={14} />,
            color: 'bg-slate-100 text-slate-800'
          };

          return (
            <div
              key={item.id}
              className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200 hover:shadow-md transition-all flex flex-col justify-between group relative overflow-hidden animate-in fade-in zoom-in duration-300"
            >
              <div className="absolute left-0 top-0 bottom-0 w-1.5" style={{ backgroundColor: isHighPriority ? '#ef4444' : '#3b82f6' }}></div>

              <div>
                <div className="flex justify-between items-start mb-4">
                  <div className="flex flex-col text-left">
                    <div className="flex items-center gap-1.5 text-slate-400">
                      <Fingerprint size={14} />
                      <span className="text-[10px] font-mono font-bold uppercase">Операція #{item.id}</span>
                    </div>
                    <span className={`flex items-center gap-1.5 text-[9px] font-black uppercase rounded-lg px-2 py-0.5 w-fit mt-1.5 ${purposeData.color}`}>
                      {purposeData.icon}
                      <span>{purposeData.label}</span>
                    </span>
                  </div>

                  <div className="text-right">
                    <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Пріоритет</div>
                    <div className={`text-xl font-black leading-none ${isHighPriority ? 'text-red-500' : 'text-slate-700'}`}>
                      {item.priority && !isNaN(item.priority) ? Number(item.priority).toFixed(1) : '0.0'}
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-3 mb-6 bg-slate-50/50 p-2.5 rounded-xl border border-slate-100">
                  <div className="flex items-center gap-2">
                    <Box size={18} className="text-blue-500" />
                    <h4 className="text-sm font-black text-slate-800 leading-tight">{item.resource_name}</h4>
                  </div>

                  <div className="flex flex-col items-end">
                    <span className="text-[9px] text-slate-400 font-black uppercase tracking-tight leading-none mb-1">Видано / Треба</span>
                    <div className="font-mono flex items-center gap-1.5 bg-white px-2.5 py-1 rounded-lg border border-slate-200 shadow-sm">
                      <span className="text-blue-600 font-black text-base">{Math.round(item.amount)}</span>
                      <span className="text-slate-300 text-sm font-light">/</span>
                      <span className="text-slate-400 font-bold text-xs">
                        {item.quantity_requested ? Math.round(item.quantity_requested) : Math.round(item.amount)}
                      </span>
                      <span className="text-slate-400 text-[9px] font-medium ml-0.5">{item.unit_name || 'од.'}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-3 pt-3 border-t border-slate-100 text-left">
                <div className="flex items-start gap-2.5">
                  <div className="mt-0.5 text-slate-400"><Database size={13} /></div>
                  <div className="flex flex-col">
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-tight leading-none mb-0.5">Джерело (Склад)</span>
                    <span className="font-bold text-slate-700 text-xs">{item.warehouse_name}</span>
                  </div>
                </div>

                <div className="flex items-start gap-2.5">
                  <div className="mt-0.5 text-slate-400"><User size={13} /></div>
                  <div className="flex flex-col">
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-tight leading-none mb-0.5">Отримувач</span>
                    <span className="font-bold text-slate-800 text-xs">{item.recipient_name}</span>
                  </div>
                </div>

                <div className="flex items-start gap-2.5">
                  <div className="mt-0.5 text-blue-500"><MapPin size={13} /></div>
                  <div className="flex flex-col w-full">
                    <span className="text-[9px] font-bold text-blue-500 uppercase tracking-tight leading-none mb-0.5">Куди поїде ресурс</span>
                    <div className="bg-blue-50/50 px-2.5 py-1.5 rounded-xl border border-blue-100 w-full mt-0.5 space-y-0.5">
                      <span className="font-black text-blue-900 text-xs block">{item.city || 'Місто не вказано'}</span>
                      {item.warehouse_address && <span className="text-[11px] text-slate-600 font-medium block leading-tight">{item.warehouse_address}</span>}
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
};

export default DistributionPlan;