// src/components/Features/RequestList.js
import React, {useState} from 'react';
import {
    ListChecks, History, User, AlertCircle, Clock,
    CheckCircle2, Filter, Package, Edit3, Check, X, MapPin, Inbox, RefreshCw, Settings
} from 'lucide-react';
import api from '../../services/api';
import Modal from '../UI/Modal';

const RequestList = ({requests = [], purposeMap = {}, onRefresh, currentUser}) => {
    const [requestTab, setRequestTab] = useState('active');
    const [statusFilter, setStatusFilter] = useState('all');
    const [resourceFilter, setResourceFilter] = useState('all');

    // Стани для редагування через модалку (для волонтерів та адмінів)
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [selectedReq, setSelectedReq] = useState(null);
    const [editQuantity, setEditQuantity] = useState("");
    const [editAutoExtend, setEditAutoExtend] = useState(false);
    const [isSaving, setIsSaving] = useState(false);

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

    // Відкриття модалки та заповнення початкових даних
    const handleOpenModal = (req) => {
        if (req.status === 'done') return;
        setSelectedReq(req);
        setEditQuantity(Math.round(req.quantity_requested).toString());

        // СТРОГА ПЕРЕВІРКА: якщо в базі чітко лежить false, ставимо false. Інакше — true.
        const currentAutoExtend = req.auto_extend === false || req.autoExtend === false ? false : true;
        setEditAutoExtend(currentAutoExtend);

        setIsModalOpen(true);
    };

    // Збереження змін з модалки на бекенд
    const handleSaveChanges = async () => {
        const finalQty = Math.round(Number(editQuantity));
        if (isNaN(finalQty) || finalQty <= 0) return;

        setIsSaving(true);
        try {
            // Відправляємо PATCH на бекенд
            const response = await api.patch(`/requests/${selectedReq.id}/`, {
                quantity_requested: finalQty,
                auto_extend: editAutoExtend // Передаємо поточний стейт галочки (true/false)
            });

            console.log("Бекенд успішно оновив заявку. Відповідь сервера:", response.data);

            setIsModalOpen(false);
            if (onRefresh) onRefresh(); // Обов'язково тригеримо оновлення списку з сервера
        } catch (e) {
            console.error("Помилка оновлення заявки:", e.response?.data || e.message);
        } finally {
            setIsSaving(false);
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

    const formatDate = (dateString) => {
        if (!dateString) return null;
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('uk-UA', { day: '2-digit', month: '2-digit', year: 'numeric' });
        } catch (e) {
            return dateString;
        }
    };

    const EmptyState = ({message, type}) => (
        <div className="flex flex-col items-center justify-center h-full py-12 animate-in fade-in zoom-in duration-300">
            <div className={`p-4 rounded-full mb-4 ${type === 'active' ? 'bg-blue-50' : 'bg-slate-50'}`}>
                <Inbox size={48} className={type === 'active' ? 'text-blue-200' : 'text-slate-200'}/>
            </div>
            <p className="text-slate-400 font-bold text-sm uppercase tracking-widest">{message}</p>
        </div>
    );

    return (
        <section className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-[600px] animate-in fade-in duration-500">
            {/* ШАПКА */}
            <div className="p-4 border-b border-slate-100 bg-slate-50/50 space-y-4">
                <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
                    <div className="flex items-center gap-2 text-slate-800">
                        <ListChecks size={22} className="text-blue-600"/>
                        <h2 className="text-lg font-bold">Черга заявок</h2>
                    </div>
                    <div className="flex bg-slate-200/50 p-1 rounded-xl">
                        <button
                            onClick={() => { setRequestTab('active'); setStatusFilter('all'); }}
                            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${requestTab === 'active' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                        >
                            Активні <span className="bg-slate-200 px-1.5 py-0.5 rounded text-[10px]">{requests.filter(r => r.status !== 'done').length}</span>
                        </button>
                        <button
                            onClick={() => { setRequestTab('history'); setStatusFilter('all'); }}
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
                        const statusDetails = getStatusDetails(req.status);
                        const stripeColor = isHistory ? '#10b981' : (isAdmin && Number(req.priority) >= 8 ? '#ef4444' : '#3b82f6');
                        const hasAutoExtend = req.auto_extend ?? true;

                        return (
                            <div key={req.id}
                                 className={`bg-white p-4 rounded-2xl border ${isHistory ? 'border-slate-100 opacity-75' : 'border-slate-200 shadow-sm'} hover:shadow-md transition-all relative overflow-hidden group`}>
                                <div className="absolute left-0 top-0 bottom-0 w-1.5" style={{backgroundColor: stripeColor}}></div>

                                <div className="flex justify-between items-start">
                                    <div className="space-y-1 flex-1">
                                        <span className={`flex w-fit items-center gap-1.5 text-[10px] font-black uppercase px-2 py-0.5 rounded-lg ${purposeData.color}`}>
                                            {purposeData.icon} {purposeData.label}
                                        </span>
                                        <h3 className={`font-bold text-lg text-slate-800 ${isHistory && 'line-through opacity-50'}`}>{req.resource_name}</h3>

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
                                            <div className="flex items-center gap-1 text-[11px] text-blue-700 font-bold bg-blue-50 w-fit px-1.5 py-0.5 rounded-md mt-1">
                                                <MapPin size={10} className="text-blue-500"/>
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

                                <div className="flex justify-between items-center mt-4 pt-3 border-t border-slate-50">
                                    <div className="flex items-center gap-1.5">
                                        {statusDetails.icon}
                                        <span className="text-[10px] font-bold uppercase text-slate-500">{statusDetails.label}</span>
                                    </div>

                                    {/* НАСТРОЮВАНИЙ ІНТЕРАКТИВНИЙ БЛОК ДЛЯ КАРТКИ */}
                                    <div className="flex items-center justify-end h-10">
                                        {/* Інтерактивна зона виклику Модалки */}
                                        <button
                                            disabled={isHistory}
                                            onClick={() => handleOpenModal(req)}
                                            className={`flex items-center gap-3 px-3 py-1.5 rounded-xl border transition-all text-right group/btn ${isHistory ? 'bg-slate-50 border-slate-100 cursor-not-allowed' : 'bg-slate-50/60 border-slate-200/60 hover:bg-blue-50/40 hover:border-blue-200/60 cursor-pointer'}`}
                                        >
                                            {/* Індикатор стану Автопродовження */}
                                            <div className="flex flex-col items-center justify-center">
                                                <span className="text-[7px] text-slate-400 font-black uppercase tracking-wider leading-none mb-1">Авто</span>
                                                <RefreshCw
                                                    size={12}
                                                    className={hasAutoExtend && !isHistory ? "text-amber-500 font-black animate-spin-slow" : "text-slate-300"}
                                                />
                                            </div>

                                            {/* Обсяг потреби */}
                                            <div className="flex flex-col items-end">
                                                <span className="text-[9px] text-slate-400 font-black uppercase leading-none mb-0.5">Потреба</span>
                                                <div className="text-base font-mono font-black flex items-center gap-1">
                                                    <span className="text-blue-600">{Number(req.quantity_allocated).toFixed(0)}</span>
                                                    <span className="text-slate-300 text-sm">/</span>
                                                    <span className="text-slate-700">{Number(req.quantity_requested).toFixed(0)}</span>
                                                </div>
                                            </div>

                                            {/* Наочна іконка шестірні/редагування при наведенні */}
                                            {!isHistory && (
                                                <div className="text-slate-400 group-hover/btn:text-blue-600 transition-colors pl-1 border-l border-slate-200/60">
                                                    <Settings size={14} />
                                                </div>
                                            )}
                                        </button>
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

            {/* ВСПЛИВАЮЧЕ МОДАЛЬНЕ ВІКНО ДЛЯ РЕДАГУВАННЯ ЗАЯВКИ */}
            <Modal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                title={selectedReq ? `Редагування: ${selectedReq.resource_name}` : "Редагування запиту"}
                subtitle="Конфігурація обсягів та параметрів дефіциту"
                icon={Settings}
                maxWidth="max-w-md"
            >
                {selectedReq && (
                    <div className="space-y-6 text-left">
                        {/* 1. Налаштування кількості */}
                        <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200/60">
                            <label className="text-[10px] font-black uppercase text-slate-400 italic mb-2 block tracking-widest">
                                Необхідна кількість (шт.)
                            </label>
                            <div className="flex items-center gap-3">
                                <div className="bg-blue-600 p-2.5 rounded-xl text-white shadow-lg shadow-blue-100">
                                    <Package size={20}/>
                                </div>
                                <input
                                    type="text"
                                    inputMode="numeric"
                                    value={editQuantity}
                                    onChange={(e) => setEditQuantity(e.target.value.replace(/[^0-9]/g, ''))}
                                    className="w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl font-black text-lg text-slate-800 outline-none focus:ring-2 focus:ring-blue-500/20"
                                    placeholder="Вкажіть кількість..."
                                />
                            </div>
                        </div>

                        {/* 2. Перемикач галочки Автопродовження */}
                        <div className="bg-amber-50/40 p-4 rounded-2xl border border-amber-100 shadow-sm">
                            <label className="flex items-center justify-between cursor-pointer select-none">
                                <div className="flex flex-col text-left pr-4">
                                    <span className="text-[11px] font-black text-amber-900 uppercase leading-none mb-1 flex items-center gap-1.5">
                                        <RefreshCw size={12} className={editAutoExtend ? "animate-spin-slow text-amber-500" : ""}/>
                                        Режим автопродовження
                                    </span>
                                    <span className="text-[10px] font-medium text-slate-400 leading-normal">
                                        Автоматично продовжити термін дії заявки на +5 днів у разі виявлення дефіциту на складах.
                                    </span>
                                </div>
                                <div className="relative col-span-1 flex items-center">
                                    <input
                                        type="checkbox"
                                        checked={editAutoExtend}
                                        onChange={(e) => setEditAutoExtend(e.target.checked)}
                                        className="w-5 h-5 text-amber-600 border-amber-300 rounded focus:ring-amber-500/20 focus:ring-2 accent-amber-500 cursor-pointer"
                                    />
                                </div>
                            </label>
                        </div>

                        {/* Кнопки управління модалкою */}
                        <div className="flex gap-3 justify-end pt-4 border-t border-slate-100">
                            <button
                                type="button"
                                onClick={() => setIsModalOpen(false)}
                                className="px-6 py-2.5 text-slate-400 font-bold hover:text-slate-600 transition-colors text-sm"
                            >
                                Скасувати
                            </button>
                            <button
                                type="button"
                                onClick={handleSaveChanges}
                                disabled={isSaving || !editQuantity || Number(editQuantity) <= 0}
                                className="px-8 py-2.5 bg-blue-600 text-white font-black rounded-xl hover:bg-slate-900 shadow-xl shadow-blue-200 active:scale-95 transition-all text-sm disabled:bg-slate-300 disabled:shadow-none"
                            >
                                {isSaving ? "ЗБЕРЕЖЕННЯ..." : "ЗБЕРЕГТИ ЗМІНИ"}
                            </button>
                        </div>
                    </div>
                )}
            </Modal>
        </section>
    );
};

export default RequestList;