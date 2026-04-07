import React, { useState } from 'react';
import {
  ListChecks,
  History,
  User,
  AlertCircle,
  Clock,
  CheckCircle2,
  Filter,
  Package
} from 'lucide-react';

const RequestList = ({ requests, requestTab, setRequestTab, purposeMap }) => {
  // Локальні стани для фільтрів
  const [statusFilter, setStatusFilter] = useState('all');
  const [resourceFilter, setResourceFilter] = useState('all');

  // 1. Базова фільтрація за вкладкою (Активні / Архів)
  const baseFiltered = requests.filter(r =>
    requestTab === 'active' ? r.status !== 'done' : r.status === 'done'
  );

  // 2. Унікальні назви ресурсів для випадаючого списку (тільки з поточних заявок)
  const availableResources = ['all', ...new Set(baseFiltered.map(r => r.resource_name))];

  // 3. Фінальна фільтрація за статусом та типом ресурсу
  const displayedRequests = baseFiltered.filter(r => {
    const matchStatus = statusFilter === 'all' || r.status === statusFilter;
    const matchResource = resourceFilter === 'all' || r.resource_name === resourceFilter;
    return matchStatus && matchResource;
  });

  const getStatusDetails = (status) => {
    switch (status) {
      case 'done':
        return { icon: <CheckCircle2 size={14} className="text-green-600" />, label: 'Виконано' };
      case 'partial':
        return { icon: <Clock size={14} className="text-amber-600" />, label: 'Частково' };
      default:
        return { icon: <AlertCircle size={14} className="text-blue-600" />, label: 'Нова' };
    }
  };

  return (
    <section className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-[600px]">
      {/* Шапка списку */}
      <div className="p-4 border-b border-slate-100 bg-slate-50/50 space-y-4">
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
          <div className="flex items-center gap-2 text-slate-800">
            <ListChecks size={20} className="text-blue-600" />
            <h2 className="text-lg font-bold">Черга заявок</h2>
          </div>

          <div className="flex bg-slate-200/50 p-1 rounded-xl">
            <button
              onClick={() => { setRequestTab('active'); setStatusFilter('all'); }}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${requestTab === 'active' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500'}`}
            >
              Активні <span className="bg-slate-200 px-1.5 py-0.5 rounded text-[10px]">{requests.filter(r => r.status !== 'done').length}</span>
            </button>
            <button
              onClick={() => { setRequestTab('history'); setStatusFilter('all'); }}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${requestTab === 'history' ? 'bg-white text-green-600 shadow-sm' : 'text-slate-500'}`}
            >
              <History size={14} /> Архів
            </button>
          </div>
        </div>

        {/* ПАНЕЛЬ ФІЛЬТРІВ */}
        <div className="grid grid-cols-2 gap-3 pb-1">
          {/* Фільтр по статусу (показуємо лише в активних) */}
          <div className="relative">
            <Filter size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              disabled={requestTab === 'history'}
              className="w-full text-[10px] pl-8 pr-2 py-2 rounded-lg border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500/20 font-bold uppercase tracking-tight disabled:bg-slate-100 disabled:text-slate-400"
            >
              <option value="all">Усі статуси</option>
              <option value="new">Тільки Нові</option>
              <option value="partial">Тільки Часткові</option>
            </select>
          </div>

          {/* Фільтр по ресурсу */}
          <div className="relative">
            <Package size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <select
              value={resourceFilter}
              onChange={(e) => setResourceFilter(e.target.value)}
              className="w-full text-[10px] pl-8 pr-2 py-2 rounded-lg border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500/20 font-bold uppercase tracking-tight"
            >
              <option value="all">Усі ресурси</option>
              {availableResources.filter(r => r !== 'all').map(res => (
                <option key={res} value={res}>{res}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Список карток */}
      <div className="overflow-y-auto flex-1 p-4 space-y-3 bg-slate-50/30 custom-scrollbar">
        {displayedRequests.map((req) => {
          const purposeData = purposeMap[req.purpose] || { label: req.purpose, icon: '❓', color: 'bg-gray-100' };
          const isHistory = req.status === 'done';
          const statusDetails = getStatusDetails(req.status);

          return (
            <div key={req.id} className={`bg-white p-4 rounded-2xl border ${isHistory ? 'border-slate-100 opacity-75' : 'border-slate-200 shadow-sm'} hover:shadow-md transition-all relative overflow-hidden group`}>
              <div className="absolute left-0 top-0 bottom-0 w-1.5" style={{ backgroundColor: isHistory ? '#10b981' : (req.priority >= 8 ? '#ef4444' : '#3b82f6') }}></div>

              <div className="flex justify-between items-start">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-lg ${purposeData.color}`}>
                      {purposeData.icon} {purposeData.label}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">ID: {req.id}</span>
                  </div>
                  <h3 className={`font-bold text-slate-800 ${isHistory && 'line-through'}`}>{req.resource_name}</h3>
                  <div className="flex items-center gap-1 text-xs text-slate-500">
                    <User size={12} /> <span>Від: {req.username}</span>
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Пріоритет</div>
                  <div className="text-xl font-black text-slate-700 leading-none">{Number(req.priority).toFixed(1)}</div>
                </div>
              </div>

              <div className="flex justify-between items-center mt-4 pt-3 border-t border-slate-50">
                <div className="flex items-center gap-1.5">
                  {statusDetails.icon}
                  <span className="text-[10px] font-bold uppercase text-slate-500">{statusDetails.label}</span>
                </div>
                <div className="text-sm font-mono font-bold">
                  <span className="text-blue-600">{Number(req.quantity_allocated).toFixed(0)}</span>
                  <span className="text-slate-300 mx-1">/</span>
                  <span className="text-slate-800">{Number(req.quantity_requested).toFixed(0)}</span>
                </div>
              </div>
            </div>
          );
        })}

        {displayedRequests.length === 0 && (
          <div className="text-center py-20 text-slate-400 italic text-sm flex flex-col items-center gap-2">
            <Filter size={24} className="opacity-20" />
            За вказаними фільтрами заявок не знайдено
          </div>
        )}
      </div>
    </section>
  );
};

export default RequestList;