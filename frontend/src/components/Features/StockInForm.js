import React, {useState} from 'react';
import {Warehouse, PackagePlus, Hash, Plus, Trash2, Save} from 'lucide-react';
import {toast} from 'react-hot-toast';
import api from '../../services/api';

const StockInForm = ({warehouses, resources, onSubmit, loading, onClose}) => {
    const [warehouse, setWarehouse] = useState('');
    const [rows, setRows] = useState([{resource: '', amount: ''}]);
    const [localLoading, setLocalLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!warehouse) return toast.error("Оберіть склад для поповнення");
        if (rows.some(r => !r.resource || !r.amount)) return toast.error("Заповніть усі поля ресурсів");

        setLocalLoading(true);
        try {
            for (const row of rows) {
                try {
                    await api.post('/stocks/add_resource/', {
                        warehouse: parseInt(warehouse, 10),
                        resource: parseInt(row.resource, 10),
                        amount: parseInt(row.amount, 10)
                    });
                } catch (rowError) {
                    const missingResource = resources.find(r => r.id === parseInt(row.resource, 10));
                    const resourceName = missingResource ? `"${missingResource.name}"` : "Обраний ресурс";

                    if (rowError.response && rowError.response.status !== 403) {
                        throw new Error(`Ресурс ${resourceName} більше не існує в базі даних. Оновіть сторінку.`);
                    }
                    if (rowError.response && rowError.response.status === 403) {
                        throw new Error("Тільки адміністратор може поповнювати склад");
                    }
                    throw rowError;
                }
            }

            toast.success("Запаси успішно поповнено");
            setWarehouse('');
            setRows([{resource: '', amount: ''}]);

            if (onSubmit) await onSubmit();
            onClose();
        } catch (error) {
            console.error("Stock in error:", error);
            toast.error(error.message || "Помилка при поповненні складу");
        } finally {
            setLocalLoading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-6">
            {/* Вибір складу - тепер на всю ширину (прибрано max-w-xs) */}
            <div className="w-full bg-emerald-50/50 p-4 rounded-2xl border border-emerald-100 shadow-sm">
                <label
                    className="flex items-center gap-2 text-[10px] font-black text-emerald-700 mb-1.5 uppercase ml-1 tracking-wider text-left">
                    <Warehouse size={12}/> Цільовий Склад
                </label>
                <select
                    required
                    value={warehouse}
                    onChange={(e) => setWarehouse(e.target.value)}
                    className="w-full p-3.5 rounded-xl border border-emerald-200 outline-none focus:ring-2 focus:ring-emerald-500/20 font-bold text-slate-700 bg-white cursor-pointer transition-all"
                >
                    <option value="">-- Оберіть склад зі списку --</option>
                    {warehouses.map(w => (
                        <option key={w.id} value={w.id}>{w.name}</option>
                    ))}
                </select>
            </div>

            {/* Список ресурсів */}
            <div className="space-y-3 max-h-[40vh] overflow-y-auto pr-2 custom-scrollbar">
                {rows.map((row, index) => (
                    <div key={index}
                         className="flex flex-col md:flex-row gap-4 items-end bg-slate-50 p-4 rounded-2xl border border-slate-200 transition-all hover:border-emerald-200 group hover:bg-white hover:shadow-sm">
                        <div className="flex-1 w-full text-left">
                            <label
                                className="flex items-center gap-1.5 text-[9px] font-bold text-slate-400 mb-1 uppercase ml-1">
                                <PackagePlus size={10}/> Ресурс
                            </label>
                            <select
                                required
                                value={row.resource}
                                onChange={(e) => {
                                    const newRows = [...rows];
                                    newRows[index].resource = e.target.value;
                                    setRows(newRows);
                                }}
                                className="w-full p-2.5 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-emerald-500/20 text-sm font-bold cursor-pointer"
                            >
                                <option value="">-- Оберіть тип --</option>
                                {resources.map(r => (
                                    // Відображаємо тільки назву ресурсу без ID або одиниць виміру в дужках
                                    <option key={r.id} value={r.id}>{r.name}</option>
                                ))}
                            </select>
                        </div>

                        <div className="w-full md:w-40 text-left">
                            <label
                                className="flex items-center gap-1.5 text-[9px] font-bold text-slate-400 mb-1 uppercase ml-1">
                                <Hash size={10}/> Кількість (шт)
                            </label>
                            <input
                                required
                                type="text"
                                inputMode="numeric"
                                value={row.amount}
                                onKeyDown={(e) => {
                                    if (['.', ',', 'e', 'E', '+', '-'].includes(e.key)) {
                                        e.preventDefault();
                                    }
                                }}
                                onChange={(e) => {
                                    const newRows = [...rows];
                                    newRows[index].amount = e.target.value.replace(/[^0-9]/g, '');
                                    setRows(newRows);
                                }}
                                className="w-full p-2.5 rounded-xl border border-slate-200 outline-none focus:ring-2 focus:ring-emerald-500/20 text-sm font-black text-slate-800"
                                placeholder="0"
                            />
                        </div>

                        {rows.length > 1 && (
                            <button
                                type="button"
                                onClick={() => setRows(rows.filter((_, i) => i !== index))}
                                className="p-2.5 text-slate-300 hover:text-red-500 transition-all active:scale-90"
                            >
                                <Trash2 size={18}/>
                            </button>
                        )}
                    </div>
                ))}
            </div>

            <button
                type="button"
                onClick={() => setRows([...rows, {resource: '', amount: ''}])}
                className="flex items-center gap-2 text-emerald-600 font-black text-[10px] uppercase tracking-widest hover:bg-emerald-50 px-6 py-4 rounded-2xl border-2 border-dashed border-emerald-200 w-full justify-center transition-all active:scale-[0.98]"
            >
                <Plus size={16}/> Додати ще одну позицію
            </button>

            <div className="pt-6 flex gap-4 justify-end border-t border-slate-100">
                <button
                    type="button"
                    onClick={onClose}
                    className="px-6 py-3 text-slate-400 font-bold hover:text-slate-600 transition-colors"
                >
                    Скасувати
                </button>
                <button
                    type="submit"
                    disabled={loading || localLoading}
                    className="flex items-center gap-3 px-10 py-4 bg-emerald-600 text-white font-black rounded-2xl hover:bg-slate-900 shadow-xl shadow-emerald-100 disabled:bg-slate-300 transition-all active:scale-95"
                >
                    {(loading || localLoading) ? (
                        "Зарахування..."
                    ) : (
                        <>
                            <Save size={20}/>
                            <span>ЗАРАХУВАТИ ПОСТАВКУ</span>
                        </>
                    )}
                </button>
            </div>
        </form>
    );
};

export default StockInForm;