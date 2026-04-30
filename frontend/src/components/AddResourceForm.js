import React, { useState, useEffect } from 'react';
import { Tag, Ruler, Layers, Save, ChevronDown } from 'lucide-react';
import api from '../services/api';
import { Toaster, toast } from 'react-hot-toast';

const AddResourceForm = ({ onResourceAdded, onClose }) => {
  const [categories, setCategories] = useState([]);
  const [formData, setFormData] = useState({ name: '', unit: '', category: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    // Використовуємо api замість axios для завантаження категорій
    api.get('/categories/')
      .then(res => setCategories(res.data))
      .catch(err => console.error("Помилка завантаження категорій:", err));
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // ВИПРАВЛЕНО: беремо дані з formData
      await api.post('/resources/', {
        name: formData.name,
        unit: formData.unit,
        category: parseInt(formData.category)
      });

      toast.success("Ресурс додано!"); // Якщо використовуєте toast
      onResourceAdded();
      onClose();
    } catch (err) {
      setError('Помилка при створенні: можливо, у вас недостатньо прав або ресурс уже існує');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="bg-slate-50 p-5 rounded-2xl border border-slate-200 space-y-4">
        <div>
          <label className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400 mb-1.5 uppercase ml-1">
            <Tag size={12} /> Назва ресурсу
          </label>
          <input
            type="text" required placeholder="Напр: Гемостатичний бинт"
            className="w-full p-3 rounded-xl border border-slate-200 outline-none focus:ring-2 focus:ring-indigo-500/20 text-sm font-medium transition-all"
            value={formData.name}
            onChange={(e) => setFormData({...formData, name: e.target.value})}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400 mb-1.5 uppercase ml-1">
              <Ruler size={12} /> Одиниця
            </label>
            <input
              type="text" required placeholder="шт, упак"
              className="w-full p-3 rounded-xl border border-slate-200 outline-none focus:ring-2 focus:ring-indigo-500/20 text-sm font-bold text-slate-700"
              value={formData.unit}
              onChange={(e) => setFormData({...formData, unit: e.target.value})}
            />
          </div>
          <div>
            <label className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400 mb-1.5 uppercase ml-1">
              <Layers size={12} /> Категорія
            </label>
            <div className="relative">
              <select
                required value={formData.category}
                onChange={(e) => setFormData({...formData, category: e.target.value})}
                className="w-full p-3 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-indigo-500/20 text-sm font-medium appearance-none cursor-pointer"
              >
                <option value="" disabled>Оберіть...</option>
                {categories.map(cat => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name} (x{cat.criticality})
                  </option>
                ))}
              </select>
              <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="text-red-500 text-[11px] font-bold bg-red-50 p-3 rounded-xl border border-red-100">
          {error}
        </div>
      )}

      <div className="flex gap-4 justify-end pt-4">
        <button type="button" onClick={onClose} className="px-6 py-3 text-slate-500 font-bold hover:bg-slate-100 rounded-xl">
          Скасувати
        </button>
        <button type="submit" disabled={loading} className="px-8 py-3 bg-indigo-600 text-white font-bold rounded-xl shadow-lg active:scale-95 disabled:bg-slate-300 transition-all">
          {loading ? "Збереження..." : <><Save size={18} className="inline mr-2"/> Зберегти</>}
        </button>
      </div>
    </form>
  );
};

export default AddResourceForm;