// src/components/Features/RequestList.js
import React, {useState} from 'react';
import {
    ListChecks, History, User, AlertCircle, Clock,
    CheckCircle2, Filter, Package, Edit3, Check, X, MapPin, Inbox
} from 'lucide-react';
import api from '../../services/api';

const RequestList = ({requests = [], purposeMap = {}, onRefresh, currentUser}) => {
    const [requestTab, setRequestTab] = useState('active');
    const [statusFilter, setStatusFilter] = useState('all');
    const [resourceFilter, setResourceFilter] = useState('all');

    const [editingId, setEditingId] = useState(null);
    const [editValue, setEditValue] = useState("");

    const isAdmin = currentUser?.is_admin;

    // 1. Базова фільтрація за вкладками
    const baseFiltered = requests.filter(r =>
        requestTab === 'active' ? r.status !== 'done' : r.status === 'done'
    );

    // 2. Додаткова фільтрація
    const displayedRequests = baseFiltered.filter(r => {
        const matchStatus = statusFilter === 'all' || r.status === statusFilter;
        const matchResource = resourceFilter === 'all' || r.resource_name === resourceFilter;
        return matchStatus && matchResource;
    });

    const handleStartEdit = (req) => {
        setEditingId(req.id);
        setEditValue(Math.round(req.quantity_requested).toString());
    };

    const handleSaveEdit = async (id) => {
        const finalValue = Math.round(Number(editValue));
        if (isNaN(finalValue)) return;
        setEditingId(null);
        try {
            await api.patch(`/requests/${id}/`, {quantity_requested: finalValue});
            if (onRefresh) onRefresh();
        } catch (e) {
            console.error("Помилка збереження:", e.response?.data || e.message);
            if (onRefresh) onRefresh();
        }
    };

    const getStatusDetails = (status) => {
        switch (status) {
            case 'done':
                return {icon: <CheckCircle2 size={14} className="text-green-600"/>, label: 'Виконано'};
            case 'partial':
                return {icon: <Clock size={14} className="text-amber-600"/>, label: 'Частково'};
            default:
                return {icon: <AlertCircle size={14} className="text-blue-600"/>, label: 'Нова'};
        }
    };

    // Форматування дати дедлайну
    const formatDate = (dateString) => {
        if (!dateString) return null;
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('uk-UA', { day: '2-digit', month: '2-digit', year: 'numeric' });
        } catch (e) {
            return dateString;
        }
    };

    // Компонент для "Порожнього стану"
    const EmptyState = ({message, type}) => (
        <div className="flex flex-col items-center justify-center h-full py-12 animate-in fade-in zoom-in duration-300">
            <div className={`p-4 rounded-full mb-4 ${type === 'active' ? 'bg-blue-50' : 'bg-slate-50'}`}>
                <Inbox size={48} className={type === 'active' ? 'text-blue-200' : 'text-slate-200'}/>
            </div>
            <p className="text-slate-400 font-bold text-sm uppercase tracking-widest">{message}</p>
        </div>
    );

    return (
        <section
            className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-[600px] animate-in fade-in duration-500">
            {/* ШАПКА */}
            <div className="p-4 border-b border-slate-100 bg-slate-50/50 space-y-4">
                <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
                    <div className="flex items-center gap-2 text-slate-800">
                        <ListChecks size={22} className="text-blue-600"/>
                        <h2 className="text-lg font-bold">Черга заявок</h2>
                    </div>
                    <div className="flex bg-slate-200/50 p-1 rounded-xl">
                        <button
                            onClick={() => {
                                setRequestTab('active');
                                setStatusFilter('all');
                            }}
                            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${requestTab === 'active' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                        >
                            Активні <span
                            className="bg-slate-200 px-1.5 py-0.5 rounded text-[10px]">{requests.filter(r => r.status !== 'done').length}</span>
                        </button>
                        <button
                            onClick={() => {
                                setRequestTab('history');
                                setStatusFilter('all');
                            }}
                            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${requestTab === 'history' ? 'bg-white text-green-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                        >
                            <History size={14}/> Архів
                        </button>
                    </div>
                </div>
            </div>

            {/* СПИСОК АБО ПОРОЖНІЙ СТАН */}
            <div className="overflow-y-auto flex-1 p-4 space-y-3 bg-slate-50/30 custom-scrollbar">
                {displayedRequests.length > 0 ? (
                    displayedRequests.map((req) => {
                        const purposeData = purposeMap[req.purpose] || {label: 'Інше', icon: '📦', color: 'bg-gray-100'};
                        const isHistory = req.status === 'done';
                        const isEditing = editingId === req.id;
                        const statusDetails = getStatusDetails(req.status);
                        const stripeColor = isHistory ? '#10b981' : (isAdmin && Number(req.priority) >= 8 ? '#ef4444' : '#3b82f6');

                        return (
                            <div key={req.id}
                                 className={`bg-white p-4 rounded-2xl border ${isHistory ? 'border-slate-100 opacity-75' : 'border-slate-200 shadow-sm'} hover:shadow-md transition-all relative overflow-hidden group`}>
                                <div className="absolute left-0 top-0 bottom-0 w-1.5"
                                     style={{backgroundColor: stripeColor}}></div>
                                <div className="flex justify-between items-start">
                                    <div className="space-y-1 flex-1">
                                        <span
                                            className={`flex w-fit items-center gap-1.5 text-[10px] font-black uppercase px-2 py-0.5 rounded-lg ${purposeData.color}`}>
                                            {purposeData.icon} {purposeData.label}
                                        </span>
                                        <h3 className={`font-bold text-lg text-slate-800 ${isHistory && 'line-through opacity-50'}`}>{req.resource_name}</h3>

                                        {/* КОМПАКТНИЙ ГОРИЗОНТАЛЬНИЙ БЛОК: ЗАЯВНИК + ТЕРМІНОВОСТЬ */}
                                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500 font-medium">
                                            <div className="flex items-center gap-1">
                                                <User size={12} className="opacity-50"/>
                                                <span>{req.user_full_name || req.username}</span>
                                            </div>
                                            {req.due_date && (
                                                <div className="flex items-center gap-1 text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-100/60 text-[11px] font-bold">
                                                    <Clock size={11} className="text-amber-500"/>
                                                    <span>до {formatDate(req.due_date)}</span>
                                                </div>
                                            )}
                                        </div>

                                        {req.city && (
                                            <div
                                                className="flex items-center gap-1 text-[11px] text-blue-700 font-bold bg-blue-50 w-fit px-1.5 py-0.5 rounded-md mt-1">
                                                <MapPin size={10} className="text-blue-500"/>
                                                <span>{req.city}</span>
                                            </div>
                                        )}
                                    </div>
                                    {isAdmin && (
                                        <div className="text-right ml-2">
                                            <div className="text-[10px] text-slate-400 font-bold uppercase">Пріоритет</div>
                                            <div
                                                className={`text-xl font-black ${!isHistory && Number(req.priority) >= 8 ? 'text-red-500' : 'text-slate-700'}`}>
                                                {Number(req.priority).toFixed(1)}
                                            </div>
                                        </div>
                                    )}
                                </div>

                                <div className="flex justify-between items-center mt-4 pt-3 border-t border-slate-50">
                                    <div className="flex items-center gap-1.5">
                                        {statusDetails.icon}
                                        <span
                                            className="text-[10px] font-bold uppercase text-slate-500">{statusDetails.label}</span>
                                    </div>
                                    <div className="relative flex items-center justify-end min-w-[140px] h-10">
                                        {isEditing ? (
                                            <div
                                                className="flex items-center gap-1 animate-in fade-in zoom-in duration-200 h-full">
                                                <div className="flex flex-col items-end">
                                                    <span
                                                        className="text-[9px] text-blue-500 font-black uppercase leading-none mb-1">Потреба</span>
                                                    <input
                                                        autoFocus
                                                        type="number"
                                                        value={editValue}
                                                        onChange={(e) => setEditValue(e.target.value.replace(/[^0-9]/g, ''))}
                                                        className="w-16 h-7 p-1 bg-slate-50 border border-blue-400 rounded-lg text-right font-mono text-lg font-black text-blue-600 outline-none"
                                                    />
                                                </div>
                                                <div className="flex gap-1 h-7 mt-3">
                                                    <button onClick={() => handleSaveEdit(req.id)}
                                                            className="w-8 h-full flex items-center justify-center bg-green-500 text-white rounded-md shadow-sm">
                                                        <Check size={16} strokeWidth={3}/>
                                                    </button>
                                                    <button onClick={() => setEditingId(null)}
                                                            className="w-8 h-full flex items-center justify-center bg-slate-200 text-slate-600 rounded-md">
                                                        <X size={16} strokeWidth={3}/>
                                                    </button>
                                                </div>
                                            </div>
                                        ) : (
                                            <div
                                                className="relative flex items-center justify-end w-full group/btn h-full">
                                                <div
                                                    className={`flex flex-col items-end transition-opacity duration-300 ${!isHistory && 'group-hover/btn:opacity-0'}`}>
                                                    <span
                                                        className="text-[9px] text-slate-400 font-black uppercase leading-none mb-0.5">Потреба</span>
                                                    <div
                                                        className="text-lg font-mono font-black flex items-center gap-1">
                                                        <span
                                                            className="text-blue-600">{Number(req.quantity_allocated).toFixed(0)}</span>
                                                        <span className="text-slate-300 text-base">/</span>
                                                        <span
                                                            className="text-slate-800">{Number(req.quantity_requested).toFixed(0)}</span>
                                                    </div>
                                                </div>
                                                {!isHistory && (
                                                    <button onClick={() => handleStartEdit(req)}
                                                            className="absolute right-0 opacity-0 group-hover/btn:opacity-100 transition-all flex items-center justify-center bg-blue-600 text-white rounded-lg w-9 h-9 shadow-md">
                                                        <Edit3 size={18}/>
                                                    </button>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        );
                    })
                ) : (
                    <EmptyState
                        message={requestTab === 'active' ? "Активних заявок немає" : "Архів порожній"}
                        type={requestTab}
                    />
                )}
            </div>
        </section>
    );
};

export default RequestList;