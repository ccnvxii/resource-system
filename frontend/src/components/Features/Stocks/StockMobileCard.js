import React from 'react';
import { Edit3, Warehouse, Trash2 } from '../../UI/icons';

const StockMobileCard = ({ stock, resource, onStartEdit, onDelete }) => {
    return (
        <div className="bg-white p-3.5 rounded-2xl border border-slate-200/80 shadow-sm transition-all hover:border-blue-200">
            <div className="flex items-start justify-between gap-2.5">
                {/* Ліва колонка: Назва, категорія, склад */}
                <div className="min-w-0 flex-1">
                    <div className="flex flex-col items-start gap-1">
                        <span className="font-bold text-slate-800 text-sm leading-tight break-words">
                            {resource.name}
                        </span>
                        {resource.category_name && (
                            <span className="text-[9px] font-medium uppercase text-blue-600 bg-blue-50 px-2 py-0.5 rounded-md">
                                {resource.category_name}
                            </span>
                        )}
                    </div>

                    <div className="flex items-center gap-1.5 mt-1.5 text-slate-500">
                        <Warehouse size={13} className="text-slate-400 shrink-0" />
                        <span className="truncate italic text-xs text-slate-500">{stock.warehouse_name}</span>
                    </div>
                </div>

                {/* Права колонка: Кількість та швидке редагування */}
                <div className="shrink-0 flex items-center gap-2">
                    <div className="flex items-center gap-2.5">
                            <div className="flex flex-col items-end">
                                <span className="font-mono font-bold text-slate-800 text-sm leading-tight">
                                    {Number(stock.amount).toFixed(0)}
                                </span>
                                <span className="text-[9px] text-slate-400 font-medium uppercase">
                                    {resource.unit_name || 'од.'}
                                </span>
                            </div>

                            <button
                                onClick={() => onStartEdit(stock)}
                                className="p-2 bg-slate-50 hover:bg-blue-50 text-slate-500 hover:text-blue-600 rounded-xl transition-colors active:scale-95 border border-slate-100"
                                aria-label="Редагувати кількість"
                            >
                                <Edit3 size={15} />
                            </button>
                            <button
                                onClick={() => onDelete && onDelete(stock)}
                                className="p-2 bg-red-50 text-red-500 hover:bg-red-100 rounded-xl transition-colors active:scale-95 border border-red-100"
                                aria-label="Видалити позицію зі складу"
                            >
                                <Trash2 size={15} />
                            </button>
                        </div>
                </div>
            </div>
        </div>
    );
};

export default React.memo(StockMobileCard);
