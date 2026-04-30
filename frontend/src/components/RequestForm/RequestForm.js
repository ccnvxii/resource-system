import React, { useState, useEffect } from 'react';
import { User, Package, Hash, Target, Plus, Trash2, Save } from 'lucide-react';
import { toast } from 'react-hot-toast';
import api from '../../services/api';

const RequestForm = ({
  usersList = [],
  resourcesList = [],
  purposes = [],
  onClose,
  fetchData,
  currentUser
}) => {
  // --- ЛОКАЛЬНИЙ СТАН ФОРМИ ---
  const [selectedUserId, setSelectedUserId] = useState('');
  const [formRows, setFormRows] = useState([{ resource: '', quantity: '', purpose: '' }]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Автоматично встановлюємо ID поточного користувача, якщо він не адмін
  useEffect(() => {
    if (currentUser && !currentUser.is_admin && !selectedUserId) {
      const me = usersList.find(u => u.email === currentUser.email);
      if (me) setSelectedUserId(me.id.toString());
    }
  }, [usersList, currentUser, selectedUserId]);

  // --- ОБРОБНИКИ ПОДІЙ ---
  const handleFormChange = (index, field, value) => {
    const newRows = [...formRows];
    newRows[index][field] = value;
    setFormRows(newRows);
  };

  const addFormRow = () => {
    setFormRows([...formRows, { resource: '', quantity: '', purpose: '' }]);
  };

  const removeFormRow = (index) => {
    setFormRows(formRows.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    // Валідація
    if (formRows.some(r => !r.resource || !r.quantity || !r.purpose)) {
      return toast.error("Будь ласка, заповніть усі поля у кожному рядку");
    }
    if (currentUser?.is_admin && !selectedUserId) {
      return toast.error("Будь ласка, оберіть заявника");
    }

    setIsSubmitting(true);
    try {
      await Promise.all(formRows.map(row => {
        const payload = {
          resource: parseInt(row.resource),
          quantity_requested: parseFloat(row.quantity),
          purpose: parseInt(row.purpose),
          user: selectedUserId ? parseInt(selectedUserId) : currentUser.id
        };
        return api.post('/requests/', payload);
      }));

      toast.success("Заявки успішно надіслано");
      fetchData(); // Оновлюємо дані в App
      onClose();   // Закриваємо модалку
    } catch (error) {
      toast.error("Помилка при відправці заявки");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* СЕКЦІЯ ЗАЯВНИКА */}
      <div className="bg-blue-50/50 p-5 rounded-2xl border border-blue-100">
        {currentUser?.is_admin ? (
          <div className="text-left">
            <label className="flex items-center gap-1.5 text-[10px] font-black uppercase text-slate-400 ml-1 mb-1.5 italic">
              <User size={12} /> Заявник (Адмін-панель)
            </label>
            <select
              value={selectedUserId}
              onChange={(e) => setSelectedUserId(e.target.value)}
              className="w-full px-4 py-3 bg-white border-2 border-slate-100 rounded-xl font-bold outline-none focus:border-blue-500 transition-all cursor-pointer"
            >
              <option value="">Оберіть користувача...</option>
              {usersList?.map(u => (
                <option key={u.id} value={u.id}>
                  {u.full_name || u.username}
                </option>
              ))}
            </select>
          </div>
        ) : (
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-blue-600 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-blue-200">
              <User size={24} />
            </div>
            <div className="text-left">
              <p className="text-[10px] font-black uppercase text-blue-400 leading-none mb-1">Ваш профіль заявника</p>
              <p className="font-black text-slate-900 text-lg">
                {currentUser?.first_name} {currentUser?.last_name}
              </p>
              <p className="text-xs font-medium text-slate-500 italic">{currentUser?.email}</p>
            </div>
          </div>
        )}
      </div>

      {/* СПИСОК ПОЗИЦІЙ */}
      <div className="space-y-4 max-h-[40vh] overflow-y-auto pr-2 custom-scrollbar">
        {formRows.map((row, index) => (
          <div key={index} className="group flex flex-col md:flex-row gap-4 items-end bg-slate-50 p-5 rounded-2xl border border-slate-200 transition-all hover:border-blue-200">

            {/* Вибір ресурсу */}
            <div className="flex-1 w-full text-left">
              <label className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400 mb-1.5 uppercase ml-1">
                <Package size={12} /> Ресурс
              </label>
              <select
                value={row.resource}
                onChange={(e) => handleFormChange(index, 'resource', e.target.value)}
                className="w-full p-3 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500/20 text-sm font-bold"
              >
                <option value="">Оберіть ресурс...</option>
                {resourcesList?.map(r => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
            </div>

            {/* Кількість */}
            <div className="w-full md:w-32 text-left">
              <label className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400 mb-1.5 uppercase ml-1">
                <Hash size={12} /> К-сть
              </label>
              <input
                type="number"
                min="1"
                value={row.quantity}
                onChange={(e) => handleFormChange(index, 'quantity', e.target.value)}
                placeholder="0"
                className="w-full p-3 rounded-xl border border-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 text-sm font-black"
              />
            </div>

            {/* Призначення */}
            <div className="w-full md:w-60 text-left">
              <label className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400 mb-1.5 uppercase ml-1">
                <Target size={12} /> Призначення
              </label>
              <select
                value={row.purpose}
                onChange={(e) => handleFormChange(index, 'purpose', e.target.value)}
                className="w-full p-3 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500/20 text-sm font-medium"
              >
                <option value="">Оберіть ціль...</option>
                {purposes?.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>

            {/* Видалення рядка */}
            {formRows.length > 1 && (
              <button
                onClick={() => removeFormRow(index)}
                className="p-3 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-xl mb-0.5"
              >
                <Trash2 size={20} />
              </button>
            )}
          </div>
        ))}
      </div>

      <button
        onClick={addFormRow}
        className="flex items-center gap-2 text-blue-600 font-black text-xs uppercase tracking-widest hover:bg-blue-50 px-6 py-4 rounded-2xl border-2 border-dashed border-blue-100 w-full justify-center transition-all"
      >
        <Plus size={18} /> Додати ще одну позицію
      </button>

      <div className="flex gap-4 justify-end pt-6 border-t border-slate-100">
        <button onClick={onClose} className="px-8 py-4 text-slate-400 font-bold hover:text-slate-600">
          Скасувати
        </button>
        <button
          onClick={handleSubmit}
          disabled={isSubmitting}
          className="flex items-center gap-3 px-10 py-4 bg-blue-600 text-white font-black rounded-2xl shadow-xl shadow-blue-200 hover:bg-slate-900 transition-all disabled:bg-slate-300"
        >
          {isSubmitting ? "НАДСИЛАННЯ..." : (
            <>
              <Save size={20} />
              <span>ЗБЕРЕГТИ ЗАЯВКУ</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default RequestForm;