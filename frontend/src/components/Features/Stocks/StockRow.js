import React from 'react';
import { Edit3 } from '../../UI/icons';

const StockRow = ({ stock, resource, onStartEdit }) => {
    return (
        <tr className="border-b border-slate-50 group hover:bg-blue-50/30 transition-colors">
            <td className="px-4 md:px-6 py-2 md:py-2.5 italic text-slate-500 text-xs md:text-sm">{stock.warehouse_name}</td>
            <td className="px-4 md:px-6 py-2 md:py-2.5">
                <div className="font-bold text-slate-800 text-xs md:text-sm">{resource.name}</div>
                <div className="text-[10px] text-blue-500 font-medium uppercase">{resource.category_name}</div>
            </td>
            <td className="px-4 md:px-6 py-2 md:py-2.5 text-right">
                <div className="flex items-center justify-end gap-2.5">
                    <div className="flex flex-col items-end">
                        <span className="font-mono font-bold text-slate-700 leading-tight">
                            {Number(stock.amount).toFixed(0)}
                        </span>
                        <span className="text-[9px] text-slate-400 font-medium uppercase leading-tight">
                            {resource.unit_name}
                        </span>
                    </div>
                    <button
                        onClick={() => onStartEdit(stock)}
                        className="p-1.5 bg-slate-50 text-slate-400 group-hover:bg-blue-50 group-hover:text-blue-600 rounded-lg hover:bg-blue-100 transition-colors flex items-center justify-center"
                        title="Редагувати"
                        aria-label="Редагувати кількість">
                        <Edit3 size={15}/>
                    </button>
                </div>
            </td>
        </tr>
    );
};

export default React.memo(StockRow);
