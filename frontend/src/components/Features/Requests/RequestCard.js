import React from 'react';
import { User, AlertCircle, Clock, CheckCircle2, MapPin, RefreshCw, Settings } from 'lucide-react';

const RequestCard = ({ req, purposeMap, isAdmin, onOpenModal }) => {
    const purposeData = purposeMap[req.purpose] || { label: 'Інше', icon: '📦', color: 'bg-gray-100' };
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
        <div className={`bg-white p-4 rounded-2xl border ${isHistory ? 'border-slate-100 opacity-75' : 'border-slate-200 shadow-sm'} hover:shadow-md transition-all relative overflow-hidden group`}>
            <div className="absolute left-0 top-0 bottom-0 w-1.5" style={{ backgroundColor: stripeColor }}></div>

            <div className="flex justify-between items-start">
                <div className="space-y-1.5 flex-1">
                    <span className={`flex w-fit items-center gap-1.5 text-xs font-bold uppercase px-2.5 py-0.5 rounded-lg ${purposeData.color}`}>
                        {purposeData.icon} {purposeData.label}
                    </span>
                    <h3 className={`font-bold text-lg text-slate-800 ${isHistory && 'line-through opacity-50'}`}>{req.resource_name}</h3>

                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500 font-medium">
                        <div className="flex items-center gap-1">
                            <User size={13} className="opacity-50" />
                            <span>{req.user_full_name || req.username}</span>
                        </div>
                        {req.due_date && (
                            <div className="flex items-center gap-1 text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-100/60 text-xs font-bold">
                                <Clock size={12} className="text-amber-500" />
                                <span>до {formatDate(req.due_date)}</span>
                            </div>
                        )}
                    </div>

                    {req.city && (
                        <div className="flex items-center gap-1 text-xs text-blue-700 font-bold bg-blue-50 w-fit px-2 py-0.5 rounded-md mt-1">
                            <MapPin size={12} className="text-blue-500" />
                            <span>{req.city}</span>
                        </div>
                    )}
                </div>

                {isAdmin && (
                    <div className="text-right ml-2">
                        <div className="text-[10px] text-slate-400 font-bold uppercase">Пріоритет</div>
                        <div className={`text-xl font-black ${!isHistory && Number(req.priority) >= 8 ? 'text-red-500' : 'text-slate-700'}`}>
                            {Number(req.priority).toFixed(1)}
                        </div>
                    </div>
                )}
            </div>

            {/* Нижня панель зі статусом та кнопкою кількості/редагування */}
            <div className="flex justify-between items-center mt-4 pt-3 border-t border-slate-100">
                <div className="flex items-center gap-2">
                    {statusDetails.icon}
                    <span className="text-xs font-bold uppercase text-slate-600">{statusDetails.label}</span>
                </div>

                <button
                    disabled={isHistory}
                    onClick={() => onOpenModal(req)}
                    className={`flex items-center gap-3 px-3.5 py-2 rounded-xl border transition-all text-right group/btn ${isHistory ? 'bg-slate-50 border-slate-100 cursor-not-allowed' : 'bg-slate-50/80 border-slate-200 hover:bg-blue-50/40 hover:border-blue-300 cursor-pointer shadow-xs'}`}
                >
                    <div className="flex items-center gap-1 text-slate-400" title="Автопродовження">
                        <RefreshCw
                            size={13}
                            className={hasAutoExtend && !isHistory ? "text-amber-500 animate-spin-slow" : "text-slate-300"}
                        />
                    </div>

                    <div className="flex items-baseline gap-1 font-mono font-bold text-sm">
                        <span className="text-blue-600 text-base">{Number(req.quantity_allocated).toFixed(0)}</span>
                        <span className="text-slate-300">/</span>
                        <span className="text-slate-700">{Number(req.quantity_requested).toFixed(0)}</span>
                    </div>

                    {!isHistory && (
                        <div className="text-slate-400 group-hover/btn:text-blue-600 transition-colors pl-1 border-l border-slate-200">
                            <Settings size={15} />
                        </div>
                    )}
                </button>
            </div>
        </div>
    );
};

export default RequestCard;