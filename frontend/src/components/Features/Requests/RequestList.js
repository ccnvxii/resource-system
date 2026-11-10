import React, {useState, useMemo, useEffect} from 'react';
import {ListChecks, Filter, Package, Inbox, RotateCcw, Settings, RefreshCw} from '../../UI/icons';
import api from '../../../services/api';
import Modal from '../../UI/Modal';
import RequestCard from './RequestCard';
import FilterSelect from '../../UI/FilterSelect';

const MOBILE_PAGE_SIZE = 5;

const RequestList = ({requests = [], purposeMap = {}, onRefresh, currentUser}) => {
    const [requestTab, setRequestTab] = useState('active');
    const [statusFilter, setStatusFilter] = useState('all');
    const [resourceFilter, setResourceFilter] = useState('all');

    const [isModalOpen, setIsModalOpen] = useState(false);
    const [selectedReq, setSelectedReq] = useState(null);
    const [editQuantity, setEditQuantity] = useState("");
    const [editAutoExtend, setEditAutoExtend] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [visibleCount, setVisibleCount] = useState(25);
    const [mobilePage, setMobilePage] = useState(1);

    const isAdmin = currentUser?.is_admin;
    const availableResources = useMemo(() => Array.from(new Set(requests.map(r => r.resource_name).filter(Boolean))), [requests]);

    const displayedRequests = useMemo(() => {
        return requests.filter(r => {
            const matchTab = requestTab === 'active' ? r.status !== 'done' : r.status === 'done';
            const matchStatus = statusFilter === 'all' ? true : (statusFilter === 'new' ? (!r.status || r.status === 'new') : r.status === 'partial');
            const matchResource = resourceFilter === 'all' || r.resource_name === resourceFilter;
            return matchTab && matchStatus && matchResource;
        });
    }, [requests, requestTab, statusFilter, resourceFilter]);

    // Скидання мобільної сторінки при зміні фільтрів або вкладок
    useEffect(() => {
        setMobilePage(1);
    }, [requestTab, statusFilter, resourceFilter]);

    const visibleRequests = useMemo(() => {
        return displayedRequests.slice(0, visibleCount);
    }, [displayedRequests, visibleCount]);

    // Мобільна пагінація без скрол-трепу
    const totalMobilePages = Math.ceil(displayedRequests.length / MOBILE_PAGE_SIZE) || 1;
    const mobileVisibleRequests = useMemo(() => {
        const start = (mobilePage - 1) * MOBILE_PAGE_SIZE;
        return displayedRequests.slice(start, start + MOBILE_PAGE_SIZE);
    }, [displayedRequests, mobilePage]);

    const handleOpenModal = (req) => {
        if (req.status === 'done') return;
        setSelectedReq(req);
        setEditQuantity(Math.round(req.quantity_requested).toString());
        setEditAutoExtend(req.auto_extend !== false);
        setIsModalOpen(true);
    };

    const handleSaveChanges = async () => {
        const finalQty = Math.round(Number(editQuantity));
        if (isNaN(finalQty) || finalQty <= 0) return;

        setIsSaving(true);
        try {
            await api.patch(`/requests/${selectedReq.id}/`, {
                quantity_requested: finalQty,
                auto_extend: editAutoExtend
            });
            setIsModalOpen(false);
            if (onRefresh) onRefresh();
        } catch (e) {
            console.error(e);
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <section
            className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-auto md:h-[650px] animate-in fade-in duration-500">
            {/* ШАПКА З ОДНАКОВОЮ ВИСОТОЮ ТА ВІДСТУПАМИ */}
            <div className="p-3.5 sm:p-4 border-b border-slate-100 bg-slate-50/50 space-y-3 sm:space-y-4">
                <div className="flex justify-between items-center h-10">
                    <div className="flex items-center gap-2 text-slate-800">
                        <ListChecks size={22} className="text-blue-600"/>
                        <h2 className="text-base sm:text-lg font-bold">Черга заявок</h2>
                    </div>
                    <div className="flex bg-slate-200/50 p-1 rounded-xl">
                        <button onClick={() => {
                            setRequestTab('active');
                            setStatusFilter('all');
                        }}
                                className={`px-3 sm:px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${requestTab === 'active' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>Активні
                        </button>
                        <button onClick={() => {
                            setRequestTab('history');
                            setStatusFilter('all');
                            setResourceFilter('all');
                        }}
                                className={`px-3 sm:px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${requestTab === 'history' ? 'bg-white text-green-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>Архів
                        </button>
                    </div>
                </div>

                {requestTab === 'active' && (
                    <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-200/60">
                        <div className="hidden sm:flex items-center gap-1 text-[10px] font-black uppercase text-slate-400 mr-1">
                            <Filter size={12}/> Фільтри:
                        </div>
                        <div
                            className="flex bg-white border border-slate-200 rounded-xl p-0.5 shadow-sm h-8 items-center">
                            <button onClick={() => setStatusFilter('all')}
                                    className={`px-2.5 sm:px-3 py-1 rounded-lg text-[10px] font-bold uppercase ${statusFilter === 'all' ? 'bg-slate-900 text-white' : 'text-slate-600'}`}>Усі
                            </button>
                            <button onClick={() => setStatusFilter('new')}
                                    className={`px-2.5 sm:px-3 py-1 rounded-lg text-[10px] font-bold uppercase ${statusFilter === 'new' ? 'bg-blue-600 text-white' : 'text-slate-600'}`}>Нові
                            </button>
                            <button onClick={() => setStatusFilter('partial')}
                                    className={`px-2.5 sm:px-3 py-1 rounded-lg text-[10px] font-bold uppercase ${statusFilter === 'partial' ? 'bg-amber-600 text-white' : 'text-slate-600'}`}>Частково
                            </button>
                        </div>
                        <FilterSelect icon={Package} value={resourceFilter}
                                      onChange={(e) => setResourceFilter(e.target.value)}
                                      className="flex-1 min-w-[120px]">
                            <option value="all">Усі ресурси</option>
                            {availableResources.map((resName, idx) => <option key={idx}
                                                                              value={resName}>{resName}</option>)}
                        </FilterSelect>
                        {(statusFilter !== 'all' || resourceFilter !== 'all') && (
                            <button onClick={() => {
                                setStatusFilter('all');
                                setResourceFilter('all');
                            }}
                                    className="flex items-center gap-1 text-[10px] font-bold text-red-500 bg-red-50 px-2.5 py-1 rounded-xl h-8">
                                <RotateCcw size={11}/> Скинути</button>
                        )}
                    </div>
                )}
            </div>

            {/* 1. Мобільний формат (смартфони < md): пагінований список без скрол-трепу */}
            <div className="block md:hidden p-3 space-y-2.5">
                {mobileVisibleRequests.length > 0 ? (
                    <>
                        {mobileVisibleRequests.map((req) => (
                            <RequestCard key={req.id} req={req} purposeMap={purposeMap} isAdmin={isAdmin}
                                         onOpenModal={handleOpenModal}/>
                        ))}
                        {totalMobilePages > 1 && (
                            <div className="flex items-center justify-between pt-3 border-t border-slate-100 text-xs font-bold text-slate-500 select-none">
                                <button
                                    disabled={mobilePage <= 1}
                                    onClick={() => setMobilePage(p => Math.max(1, p - 1))}
                                    className="px-3 py-1.5 rounded-xl border border-slate-200 bg-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 active:scale-95 transition-all shadow-xs"
                                >
                                    ← Попередня
                                </button>
                                <span className="text-slate-600 font-mono text-xs">
                                    {mobilePage} / {totalMobilePages} <span className="text-slate-400 font-sans font-normal text-[11px]">({displayedRequests.length})</span>
                                </span>
                                <button
                                    disabled={mobilePage >= totalMobilePages}
                                    onClick={() => setMobilePage(p => Math.min(totalMobilePages, p + 1))}
                                    className="px-3 py-1.5 rounded-xl border border-slate-200 bg-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 active:scale-95 transition-all shadow-xs"
                                >
                                    Наступна →
                                </button>
                            </div>
                        )}
                    </>
                ) : (
                    <div className="flex flex-col items-center justify-center py-10 text-slate-400">
                        <Inbox size={40} className="text-slate-200 mb-2"/>
                        <p className="text-xs font-bold uppercase tracking-widest">Немає заявок</p>
                    </div>
                )}
            </div>

            {/* 2. Десктопний формат (планшети та десктопи >= md): список зі скролбаром */}
            <div className="hidden md:block overflow-y-auto flex-1 min-h-0 p-4 pr-2 space-y-3 custom-scrollbar">
                {visibleRequests.length > 0 ? (
                    <>
                        {visibleRequests.map((req) => (
                            <RequestCard key={req.id} req={req} purposeMap={purposeMap} isAdmin={isAdmin}
                                         onOpenModal={handleOpenModal}/>
                        ))}
                        {displayedRequests.length > visibleCount && (
                            <div className="pt-2 text-center">
                                <button
                                    onClick={() => setVisibleCount(prev => prev + 25)}
                                    className="text-xs font-black uppercase tracking-wider text-blue-600 hover:text-blue-800 transition-colors py-2 px-5 rounded-xl bg-blue-50 hover:bg-blue-100"
                                >
                                    Показати ще (+25 з {displayedRequests.length})
                                </button>
                            </div>
                        )}
                    </>
                ) : (
                    <div className="flex flex-col items-center justify-center py-24 text-slate-400">
                        <Inbox size={48} className="text-slate-200 mb-2"/>
                        <p className="text-xs font-bold uppercase tracking-widest">Немає заявок</p>
                    </div>
                )}
            </div>

            {/* Модалка редагування */}
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
                        <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200/60">
                            <label
                                className="text-[10px] font-black uppercase text-slate-400 italic mb-2 block tracking-widest">Необхідна
                                кількість (шт.)</label>
                            <input
                                type="text"
                                inputMode="numeric"
                                value={editQuantity}
                                onChange={(e) => setEditQuantity(e.target.value.replace(/[^0-9]/g, ''))}
                                className="w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl font-black text-lg text-slate-800 outline-none focus:ring-2 focus:ring-blue-500/20"
                            />
                        </div>

                        <div className="bg-amber-50/40 p-4 rounded-2xl border border-amber-100 shadow-sm">
                            <label className="flex items-center justify-between cursor-pointer select-none">
                                <div className="flex flex-col text-left pr-4">
                                    <span
                                        className="text-[11px] font-black text-amber-900 uppercase leading-none mb-1 flex items-center gap-1.5">
                                        <RefreshCw size={12}
                                                   className={editAutoExtend ? "animate-spin-slow text-amber-500" : ""}/>
                                        Режим автопродовження
                                    </span>
                                    <span className="text-[10px] font-medium text-slate-400 leading-normal">
                                        Автоматично продовжити термін дії заявки на +5 днів у разі виявлення дефіциту на складах.
                                    </span>
                                </div>
                                <input
                                    type="checkbox"
                                    checked={editAutoExtend}
                                    onChange={(e) => setEditAutoExtend(e.target.checked)}
                                    className="w-5 h-5 text-amber-600 accent-amber-500 cursor-pointer"
                                />
                            </label>
                        </div>

                        <div className="flex flex-col-reverse sm:flex-row gap-2.5 sm:gap-3 justify-end pt-4 border-t border-slate-100">
                            <button onClick={() => setIsModalOpen(false)}
                                    className="w-full sm:w-auto px-5 py-2.5 text-slate-400 font-bold hover:text-slate-600 transition-colors text-sm">Скасувати
                            </button>
                            <button onClick={handleSaveChanges} disabled={isSaving}
                                    className="w-full sm:w-auto px-8 py-2.5 bg-blue-600 text-white font-black rounded-xl hover:bg-slate-900 shadow-xl transition-all text-sm">
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