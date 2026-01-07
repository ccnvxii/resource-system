import React, { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  // --- СТАНИ (STATE) ---
  const [stocks, setStocks] = useState([]);
  const [requests, setRequests] = useState([]);
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);

  // Довідники
  const [resourcesMap, setResourcesMap] = useState({});
  const [resourcesList, setResourcesList] = useState([]);
  const [usersList, setUsersList] = useState([]);

  // UI стани
  const [popup, setPopup] = useState({ isOpen: false, type: 'info', title: '', message: '' });
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState('');

  // НОВЕ: Перемикач вкладок (active = в роботі, history = виконані)
  const [requestTab, setRequestTab] = useState('active');

  const [formRows, setFormRows] = useState([
    { resource: '', quantity: '', purpose: 'personal' }
  ]);

  const API_URL = 'http://127.0.0.1:8000/api';

  const PURPOSE_MAP = {
    'military': { label: 'Військові', icon: '⚔️', color: 'bg-red-100 text-red-800' },
    'hospital': { label: 'Лікарня', icon: '🏥', color: 'bg-blue-100 text-blue-800' },
    'disaster': { label: 'Катастрофа', icon: '🔥', color: 'bg-orange-100 text-orange-800' },
    'refugees': { label: 'ВПО', icon: '🏃', color: 'bg-yellow-100 text-yellow-800' },
    'school':   { label: 'Школа', icon: '🏫', color: 'bg-purple-100 text-purple-800' },
    'personal': { label: 'Особисте', icon: '👤', color: 'bg-gray-100 text-gray-800' },
  };

  const showPopup = (title, message, type = 'info') => setPopup({ isOpen: true, title, message, type });
  const closePopup = () => setPopup({ ...popup, isOpen: false });

  const fetchData = async () => {
    try {
      const [stockRes, reqRes, resRes, userRes] = await Promise.all([
        axios.get(`${API_URL}/stocks/`),
        axios.get(`${API_URL}/requests/`),
        axios.get(`${API_URL}/resources/`),
        axios.get(`${API_URL}/users/`)
      ]);

      const resMap = {};
      resRes.data.forEach(r => { resMap[r.id] = r; });
      setResourcesMap(resMap);
      setResourcesList(resRes.data);
      setUsersList(userRes.data);

      if (userRes.data.length > 0 && !selectedUserId) {
        setSelectedUserId(userRes.data[0].id);
      }

      setStocks(stockRes.data);
      setRequests(reqRes.data);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleDistribute = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/distribute/`);
      if (response.data.message) {
        showPopup("Інфо", response.data.message, "info");
        setPlan(null);
      } else {
        setPlan(response.data);
      }
      fetchData();
    } catch (error) {
      showPopup("Помилка", "Не вдалося виконати розподіл.", "error");
    } finally {
      setLoading(false);
    }
  };

  // --- ФОРМА ---
  const handleFormChange = (index, field, value) => {
    const newRows = [...formRows];
    newRows[index][field] = value;
    setFormRows(newRows);
  };

  const addFormRow = () => {
    setFormRows([...formRows, { resource: '', quantity: '', purpose: 'personal' }]);
  };

  const removeFormRow = (index) => {
    const newRows = formRows.filter((_, i) => i !== index);
    setFormRows(newRows);
  };

  const handleSubmitRequest = async () => {
    if (!selectedUserId) {
      showPopup("Увага", "Оберіть заявника.", "error");
      return;
    }
    for (let row of formRows) {
      if (!row.resource || !row.quantity) {
        showPopup("Увага", "Заповніть всі поля.", "error");
        return;
      }
    }
    setLoading(true);
    try {
      const promises = formRows.map(row => {
        return axios.post(`${API_URL}/requests/`, {
          user: selectedUserId,
          resource: row.resource,
          quantity_requested: row.quantity,
          purpose: row.purpose,
          status: 'new'
        });
      });
      await Promise.all(promises);
      showPopup("Успіх", `Створено ${formRows.length} заявок!`, "success");
      setIsFormOpen(false);
      setFormRows([{ resource: '', quantity: '', purpose: 'personal' }]);
      fetchData();
    } catch (error) {
      const msg = error.response?.data ? JSON.stringify(error.response.data) : "Помилка";
      showPopup("Помилка", msg, "error");
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'done': return <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-bold border border-green-200">ВИКОНАНО</span>;
      case 'partial': return <span className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded-full text-xs font-bold border border-yellow-200">ЧАСТКОВО</span>;
      default: return <span className="px-2 py-1 bg-blue-50 text-blue-600 rounded-full text-xs font-bold border border-blue-100">НОВА</span>;
    }
  };

  // --- ЛОГІКА ФІЛЬТРАЦІЇ (НОВЕ) ---
  const activeRequests = requests.filter(r => r.status !== 'done');
  const historyRequests = requests.filter(r => r.status === 'done');

  // Що показуємо зараз?
  const displayedRequests = requestTab === 'active' ? activeRequests : historyRequests;

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-800 p-6 md:p-10 relative">

      {/* POP-UP */}
      {popup.isOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fade-in">
          <div className={`bg-white rounded-2xl shadow-2xl max-w-sm w-full mx-4 p-6 border-t-4 ${popup.type === 'error' ? 'border-red-500' : 'border-blue-500'}`}>
            <h3 className="text-lg font-bold mb-2">{popup.title}</h3>
            <p className="text-slate-600 mb-6 text-sm">{popup.message}</p>
            <div className="flex justify-end">
              <button onClick={closePopup} className="px-4 py-2 bg-slate-800 text-white font-medium rounded-lg hover:bg-slate-700">ОК</button>
            </div>
          </div>
        </div>
      )}

      {/* FORM MODAL */}
      {isFormOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl m-4 p-6 md:p-8 relative animate-scale-up">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-2xl font-bold text-slate-800">📝 Нова заявка</h2>
                <p className="text-xs text-slate-400 font-mono mt-1">MODE: PRIORITY MATRIX</p>
              </div>
              <button onClick={() => setIsFormOpen(false)} className="text-slate-400 hover:text-slate-600 text-2xl">✕</button>
            </div>
            <div className="mb-6 bg-blue-50 p-4 rounded-xl border border-blue-100">
              <label className="block text-sm font-bold text-blue-800 mb-2">👤 Заявник</label>
              <select
                value={selectedUserId}
                onChange={(e) => setSelectedUserId(e.target.value)}
                className="w-full p-3 rounded-lg border border-blue-200 focus:ring-2 focus:ring-blue-500 outline-none bg-white font-medium"
              >
                {usersList.map(u => (<option key={u.id} value={u.id}>{u.username} ({u.email})</option>))}
              </select>
            </div>
            <div className="space-y-3 max-h-[50vh] overflow-y-auto pr-2 custom-scrollbar">
              {formRows.map((row, index) => (
                <div key={index} className="flex flex-col md:flex-row gap-3 items-end bg-slate-50 p-4 rounded-xl border border-slate-200">
                  <div className="flex-1 w-full">
                    <label className="block text-xs font-bold text-slate-500 mb-1 uppercase">Ресурс</label>
                    <select
                      value={row.resource}
                      onChange={(e) => handleFormChange(index, 'resource', e.target.value)}
                      className="w-full p-2.5 rounded-lg border border-slate-300 outline-none"
                    >
                      <option value="">-- Оберіть --</option>
                      {resourcesList.map(r => (<option key={r.id} value={r.id}>{r.name} ({r.unit})</option>))}
                    </select>
                  </div>
                  <div className="w-full md:w-32">
                    <label className="block text-xs font-bold text-slate-500 mb-1 uppercase">Кількість</label>
                    <input type="number" min="1" value={row.quantity} onChange={(e) => handleFormChange(index, 'quantity', e.target.value)} className="w-full p-2.5 rounded-lg border border-slate-300 outline-none"/>
                  </div>
                  <div className="w-full md:w-64">
                    <label className="block text-xs font-bold text-slate-500 mb-1 uppercase">Призначення</label>
                    <select value={row.purpose} onChange={(e) => handleFormChange(index, 'purpose', e.target.value)} className="w-full p-2.5 rounded-lg border border-slate-300 outline-none bg-white font-medium">
                      <option value="military">⚔️ Військові (10)</option>
                      <option value="hospital">🏥 Лікарня (9)</option>
                      <option value="disaster">🔥 Катастрофа (8)</option>
                      <option value="refugees">🏃 ВПО (6)</option>
                      <option value="school">🏫 Школа (4)</option>
                      <option value="personal">👤 Особисте (1)</option>
                    </select>
                  </div>
                  {formRows.length > 1 && (<button onClick={() => removeFormRow(index)} className="p-3 text-red-400 hover:text-red-600 rounded-lg">🗑️</button>)}
                </div>
              ))}
            </div>
            <div className="mt-4">
              <button onClick={addFormRow} className="flex items-center gap-2 text-blue-600 font-bold hover:bg-blue-50 px-4 py-2 rounded-lg border border-dashed border-blue-300 w-full justify-center">➕ Додати позицію</button>
            </div>
            <div className="mt-8 flex gap-3 justify-end pt-5 border-t border-slate-100">
              <button onClick={() => setIsFormOpen(false)} className="px-5 py-2.5 text-slate-600 font-semibold hover:bg-slate-100 rounded-lg">Скасувати</button>
              <button onClick={handleSubmitRequest} disabled={loading} className="px-6 py-2.5 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700 shadow-lg active:scale-95">{loading ? "Збереження..." : "✅ Зберегти"}</button>
            </div>
          </div>
        </div>
      )}

      {/* --- MAIN CONTENT --- */}
      <div className="max-w-7xl mx-auto space-y-8">

        <header className="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <div>
            <h1 className="text-3xl font-extrabold text-slate-800 tracking-tight flex items-center gap-3">
              <span className="text-blue-600">ResQ</span> System
            </h1>
            <p className="text-slate-500 mt-1 font-medium">Система гуманітарного розподілу з матрицею пріоритетів</p>
          </div>
          <div className="flex gap-3 mt-4 md:mt-0">
            <button onClick={() => setIsFormOpen(true)} className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-md active:scale-95 flex items-center gap-2">📝 Створити заявку</button>
            <button onClick={fetchData} className="px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-lg active:scale-95">🔄</button>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

          {/* СКЛАДИ */}
          <section className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-[600px]">
            <div className="p-5 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
              <h2 className="text-lg font-bold flex items-center gap-2 text-slate-800">📦 Запаси на складах</h2>
              <span className="text-xs font-bold bg-slate-200 text-slate-600 px-2 py-1 rounded-md">{stocks.length} поз.</span>
            </div>
            <div className="overflow-y-auto overflow-x-auto flex-1 custom-scrollbar">
              <table className="w-full text-sm text-left relative">
                <thead className="bg-slate-50 text-slate-500 uppercase text-xs font-bold sticky top-0 z-10 shadow-sm">
                  <tr>
                    <th className="px-6 py-3 bg-slate-50">Склад</th>
                    <th className="px-6 py-3 bg-slate-50">Ресурс</th>
                    <th className="px-6 py-3 text-right bg-slate-50">Наявність</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {stocks.map((stock) => {
                    const resource = resourcesMap[stock.resource] || { name: '...', category_name: '...' };
                    return (
                      <tr key={stock.id} className="hover:bg-slate-50 transition-colors">
                        <td className="px-6 py-3 font-medium text-slate-700">{stock.warehouse_name}</td>
                        <td className="px-6 py-3"><div className="font-semibold text-slate-800">{resource.name}</div><div className="text-xs text-slate-400">{resource.category_name}</div></td>
                        <td className="px-6 py-3 text-right"><span className="font-mono font-bold text-slate-700 bg-slate-100 px-2 py-1 rounded">{Number(stock.amount).toFixed(0)} <span className="text-xs text-gray-400 font-normal">{resource.unit}</span></span></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          {/* --- ЗАЯВКИ (З ВКЛАДКАМИ) --- */}
          <section className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-[600px]">

            {/* Шапка з перемикачем вкладок */}
            <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
              <h2 className="text-lg font-bold flex items-center gap-2 text-slate-800">
                📋 Черга заявок
              </h2>

              {/* ПЕРЕМИКАЧ (TABS) */}
              <div className="flex bg-slate-200/50 p-1 rounded-lg">
                <button
                  onClick={() => setRequestTab('active')}
                  className={`px-4 py-1.5 rounded-md text-xs font-bold transition-all ${requestTab === 'active' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                >
                  В черзі ({activeRequests.length})
                </button>
                <button
                  onClick={() => setRequestTab('history')}
                  className={`px-4 py-1.5 rounded-md text-xs font-bold transition-all ${requestTab === 'history' ? 'bg-white text-green-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                >
                  Архів ({historyRequests.length})
                </button>
              </div>
            </div>

            <div className="overflow-y-auto flex-1 p-4 space-y-3 bg-slate-50/30 custom-scrollbar">
              {displayedRequests.map((req) => {
                const purposeData = PURPOSE_MAP[req.purpose] || { label: req.purpose, icon: '❓', color: 'bg-gray-200' };
                // Для історії робимо картки трохи тьмянішими
                const isHistory = req.status === 'done';

                return (
                  <div key={req.id} className={`bg-white p-4 rounded-xl border ${isHistory ? 'border-slate-100 opacity-80' : 'border-slate-200 shadow-sm'} hover:shadow-md transition-all relative overflow-hidden group`}>

                    {/* Якщо виконано - зелена смужка, інакше - за пріоритетом */}
                    <div className="absolute left-0 top-0 bottom-0 w-1.5 transition-colors"
                         style={{ backgroundColor: isHistory ? '#10b981' : (req.priority >= 8 ? '#ef4444' : req.priority >= 4 ? '#f59e0b' : '#3b82f6') }}>
                    </div>

                    <div className="pl-3">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                           <div className="flex items-center gap-2 mb-1">
                             <span className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${purposeData.color}`}>
                               {purposeData.icon} {purposeData.label}
                             </span>
                             <span className="text-xs text-slate-400 font-mono">ID:{req.id}</span>
                           </div>
                           <h3 className={`font-bold text-base leading-tight ${isHistory ? 'text-slate-500 line-through' : 'text-slate-800'}`}>
                             {req.resource_name}
                           </h3>
                           <p className="text-xs text-slate-500 mt-0.5">Від: <span className="font-medium text-slate-700">{req.username}</span></p>
                        </div>
                        <div className="text-right">
                          <div className="text-[10px] text-slate-400 font-bold uppercase">Пріоритет</div>
                          <div className="text-xl font-extrabold text-slate-700 leading-none">{Number(req.priority).toFixed(1)}</div>
                        </div>
                      </div>
                      <div className="flex justify-between items-end border-t border-slate-50 pt-2 mt-2">
                         {getStatusBadge(req.status)}
                         <div className="text-right">
                            <span className="text-xs text-slate-400 mr-1">Видано:</span>
                            <span className="font-mono font-bold text-sm">
                              <span className={req.quantity_allocated >= req.quantity_requested ? "text-green-600" : "text-slate-800"}>
                                {Number(req.quantity_allocated).toFixed(0)}
                              </span>
                              <span className="text-slate-300 mx-1">/</span>
                              {Number(req.quantity_requested).toFixed(0)}
                            </span>
                         </div>
                      </div>
                    </div>
                  </div>
                );
              })}

              {displayedRequests.length === 0 && (
                <div className="text-center text-slate-400 py-20 flex flex-col items-center">
                  <span className="text-4xl mb-2">{requestTab === 'active' ? '🎉' : '📂'}</span>
                  {requestTab === 'active' ? 'Всі заявки оброблено!' : 'Історія порожня'}
                </div>
              )}
            </div>
          </section>
        </div>

        <div className="flex justify-center py-6">
          <button onClick={handleDistribute} disabled={loading} className={`group relative px-12 py-4 rounded-full text-xl font-bold text-white shadow-xl transform transition-all ${loading ? 'bg-slate-400 cursor-not-allowed' : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:scale-105 hover:shadow-2xl active:scale-95'}`}>
            {loading ? "Обчислення..." : "ЗАПУСТИТИ РОЗПОДІЛ"}
          </button>
        </div>

        {plan && plan.items && (
          <div className="animate-fade-in-up bg-green-50 rounded-2xl border-2 border-green-200 p-8 shadow-sm mb-10">
            <h3 className="text-2xl font-bold text-green-800 mb-6 flex items-center gap-2">
              ✅ План розподілу сформовано
              <span className="text-sm font-normal bg-green-200 text-green-800 px-3 py-1 rounded-full">{plan.items.length} трансферів</span>
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {plan.items.map((item) => {
                // Отримуємо іконку та назву призначення
                const purposeInfo = PURPOSE_MAP[item.purpose] || { label: item.purpose, icon: '📦', color: 'bg-gray-100' };

                return (
                  <div key={item.id} className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-green-500 hover:shadow-md transition-shadow flex flex-col justify-between">

                    {/* Заголовок картки */}
                    <div>
                      <div className="flex justify-between items-start mb-2">
                        <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">Трансфер #{item.id}</div>
                        <div className="text-green-600 font-bold text-xl bg-green-50 px-2 rounded">+{Number(item.amount).toFixed(0)}</div>
                      </div>

                      <div className="text-lg font-bold text-slate-800 mb-4">{item.resource_name}</div>
                    </div>

                    {/* Логістика: Звідки -> Куди */}
                    <div className="space-y-3 text-sm border-t border-slate-100 pt-3">

                      {/* Звідки */}
                      <div className="flex items-center gap-2 text-slate-600">
                        <span className="text-lg">📤</span>
                        <span className="text-xs text-slate-400 uppercase font-bold">Звідки:</span>
                        <span className="font-semibold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded">
                          {item.warehouse_name}
                        </span>
                      </div>
                      {/* Куди */}
                      <div className="flex items-center gap-2 text-slate-600">
                        <span className="text-lg">📥</span>
                        <span className="text-xs text-slate-400 uppercase font-bold">Куди:</span>

                        <div className="flex flex-col">
                           <span className={`text-xs font-bold px-1.5 py-0.5 rounded w-fit mb-0.5 ${purposeInfo.color}`}>
                             {purposeInfo.icon} {purposeInfo.label}
                           </span>
                           <span className="font-medium text-slate-800">{item.recipient_name}</span>
                        </div>
                      </div>

                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;