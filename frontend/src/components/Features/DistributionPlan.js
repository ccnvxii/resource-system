import React from 'react';
import {
  CheckCircle2,
  Database,
  User,
  Box,
  Fingerprint,
  PieChart,
  Download
} from 'lucide-react';
import * as XLSX from 'xlsx'; // Імпорт бібліотеки для роботи з Excel

const DistributionPlan = ({ plan, purposeMap }) => {

  // Функція для експорту конкретного плану в Excel
  const exportPlanToExcel = () => {
    if (!plan.items || plan.items.length === 0) return;

    // Підготовка даних для таблиці (форматування для зручності читання)
    const dataToExport = plan.items.map(item => ({
      "ID Операції": item.id,
      "Пріоритет": item.priority ? Number(item.priority).toFixed(1) : '0.0',
      "Ресурс": item.resource_name,
      "Кількість": Math.round(item.amount),
      "Одиниця": item.unit_name || 'од.',
      "Склад-джерело": item.warehouse_name,
      "Отримувач": item.recipient_name,
      "Призначення": item.purpose_name
    }));

    // Створення книги та листа
    const ws = XLSX.utils.json_to_sheet(dataToExport);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Результати розподілу");

    // Завантаження файлу з назвою плану та датою
    const fileName = `Distribution_Plan_${plan.id || 'new'}.xlsx`;
    XLSX.writeFile(wb, fileName);
  };

  return (
    <div className="animate-fade-in-up bg-slate-50 rounded-3xl border-2 border-slate-200 p-6 md:p-8 mb-10">
      {/* Заголовок плану */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 p-2.5 rounded-xl shadow-lg shadow-blue-100">
            <PieChart className="text-white" size={24} />
          </div>
          <div>
            <h3 className="text-2xl font-black text-slate-800 tracking-tight">
              Результати оптимізації розподілу
            </h3>
            <p className="text-slate-500 text-xs font-bold uppercase tracking-widest">
              Алгоритм Weighted Max-Min Fairness за матрицею пріоритетів
            </p>
          </div>
        </div>

        {/* КНОПКА ЕКСПОРТУ (Додано) */}
        <div className="flex items-center gap-3 w-full md:w-auto">
          <button
            onClick={exportPlanToExcel}
            className="flex items-center justify-center gap-2 px-5 py-2.5 bg-white border-2 border-slate-200 rounded-xl font-black text-[11px] uppercase text-slate-600 hover:bg-slate-100 hover:border-slate-300 transition-all shadow-sm active:scale-95 flex-1 md:flex-none"
          >
            <Download size={16} className="text-blue-600" />
            Експорт плану (.xlsx)
          </button>
          <span className="flex items-center gap-2 text-sm font-bold bg-white text-slate-700 px-4 py-2 rounded-xl border border-slate-200 shadow-sm whitespace-nowrap">
            <CheckCircle2 size={16} className="text-green-500" />
            {plan.items.length} операцій
          </span>
        </div>
      </div>

      {/* Сітка результатів (залишається без змін) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {plan.items.map((item) => {
          const isHighPriority = item.priority >= 8;

          return (
            <div
              key={item.id}
              className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200 hover:shadow-md transition-all flex flex-col justify-between group relative overflow-hidden"
            >
              <div
                className="absolute left-0 top-0 bottom-0 w-1.5"
                style={{ backgroundColor: isHighPriority ? '#ef4444' : '#3b82f6' }}
              ></div>

              <div>
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-1.5 text-slate-400">
                    <Fingerprint size={14} />
                    <span className="text-[10px] font-mono font-bold uppercase">Операція #{item.id}</span>
                  </div>

                  <div className="text-right">
                    <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Пріоритет</div>
                    <div className="text-xl font-black text-slate-700 leading-none">
                      {item.priority && !isNaN(item.priority) ? Number(item.priority).toFixed(1) : '0.0'}
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-3 mb-6">
                  <div className="flex items-center gap-3">
                    <Box size={20} className="text-blue-500" />
                    <h4 className="text-lg font-extrabold text-slate-800 leading-tight">
                      {item.resource_name}
                    </h4>
                  </div>
                  <div className="bg-blue-50 text-blue-700 px-3 py-1 rounded-lg font-black text-lg border border-blue-100">
                    {Math.round(item.amount)} {/* Ціле число для відображення */}
                  </div>
                </div>
              </div>

              <div className="space-y-4 pt-4 border-t border-slate-100">
                <div className="flex items-start gap-3">
                  <div className="mt-1 text-slate-400">
                    <Database size={14} />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter">Джерело (Склад)</span>
                    <span className="font-bold text-slate-700 text-sm">{item.warehouse_name}</span>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="mt-1 text-slate-400">
                    <User size={14} />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter">Отримувач</span>
                    <span className="font-bold text-slate-800 text-sm leading-none">{item.recipient_name}</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default DistributionPlan;