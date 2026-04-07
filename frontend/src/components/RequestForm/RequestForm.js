import React from 'react';
import {
  X,
  User,
  Package,
  Hash,
  Target,
  Plus,
  Trash2,
  Save,
  FileText,
  AlertCircle
} from 'lucide-react';

const RequestForm = ({
  isOpen, onClose, usersList, resourcesList, selectedUserId,
  setSelectedUserId, formRows, handleFormChange, addFormRow,
  removeFormRow, handleSubmitRequest, loading
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl m-4 p-6 md:p-8 relative animate-scale-up">

        {/* Шапка модального вікна */}
        <div className="flex justify-between items-start mb-8">
          <div className="flex items-center gap-3">
            <div className="bg-blue-100 p-2.5 rounded-xl">
              <FileText className="text-blue-600" size={24} />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-slate-800 tracking-tight">Нова заявка</h2>
              <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-0.5">
                Режим: Матриця пріоритетів
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-100 rounded-full text-slate-400 transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Вибір заявника */}
        <div className="mb-8 bg-blue-50/50 p-5 rounded-2xl border border-blue-100">
          <label className="flex items-center gap-2 text-sm font-bold text-blue-800 mb-3 uppercase tracking-wide">
            <User size={16} /> Заявник
          </label>
          <select
            value={selectedUserId}
            onChange={(e) => setSelectedUserId(e.target.value)}
            className="w-full p-3 rounded-xl border border-blue-200 outline-none bg-white font-medium text-slate-700 focus:ring-2 focus:ring-blue-500/20 transition-all cursor-pointer"
          >
            <option value="" disabled>Оберіть користувача зі списку</option>
            {usersList.map(u => (
              <option key={u.id} value={u.id}>{u.username} ({u.email})</option>
            ))}
          </select>
        </div>

        {/* Список позицій */}
        <div className="space-y-4 max-h-[45vh] overflow-y-auto pr-2 custom-scrollbar">
          {formRows.map((row, index) => (
            <div key={index} className="group flex flex-col md:flex-row gap-4 items-end bg-slate-50 p-5 rounded-2xl border border-slate-200 transition-all hover:border-blue-200">

              {/* Вибір ресурсу */}
              <div className="flex-1 w-full">
                <label className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400 mb-1.5 uppercase ml-1">
                  <Package size={12} /> Ресурс
                </label>
                <select
                  value={row.resource}
                  onChange={(e) => handleFormChange(index, 'resource', e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500/20 text-sm font-medium"
                >
                  <option value="">Оберіть ресурс...</option>
                  {resourcesList.map(r => (
                    <option key={r.id} value={r.id}>{r.name} ({r.unit})</option>
                  ))}
                </select>
              </div>

              {/* Кількість */}
              <div className="w-full md:w-32">
                <label className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400 mb-1.5 uppercase ml-1">
                  <Hash size={12} /> К-сть
                </label>
                <input
                  type="number"
                  min="1"
                  value={row.quantity}
                  onChange={(e) => handleFormChange(index, 'quantity', e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 text-sm font-bold text-slate-700"
                  placeholder="0"
                />
              </div>

              {/* Призначення */}
              <div className="w-full md:w-64">
                <label className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400 mb-1.5 uppercase ml-1">
                  <Target size={12} /> Призначення
                </label>
                <select
                  value={row.purpose}
                  onChange={(e) => handleFormChange(index, 'purpose', e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500/20 text-sm font-medium"
                >
                  <option value="military">Військові потреби (10)</option>
                  <option value="hospital">Медичні заклади (9)</option>
                  <option value="disaster">Зона лиха (8)</option>
                  <option value="refugees">ВПО та біженці (6)</option>
                  <option value="school">Освітні заклади (4)</option>
                  <option value="personal">Особисте споживання (1)</option>
                </select>
              </div>

              {/* Кнопка видалення рядка */}
              {formRows.length > 1 && (
                <button
                  onClick={() => removeFormRow(index)}
                  className="p-2.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all mb-0.5"
                  title="Видалити позицію"
                >
                  <Trash2 size={18} />
                </button>
              )}
            </div>
          ))}
        </div>

        {/* Кнопка додавання нового рядка */}
        <div className="mt-6">
          <button
            onClick={addFormRow}
            className="flex items-center gap-2 text-blue-600 font-bold hover:bg-blue-50 px-6 py-3 rounded-xl border-2 border-dashed border-blue-200 w-full justify-center transition-all group"
          >
            <Plus size={20} className="group-hover:scale-110 transition-transform" />
            Додати ще одну позицію
          </button>
        </div>

        {/* Кнопки дій */}
        <div className="mt-10 flex gap-4 justify-end pt-6 border-t border-slate-100">
          <button
            onClick={onClose}
            className="px-6 py-3 text-slate-500 font-bold hover:bg-slate-100 rounded-xl transition-colors"
          >
            Скасувати
          </button>
          <button
            onClick={handleSubmitRequest}
            disabled={loading}
            className="flex items-center gap-2 px-8 py-3 bg-blue-600 text-white font-bold rounded-xl hover:bg-blue-700 shadow-lg shadow-blue-200 transition-all active:scale-95 disabled:bg-slate-300 disabled:shadow-none"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                Збереження...
              </>
            ) : (
              <>
                <Save size={18} />
                Зберегти заявку
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default RequestForm;