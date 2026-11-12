import React from 'react';
import { User, AlertCircle, Clock, CheckCircle2, MapPin, RefreshCw, Settings, Package } from '../../UI/icons';

const RequestCard = ({ req, purposeMap, isAdmin, onOpenModal }) => {
    const purposeData = purposeMap[req.purpose] || { label: 'Інше', icon: <Package size={13} />, color: 'bg-gray-100' };
    const isHistory = req.status === 'done';
    const hasAutoExtend = req.auto_extend ?? true;

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

    const formatDate = (dateString) => {
        if (!dateString) return null;
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('uk-UA', { day: '2-digit', month: '2-digit', year: 'numeric' });
        } catch (e) {
            return dateString;
        }
    };

    const statusDetails = getStatusDetails(req.status);

    // Логіка кольору смужки: Виконано -> Зелений | Адмін + Високий пріоритет -> Червоний | Частково -> Оранжевий | Нова -> Синій
    const getStripeColor = () => {
        if (isHistory) return '#10b981'; // зелений для архіву
        if (isAdmin && Number(req.priority) >= 8) return '#ef4444'; // червоний для критичного пріоритету адміна
        if (req.status === 'partial') return '#f59e0b'; // оранжевий для частково виконаних
        return '#3b82f6'; // синій для нових
    };

    const stripeColor = getStripeColor();

    return (
        <div className={`bg-white p-3 rounded-xl border ${isHistory ? 'border-slate-100 opacity-75' : 'border-slate-200 shadow-sm'} hover:shadow-md transition-all relative overflow-hidden group`}>
            <div className="absolute left-0 top-0 bottom-0 w-1.5" style={{ backgroundColor: stripeColor }}></div>

            <div className="pl-1.5 space-y-1.5">
                {/* Рядок 1: призначення та пріоритет (призначення в один рядок, без переносу) */}
                <div className="flex items-center justify-between gap-2">
                    <span className={`flex min-w-0 w-fit items-center gap-1 text-[10px] sm:text-[11px] font-semibold uppercase px-2 py-0.5 rounded-lg whitespace-nowrap ${purposeData.color}`}>
                        <span className="shrink-0">{purposeData.icon}</span>
                        <span className="truncate">{purposeData.label}</span>
                    </span>
                    {isAdmin && (
                        <div className="flex items-baseline gap-1 shrink-0" title="Пріоритет">
                            <span className="text-[10px] text-slate-400 font-medium uppercase">Пр.</span>
                            <span className={`text-base font-bold leading-none ${!isHistory && Number(req.priority) >= 8 ? 'text-red-500' : 'text-slate-700'}`}>
                                {Number(req.priority).toFixed(1)}
                            </span>
                        </div>
                    )}
                </div>

                {/* Рядок 2: ресурс та статус заявки */}
                <div className="flex items-center justify-between gap-2">
                    <h3 className={`font-bold text-base leading-tight text-slate-800 py-1 min-w-0 ${isHistory && 'line-through opacity-50'}`}>{req.resource_name}</h3>
                    <div className="flex items-center gap-1.5 shrink-0" title="Статус заявки">
                        {statusDetails.icon}
                        <span className="text-[9px] sm:text-[10px] font-semibold uppercase text-slate-600">{statusDetails.label}</span>
                    </div>
                </div>

                {/* Рядок 3: ліворуч заявник + термін, під ними місто; праворуч дії (кількість та кошик) */}
                <div className="flex items-center justify-between gap-2">
                    <div className="flex flex-col gap-1 text-xs text-slate-500 font-medium min-w-0">
                        {/* Завжди в одному рядку: заявник та термін */}
                        <div className="flex items-center gap-2.5 min-w-0">
                            <div className="flex items-center gap-1 min-w-0">
                                <User size={13} className="opacity-50 shrink-0" />
                                <span className="truncate">{req.user_full_name || req.username}</span>
                            </div>
                            {req.due_date && (
                                <div className="flex items-center gap-1 text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-100/60 shrink-0 whitespace-nowrap">
                                    <Clock size={12} className="text-amber-500 shrink-0" />
                                    <span>до {formatDate(req.due_date)}</span>
                                </div>
                            )}
                        </div>
                        {/* Місто — завжди окремим рядком під ними */}
                        {req.city && (
                            <div className="flex items-center gap-1 text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded-md w-fit max-w-full">
                                <MapPin size={12} className="text-blue-500 shrink-0" />
                                <span className="truncate">{req.city}</span>
                            </div>
                        )}
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                        <button
                            disabled={isHistory && !isAdmin}
                            onClick={() => onOpenModal(req)}
                            className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg border transition-all text-right group/btn ${isHistory && !isAdmin ? 'bg-slate-50 border-slate-100 cursor-not-allowed' : 'bg-slate-50/80 border-slate-200 hover:bg-blue-50/40 hover:border-blue-300 cursor-pointer shadow-xs'}`}
                        >
                            <span title="Автопродовження">
                                <RefreshCw
                                    size={12}
                                    className={hasAutoExtend && !isHistory ? "text-amber-500 animate-spin-slow" : "text-slate-300"}
                                />
                            </span>
                            <div className="flex items-baseline gap-1 font-mono font-bold text-sm">
                                <span className="text-blue-600">{Number(req.quantity_allocated).toFixed(0)}</span>
                                <span className="text-slate-300">/</span>
                                <span className="text-slate-700">{Number(req.quantity_requested).toFixed(0)}</span>
                            </div>
                            {(!isHistory || isAdmin) && (
                                <span className="text-slate-400 group-hover/btn:text-blue-600 transition-colors pl-1.5 border-l border-slate-200">
                                    <Settings size={14} />
                                </span>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default React.memo(RequestCard);
