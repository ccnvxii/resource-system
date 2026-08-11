import React from 'react';
import { Edit3, Check } from 'lucide-react';

const StockRow = ({ stock, resource, isEditing, editValue, setEditValue, onStartEdit, onSaveEdit }) => {
    return (
        <tr className="border-b border-slate-50 group hover:bg-blue-50/30">
            <td className="px-6 py-4 italic text-slate-500">{stock.warehouse_name}</td>
            <td className="px-6 py-4">
                <div className="font-bold text-slate-800">{resource.name}</div>
                <div className="text-[10px] text-blue-500 font-bold uppercase">{resource.category_name}</div>
            </td>
            <td className="px-6 py-4 text-right">
                <div className="relative flex items-center justify-end h-10">
                    {isEditing ? (
                        <div className="flex items-center gap-1 animate-in fade-in zoom-in duration-200">
                            <input
                                type="number"
                                step="1"
                                value={editValue}
                                onChange={(e) => setEditValue(e.target.value)}
                                onBlur={() => onSaveEdit(stock.id)}
                                autoFocus
                                className="w-20 border-2 border-blue-500 rounded p-1 text-right"
                            />
                            <button onClick={() => onSaveEdit(stock.id)}
                                    className="p-1 bg-green-500 text-white rounded-md">
                                <Check size={14}/>
                            </button>
                        </div>
                    ) : (
                        <div className="relative flex items-center justify-end w-full h-full">
                            <div className="flex flex-col items-end transition-opacity duration-300 group-hover:opacity-20">
                                <span className="font-mono font-bold text-slate-700">
                                  {Number(stock.amount).toFixed(0)}
                                </span>
                                <span className="text-[9px] text-slate-400 font-black uppercase">
                                  {resource.unit_name}
                                </span>
                            </div>

                            <button
                                onClick={() => onStartEdit(stock.id, stock.amount)}
                                className="absolute inset-y-0 right-0 opacity-0 group-hover:opacity-100 transition-all p-2 bg-blue-50 text-blue-600 rounded-xl hover:bg-blue-100 flex items-center justify-center"
                                title="Редагувати">
                                <Edit3 size={16}/>
                            </button>
                        </div>
                    )}
                </div>
            </td>
        </tr>
    );
};

export default StockRow;