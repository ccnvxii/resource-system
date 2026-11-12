import React, {useState, useMemo, useEffect} from 'react';
import {PackageSearch, Filter, ChevronUp, ChevronDown, Download, RotateCcw, Settings, Trash2} from '../../UI/icons';
import {exportResourcesToExcel} from '../../../utils/excelExport';
import api from '../../../services/api';
import { toast } from 'react-hot-toast';
import StockRow from './StockRow';
import StockMobileCard from './StockMobileCard';
import FilterSelect from '../../UI/FilterSelect';
import Modal from '../../UI/Modal';
import ConfirmModal from '../../UI/ConfirmModal';

const INITIAL_ROWS_COUNT = 30;
const MOBILE_STOCK_PAGE_SIZE = 6;

const StockTable = ({stocks = [], resourcesMap = {}, onRefresh, isLoading = false}) => {
    const [filterCategory, setFilterCategory] = useState('all');
    const [filterWarehouse, setFilterWarehouse] = useState('all');
    const [sortOrder, setSortOrder] = useState('none');
    const [editingStock, setEditingStock] = useState(null);
    const [isSaving, setIsSaving] = useState(false);
    const [confirmStock, setConfirmStock] = useState(null);
    const [isDeleting, setIsDeleting] = useState(false);
    const [editValue, setEditValue] = useState("");
    const [visibleCount, setVisibleCount] = useState(INITIAL_ROWS_COUNT);
    const [mobilePage, setMobilePage] = useState(1);

    const categories = useMemo(() => ['all', ...new Set(Object.values(resourcesMap).map(r => r.category_name))], [resourcesMap]);
    const warehouses = useMemo(() => ['all', ...new Set(stocks.map(s => s.warehouse_name))], [stocks]);

    const filteredStocks = useMemo(() => {
        return stocks.filter(stock => {
            const resource = resourcesMap[stock.resource];
            const isPositive = Number(stock.amount) > 0;
            const matchCategory = filterCategory === 'all' || resource?.category_name === filterCategory;
            const matchWarehouse = filterWarehouse === 'all' || stock.warehouse_name === filterWarehouse;
            return isPositive && matchCategory && matchWarehouse;
        });
    }, [stocks, resourcesMap, filterCategory, filterWarehouse]);

    const sortedStocks = useMemo(() => {
        return [...filteredStocks].sort((a, b) => {
            if (sortOrder === 'none') return 0;
            const amountA = Number(a.amount) || 0;
            const amountB = Number(b.amount) || 0;
            return sortOrder === 'asc' ? amountA - amountB : amountB - amountA;
        });
    }, [filteredStocks, sortOrder]);

    useEffect(() => {
        setMobilePage(1);
    }, [filterCategory, filterWarehouse, sortOrder]);

    const visibleStocks = useMemo(() => {
        return sortedStocks.slice(0, visibleCount);
    }, [sortedStocks, visibleCount]);

    // Мобільна пагінація карток
    const totalMobilePages = Math.ceil(sortedStocks.length / MOBILE_STOCK_PAGE_SIZE) || 1;
    const mobileVisibleStocks = useMemo(() => {
        const start = (mobilePage - 1) * MOBILE_STOCK_PAGE_SIZE;
        return sortedStocks.slice(start, start + MOBILE_STOCK_PAGE_SIZE);
    }, [sortedStocks, mobilePage]);

    const toggleSort = () => {
        if (sortOrder === 'none') setSortOrder('desc');
        else if (sortOrder === 'desc') setSortOrder('asc');
        else setSortOrder('none');
    };

    const hasActiveFilters = filterCategory !== 'all' || filterWarehouse !== 'all';
    const resetFilters = () => {
        setFilterCategory('all');
        setFilterWarehouse('all');
    };
    const renderLoading = (padding) => (
        <div className={`flex flex-col items-center justify-center text-center ${padding} text-slate-400`} role="status" aria-live="polite">
            <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mb-3"/>
            <p className="text-xs font-medium uppercase tracking-widest">Завантаження запасів...</p>
        </div>
    );

    const renderEmpty = (padding) => (
        <div className={`flex flex-col items-center justify-center text-center ${padding} text-slate-400`}>
            <PackageSearch size={40} className="text-slate-200 mb-2"/>
            {hasActiveFilters ? (
                <>
                    <p className="text-xs font-medium uppercase tracking-widest">За вашими фільтрами запасів не знайдено</p>
                    <button
                        onClick={resetFilters}
                        className="mt-3 flex items-center gap-1.5 text-xs font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 px-4 py-2 rounded-xl transition-colors active:scale-95"
                    >
                        <RotateCcw size={12}/> Скинути фільтри пошуку
                    </button>
                </>
            ) : (
                <p className="text-xs font-medium uppercase tracking-widest">Запасів поки немає</p>
            )}
        </div>
    );

    // Запит на видалення: спочатку відкриваємо модальне підтвердження
    const handleDelete = (stock) => setConfirmStock(stock);

    const performDelete = async () => {
        if (!confirmStock) return;
        setIsDeleting(true);
        try {
            await api.delete(`/stocks/${confirmStock.id}/`);
            toast.success('Позицію видалено зі складу');
            setConfirmStock(null);
            setEditingStock(null);
            if (onRefresh) onRefresh();
        } catch (e) {
            console.error(e);
        } finally {
            setIsDeleting(false);
        }
    };

    const openEdit = (stock) => {
        setEditingStock(stock);
        setEditValue(Math.round(Number(stock.amount)).toString());
    };

    const handleSaveEdit = async () => {
        if (!editingStock) return;
        const roundedValue = Math.round(Number(editValue));
        if (editValue === "" || isNaN(roundedValue) || roundedValue < 0) {
            toast.error("Вкажіть коректну кількість");
            return;
        }
        setIsSaving(true);
        try {
            if (roundedValue === 0) {
                // Нульовий залишок = позицію списано: видаляємо її зі складу
                await api.delete(`/stocks/${editingStock.id}/`);
                toast.success("Залишок 0 - позицію списано зі складу");
            } else {
                await api.patch(`/stocks/${editingStock.id}/update_amount/`, {amount: roundedValue});
            }
            setEditingStock(null);
            if (onRefresh) onRefresh();
        } catch (e) {
            console.error(e);
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <section
            className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-auto md:h-[650px]">
            <div className="p-3.5 sm:p-4 border-b border-slate-100 bg-slate-50/50 space-y-3 sm:space-y-4">
                <div className="flex justify-between items-center h-10">
                    <div className="flex items-center gap-2 text-slate-800 min-w-0">
                        <PackageSearch size={22} className="text-blue-600 shrink-0"/>
                        <h2 className="text-base sm:text-lg font-bold truncate">Запаси на складах</h2>
                        <span className="text-[11px] font-normal text-slate-400 shrink-0 whitespace-nowrap" title="Кількість позицій з урахуванням фільтрів">{sortedStocks.length} поз.</span>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                    <button
                        onClick={() => exportResourcesToExcel(stocks, resourcesMap)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-white border border-slate-200 text-slate-600 hover:text-blue-600 shadow-sm transition-colors active:scale-95"
                        title="Завантажити звіт по ресурсах (Excel)"
                    >
                        <Download size={14}/>
                        <span>Звіт</span>
                    </button>
                    {/* Швидке сортування на мобільних телефонах */}
                    <button
                        onClick={toggleSort}
                        className="md:hidden flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-white border border-slate-200 text-slate-600 hover:text-blue-600 shadow-sm transition-colors active:scale-95 shrink-0"
                        aria-label="Сортувати за кількістю"
                    >
                        <span>К-сть</span>
                        <span className="flex flex-col text-slate-400">
                            <ChevronUp size={10} className={`-mb-1 ${sortOrder === 'asc' ? 'text-blue-600 stroke-[3]' : ''}`}/>
                            <ChevronDown size={10} className={`${sortOrder === 'desc' ? 'text-blue-600 stroke-[3]' : ''}`}/>
                        </span>
                    </button>
                    </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-200/60">
                    <div className="hidden sm:flex items-center gap-1 text-[10px] font-medium uppercase text-slate-400 mr-1">
                        <Filter size={12}/> Фільтри:
                    </div>
                    <FilterSelect
                        icon={PackageSearch}
                        value={filterCategory}
                        onChange={(e) => setFilterCategory(e.target.value)}
                        className="flex-1 min-w-[120px]"
                    >
                        <option value="all">Усі категорії</option>
                        {categories.filter(c => c !== 'all' && c).map(cat => (
                            <option key={cat} value={cat}>{cat}</option>
                        ))}
                    </FilterSelect>
                    <FilterSelect
                        icon={PackageSearch}
                        value={filterWarehouse}
                        onChange={(e) => setFilterWarehouse(e.target.value)}
                        className="flex-1 min-w-[120px]"
                    >
                        <option value="all">Усі склади</option>
                        {warehouses.filter(w => w !== 'all' && w).map(wh => (
                            <option key={wh} value={wh}>{wh}</option>
                        ))}
                    </FilterSelect>
                    {hasActiveFilters && (
                        <button onClick={resetFilters}
                                className="flex items-center gap-1 text-[10px] font-medium text-red-500 bg-red-50 px-2.5 py-1 rounded-xl h-8">
                            <RotateCcw size={11}/> Скинути</button>
                    )}
                </div>
            </div>

            {/* 1. Десктопний вигляд: Таблиця (показується на екранах від md і ширше) */}
            <div className="hidden md:block overflow-y-auto flex-1 custom-scrollbar pr-1">
                <table className="w-full text-sm text-left">
                    <thead className="bg-slate-50 sticky top-0 uppercase text-[10px] font-medium text-slate-400">
                    <tr>
                        <th className="px-6 py-2">Склад</th>
                        <th className="px-6 py-2">Ресурс</th>
                        <th className="px-6 py-2 text-right">
                            <button
                                onClick={toggleSort}
                                className="inline-flex items-center gap-1.5 ml-auto hover:text-blue-600 transition-colors uppercase cursor-pointer select-none group"
                            >
                                <span>Кількість</span>
                                <span className="flex flex-col text-slate-400 group-hover:text-blue-600">
                                    <ChevronUp size={10}
                                               className={`-mb-1 ${sortOrder === 'asc' ? 'text-blue-600 stroke-[3]' : ''}`}/>
                                    <ChevronDown size={10}
                                                 className={`${sortOrder === 'desc' ? 'text-blue-600 stroke-[3]' : ''}`}/>
                                </span>
                            </button>
                        </th>
                    </tr>
                    </thead>
                    <tbody>
                    {visibleStocks.map((stock) => (
                        <StockRow
                            key={stock.id}
                            stock={stock}
                            resource={resourcesMap[stock.resource] || {
                                name: '...',
                                category_name: '...',
                                unit_name: '?'
                            }}
                            onStartEdit={openEdit}
                        />
                    ))}
                    </tbody>
                </table>
                {visibleStocks.length === 0 && (isLoading ? renderLoading('py-24') : renderEmpty('py-24'))}
            </div>

            {/* 2. Спеціальний мобільний формат: акуратні картки без скрол-трепу */}
            <div className="md:hidden p-3 space-y-2.5">
                {mobileVisibleStocks.length > 0 ? (
                    <>
                        {mobileVisibleStocks.map((stock) => (
                            <StockMobileCard
                                key={stock.id}
                                stock={stock}
                                resource={resourcesMap[stock.resource] || {
                                    name: '...',
                                    category_name: '...',
                                    unit_name: '?'
                                }}
                            onStartEdit={openEdit}
                            />
                        ))}
                        {totalMobilePages > 1 && (
                            <div className="flex items-center justify-between pt-3 border-t border-slate-100 text-xs font-medium text-slate-500 select-none">
                                <button
                                    disabled={mobilePage <= 1}
                                    onClick={() => setMobilePage(p => Math.max(1, p - 1))}
                                    className="px-3 py-1.5 rounded-xl border border-slate-200 bg-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 active:scale-95 transition-all shadow-xs"
                                >
                                    ← Попередня
                                </button>
                                <span className="text-slate-600 font-mono text-xs">
                                    {mobilePage} / {totalMobilePages} <span className="text-slate-400 font-sans font-normal text-[11px]">({sortedStocks.length})</span>
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
                    (isLoading ? renderLoading('py-10') : renderEmpty('py-10'))
                )}
            </div>

            {/* Кнопка довантаження порцій для десктопу */}
            {sortedStocks.length > visibleCount && (
                <div className="hidden md:block p-3 text-center border-t border-slate-100 bg-slate-50/50">
                    <button
                        onClick={() => setVisibleCount(prev => prev + 30)}
                        className="text-xs font-semibold tracking-wide text-blue-600 hover:text-blue-800 transition-colors py-1.5 px-4 rounded-xl bg-blue-50 hover:bg-blue-100"
                    >
                        Показати ще (+30 з {sortedStocks.length})
                    </button>
                </div>
            )}

            {/* Модалка редагування - той самий формат, що й для заявок */}
            <Modal
                isOpen={!!editingStock}
                onClose={() => { if (!confirmStock) setEditingStock(null); }}
                title={editingStock ? `Редагування: ${resourcesMap[editingStock.resource]?.name || editingStock.resource_name}` : "Редагування запасу"}
                subtitle="Конфігурація обсягів на складі"
                icon={Settings}
                maxWidth="max-w-xl"
            >
                {editingStock && (
                    <div className="space-y-6 text-left">
                        <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200/60">
                            <label
                                className="text-[10px] font-semibold uppercase text-slate-400 italic mb-2 block tracking-widest">Кількість
                                на складі ({resourcesMap[editingStock.resource]?.unit_name || editingStock.unit_name || "шт."})</label>
                            <input
                                type="text"
                                inputMode="numeric"
                                autoFocus
                                value={editValue}
                                onChange={(e) => setEditValue(e.target.value.replace(/[^0-9]/g, ""))}
                                onKeyDown={(e) => { if (e.key === "Enter") handleSaveEdit(); }}
                                className="w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl font-bold text-lg text-slate-800 outline-none focus:ring-2 focus:ring-blue-500/20"
                            />
                            <p className="text-[10px] font-medium text-slate-400 mt-2 leading-normal">
                                Склад: {editingStock.warehouse_name}. Значення 0 спише позицію та видалить її зі складу.
                            </p>
                        </div>

                        <div className="flex flex-col-reverse sm:flex-row gap-2.5 sm:gap-3 justify-end pt-4 border-t border-slate-100">
                            <button onClick={() => handleDelete(editingStock)}
                                    className="w-full sm:w-auto sm:mr-auto whitespace-nowrap px-4 py-2.5 flex items-center justify-center gap-2 text-red-500 bg-red-50 hover:bg-red-100 rounded-xl font-semibold transition-colors text-sm">
                                <Trash2 size={16}/> Видалити зі складу
                            </button>
                            <button onClick={() => setEditingStock(null)}
                                    className="w-full sm:w-auto whitespace-nowrap px-5 py-2.5 text-slate-400 font-medium hover:text-slate-600 transition-colors text-sm">Скасувати
                            </button>
                            <button onClick={handleSaveEdit} disabled={isSaving}
                                    className="w-full sm:w-auto whitespace-nowrap px-7 py-2.5 bg-blue-600 text-white font-bold rounded-xl hover:bg-slate-900 shadow-xl transition-all text-sm">
                                {isSaving ? "ЗБЕРЕЖЕННЯ..." : "ЗБЕРЕГТИ ЗМІНИ"}
                            </button>
                        </div>
                    </div>
                )}
            </Modal>

            <ConfirmModal
                isOpen={!!confirmStock}
                title="Видалити позицію зі складу?"
                message={confirmStock ? `«${resourcesMap[confirmStock.resource]?.name || confirmStock.resource_name}» (${confirmStock.warehouse_name})` : ''}
                details={confirmStock ? `Кількість ${Math.round(Number(confirmStock.amount))} буде списано та втрачено.` : ''}
                confirmText="Видалити"
                loading={isDeleting}
                onConfirm={performDelete}
                onCancel={() => setConfirmStock(null)}
            />
        </section>
    );
};

export default StockTable;