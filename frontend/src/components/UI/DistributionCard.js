import React from 'react';
import {
  Database,
  User,
  Box,
  Fingerprint,
  MapPin,
  HelpCircle,
  Clock
} from 'lucide-react';
import { PURPOSE_MAP } from '../../constants/purposes';

const formatDate = (dateString) => {
  if (!dateString) return null;
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('uk-UA', { day: '2-digit', month: '2-digit', year: 'numeric' });
  } catch (e) {
    return dateString;
  }
};

const DistributionCard = ({ item }) => {
  const isHighPriority = item.priority >= 8;
  const purposeKey = item.purpose_code || item.purpose;
  const purposeData = PURPOSE_MAP[purposeKey] || {
      label: item.purpose_name || 'Інше',
      icon: <HelpCircle size={14} />,
      color: 'bg-slate-100 text-slate-800'
  };

  return (
    <div className="bg-white p-5 rounded-2xl border border-slate-200 hover:shadow-md transition-all flex flex-col justify-between group relative overflow-hidden animate-in fade-in zoom-in duration-300 shadow-sm">
      <div className="absolute left-0 top-0 bottom-0 w-1.5" style={{ backgroundColor: isHighPriority ? '#ef4444' : '#3b82f6' }}></div>

      <div>
        <div className="flex justify-between items-start mb-4">
          <div className="flex flex-col text-left flex-1">
            <div className="flex items-center gap-1.5 text-slate-400">
              <Fingerprint size={14} />
              <span className="text-[10px] font-mono font-bold uppercase">Операція #{item.id}</span>
            </div>
            <div className="flex flex-wrap items-center gap-2 mt-1.5">
              <span className={`flex items-center gap-1.5 text-[9px] font-black uppercase rounded-lg px-2 py-0.5 w-fit ${purposeData.color}`}>
                {purposeData.icon} <span>{purposeData.label}</span>
              </span>
              {item.due_date && (
                <span className="flex items-center gap-1 text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-100/60 text-[10px] font-black uppercase tracking-tight">
                  <Clock size={10} className="text-amber-500" /> <span>до {formatDate(item.due_date)}</span>
                </span>
              )}
            </div>
          </div>
          <div className="text-right ml-2">
            <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Пріоритет</div>
            <div className={`text-xl font-black leading-none ${isHighPriority ? 'text-red-500' : 'text-slate-700'}`}>
              {item.priority ? Number(item.priority).toFixed(1) : '0.0'}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between gap-4 mb-6 bg-slate-50/50 p-2.5 rounded-xl border border-slate-100">
          <div className="flex items-center gap-2 flex-1 min-w-0 text-left">
            <Box size={18} className="text-blue-500 shrink-0" />
            <h4 className="text-sm font-black text-slate-800 leading-tight truncate">{item.resource_name}</h4>
          </div>
          <div className="flex flex-col items-end shrink-0 min-w-[85px]">
            <span className="text-[8px] text-slate-400 font-black uppercase tracking-tight leading-none mb-1">Видано / Треба</span>
            <div className="font-mono bg-white px-2 py-1 rounded-lg border border-slate-200 shadow-sm w-full flex flex-col items-center">
              <div className="flex items-center justify-center gap-1">
                <span className="text-blue-600 font-black text-sm">{Math.round(item.amount)}</span>
                <span className="text-slate-300 text-xs font-light">/</span>
                <span className="text-slate-400 font-bold text-xs">{item.quantity_requested ? Math.round(item.quantity_requested) : Math.round(item.amount)}</span>
              </div>
              <span className="text-slate-400 font-medium text-[9px] font-sans mt-0.5 truncate max-w-[80px] text-center">{item.unit_name || 'од.'}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-3 pt-3 border-t border-slate-100 text-left">
        <div className="flex items-start gap-2.5">
          <div className="mt-0.5 text-slate-400"><Database size={13} /></div>
          <div className="flex flex-col w-full">
            <div className="flex justify-between items-center w-full">
                <span className="text-[9px] font-bold text-slate-400 uppercase tracking-tight leading-none mb-0.5">Джерело (Склад)</span>
                {item.total_available_at_source !== undefined && (
                    <span className="text-[9px] font-black text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded leading-none">
                        Всього: {Math.round(item.total_available_at_source)}
                    </span>
                )}
            </div>
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
            <span className="text-[9px] font-bold text-blue-500 uppercase tracking-tight leading-none mb-0.5">Куди поїде</span>
            <div className="bg-blue-50/50 px-2.5 py-1.5 rounded-xl border border-blue-100 w-full mt-0.5 space-y-0.5">
              <span className="font-black text-blue-900 text-xs block">{item.city || 'Місто не вказано'}</span>
              {item.warehouse_address && <span className="text-[11px] text-slate-600 font-medium block leading-tight">{item.warehouse_address}</span>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DistributionCard;