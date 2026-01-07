import React, { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  const [stocks, setStocks] = useState([]);
  const [requests, setRequests] = useState([]);
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);

  // Довідники
  const [resourcesMap, setResourcesMap] = useState({});
  const [resourcesList, setResourcesList] = useState([]);
  // НОВЕ: Список користувачів
  const [usersList, setUsersList] = useState([]);

  // --- POP-UP ---
  const [popup, setPopup] = useState({ isOpen: false, type: 'info', title: '', message: '' });

  // --- FORM MODAL ---
  const [isFormOpen, setIsFormOpen] = useState(false);

  // НОВЕ: Обраний користувач для заявки
  const [selectedUserId, setSelectedUserId] = useState('');

  const [formRows, setFormRows] = useState([
    { resource: '', quantity: '', priority: 5 }
  ]);

  const API_URL = 'http://127.0.0.1:8000/api';

  const showPopup = (title, message, type = 'info') => setPopup({ isOpen: true, title, message, type });
  const closePopup = () => setPopup({ ...popup, isOpen: false });

  // --- ЗАВАНТАЖЕННЯ ДАНИХ ---
  const fetchData = async () => {
    try {
      // Додали завантаження users
      const [stockRes, reqRes, resRes, userRes] = await Promise.all([
        axios.get(`${API_URL}/stocks/`),
        axios.get(`${API_URL}/requests/`),
        axios.get(`${API_URL}/resources/`),
        axios.get(`${API_URL}/users/`) // <-- Завантажуємо юзерів
      ]);

      const resMap = {};
      resRes.data.forEach(r => { resMap[r.id] = r; });
      setResourcesMap(resMap);
      setResourcesList(resRes.data);

      setUsersList(userRes.data); // Зберігаємо юзерів

      // Якщо є юзери, обираємо першого автоматично
      if (userRes.data.length > 0) {
        setSelectedUserId(userRes.data[0].id);
      }

      setStocks(stockRes.data);
      setRequests(reqRes.data);
    } catch (error) {
      console.error(error);
      // Не лякаємо користувача попапом при старті, просто пишемо в консоль
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
      showPopup("Помилка", "Щось пішло не так при розподілі.", "error");
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
    setFormRows([...formRows, { resource: '', quantity: '', priority: 5 }]);
  };

  const removeFormRow = (index) => {
    const newRows = formRows.filter((_, i) => i !== index);
    setFormRows(newRows);
  };

  const handleSubmitRequest = async () => {
    // Валідація
    if (!selectedUserId) {
      showPopup("Помилка", "Оберіть користувача!", "error");
      return;
    }

    for (let row of formRows) {
      if (!row.resource || !row.quantity) {
        showPopup("Помилка", "Заповніть всі поля (Ресурс та Кількість)", "error");
        return;
      }
    }

    setLoading(true);
    try {
      const promises = formRows.map(row => {
        return axios.post(`${API_URL}/requests/`, {
          user: selectedUserId, // <-- Використовуємо реальний ID
          resource: row.resource,
          quantity_requested: row.quantity,
          priority: row.priority,
          status: 'new'
        });
      });

      await Promise.all(promises);

      showPopup("Успіх", `Створено ${formRows.length} нових заявок!`, "success");
      setIsFormOpen(false);
      setFormRows([{ resource: '', quantity: '', priority: 5 }]);
      fetchData();
    } catch (error) {
      console.error(error);
      // Показуємо детальну помилку, якщо сервер відповів текстом
      const msg = error.response?.data ? JSON.stringify(error.response.data) : "Перевірте консоль";
      showPopup("Помилка збереження", msg, "error");
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'done': return 'bg-green-100 text-green-700 border-green-200';
      case 'partial': return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      default: return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-800 p-6 md:p-10 relative">

      {/* POP-UP */}
      {popup.isOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fade-in">
          <div className={`bg-white rounded-2xl shadow-2xl max-w-sm w-full mx-4 p-6 border-t-4 ${popup.type === 'error' ? 'border-red-500' : 'border-blue-500'}`}>
            <h3 className={`text-lg font-bold mb-2 ${popup.type === 'error' ? 'text-red-600' : 'text-slate-800'}`}>{popup.title}</h3>
            <p className="text-slate-600 mb-4 break-words text-sm">{popup.message}</p>
            <div className="flex justify-end">
              <button onClick={closePopup} className="px-4 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-700">ОК</button>
            </div>
          </div>
        </div>
      )}

      {/* FORM MODAL */}
      {isFormOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl m-4 p-6 md:p-8 relative">

            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-slate-800">📝 Нова заявка</h2>
              <button onClick={() => setIsFormOpen(false)} className="text-slate-400 hover:text-slate-600 text-2xl">✕</button>
            </div>

            {/* ВИБІР КОРИСТУВАЧА */}
            <div className="mb-6 bg-blue-50 p-4 rounded-xl border border-blue-100">
              <label className="block text-sm font-bold text-blue-800 mb-2">👤 Хто створює заявку?</label>
              <select
                value={selectedUserId}
                onChange={(e) => setSelectedUserId(e.target.value)}
                className="w-full p-2.5 rounded-lg border border-blue-200 focus:ring-2 focus:ring-blue-500 outline-none bg-white"
              >
                {usersList.length === 0 && <option value="">Немає користувачів (перевірте backend)</option>}
                {usersList.map(u => (
                  <option key={u.id} value={u.id}>{u.username} (ID: {u.id})</option>
                ))}
              </select>
            </div>

            <div className="space-y-3 max-h-[50vh] overflow-y-auto pr-2">
              {formRows.map((row, index) => (
                <div key={index} className="flex flex-col md:flex-row gap-3 items-end bg-slate-50 p-3 rounded-xl border border-slate-200">

                  {/* Ресурс */}
                  <div className="flex-1 w-full">
                    <label className="block text-xs font-bold text-slate-500 mb-1 uppercase">Ресурс</label>
                    <select
                      value={row.resource}
                      onChange={(e) => handleFormChange(index, 'resource', e.target.value)}
                      className="w-full p-2 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 outline-none"
                    >
                      <option value="">-- Оберіть --</option>
                      {resourcesList.map(r => (
                        <option key={r.id} value={r.id}>{r.name} ({r.unit})</option>
                      ))}
                    </select>
                  </div>

                  {/* Кількість */}
                  <div className="w-full md:w-32">
                    <label className="block text-xs font-bold text-slate-500 mb-1 uppercase">Кількість</label>
                    <input
                      type="number"
                      min="1"
                      value={row.quantity}
                      onChange={(e) => handleFormChange(index, 'quantity', e.target.value)}
                      className="w-full p-2 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                  </div>

                  {/* Пріоритет */}
                  <div className="w-full md:w-32">
                    <label className="block text-xs font-bold text-slate-500 mb-1 uppercase">Пріоритет</label>
                    <select
                      value={row.priority}
                      onChange={(e) => handleFormChange(index, 'priority', e.target.value)}
                      className="w-full p-2 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 outline-none"
                    >
                      {[1,2,3,4,5,6,7,8,9,10].map(n => (
                        <option key={n} value={n}>{n}</option>
                      ))}
                    </select>
                  </div>

                  {/* Видалити */}
                  {formRows.length > 1 && (
                    <button
                      onClick={() => removeFormRow(index)}
                      className="p-2.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors mb-[1px]"
                    >
                      🗑️
                    </button>
                  )}
                </div>
              ))}
            </div>

            <div className="mt-4">
              <button
                onClick={addFormRow}
                className="flex items-center gap-2 text-blue-600 font-bold hover:bg-blue-50 px-4 py-2 rounded-lg transition-colors"
              >
                ➕ Додати ще ресурс
              </button>
            </div>

            <div className="mt-8 flex gap-3 justify-end pt-4 border-t border-slate-100">
              <button onClick={() => setIsFormOpen(false)} className="px-5 py-2.5 text-slate-600 font-semibold hover:bg-slate-100 rounded-lg">Скасувати</button>
              <button onClick={handleSubmitRequest} disabled={loading} className="px-6 py-2.5 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700 shadow-lg active:scale-95 transition-all">
                {loading ? "Відправка..." : "Зберегти заявку"}
              </button>
            </div>

          </div>
        </div>
      )}

      {/* MAIN CONTENT */}
      <div className="max-w-7xl mx-auto space-y-10">
        <header className="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <div>
            <h1 className="text-3xl font-extrabold text-blue-600 tracking-tight">Resource System</h1>
            <p className="text-slate-500 mt-1 font-medium">Система управління гуманітарною допомогою</p>
          </div>
          <div className="flex gap-3 mt-4 md:mt-0">
            <button onClick={() => setIsFormOpen(true)} className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-md transition-all active:scale-95 flex items-center gap-2">📝 Створити заявку</button>
            <button onClick={fetchData} className="px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-lg transition-all active:scale-95">🔄 Оновити</button>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <section className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="p-6 border-b border-slate-100 bg-slate-50/50">
              <h2 className="text-xl font-bold flex items-center gap-2">📦 Запаси на складах <span className="text-xs font-normal bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">{stocks.length}</span></h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="bg-slate-50 text-slate-500 uppercase text-xs font-bold">
                  <tr><th className="px-6 py-4">Склад</th><th className="px-6 py-4">Ресурс</th><th className="px-6 py-4 text-right">Кількість</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {stocks.map((stock) => {
                    const resource = resourcesMap[stock.resource] || { name: '...', category_name: '...' };
                    return (
                      <tr key={stock.id} className="hover:bg-slate-50">
                        <td className="px-6 py-4 font-medium text-slate-700">{stock.warehouse_name}</td>
                        <td className="px-6 py-4"><div className="font-semibold text-slate-800">{resource.name}</div><div className="text-xs text-slate-500">{resource.category_name}</div></td>
                        <td className="px-6 py-4 text-right"><span className="font-mono font-bold text-slate-700 bg-slate-100 px-2 py-1 rounded">{Number(stock.amount).toFixed(0)} <span className="text-xs text-gray-400">{resource.unit}</span></span></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          <section className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-[500px]">
             <div className="p-6 border-b border-slate-100 bg-slate-50/50">
              <h2 className="text-xl font-bold flex items-center gap-2">📋 Активні заявки <span className="text-xs font-normal bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full">{requests.length}</span></h2>
            </div>
            <div className="overflow-y-auto flex-1 p-6 space-y-4 bg-slate-50/30">
              {requests.map((req) => (
                <div key={req.id} className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:shadow-md relative overflow-hidden">
                  <div className={`absolute left-0 top-0 bottom-0 w-1.5 ${req.priority > 7 ? 'bg-red-500' : 'bg-blue-400'}`}></div>
                  <div className="flex justify-between items-start pl-3">
                    <div>
                      <h3 className="font-bold text-lg text-slate-800">{req.resource_name}</h3>
                      <p className="text-sm text-slate-500 mt-1">Користувач: <span className="font-medium text-slate-700">{req.username}</span></p>
                      <div className="mt-2"><span className="text-xs font-bold px-2 py-1 rounded bg-slate-100 border">Пріоритет: {req.priority}</span></div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-slate-400 uppercase font-bold tracking-wider mb-1">Прогрес</div>
                      <div className="font-mono text-lg font-bold text-slate-700"><span className={req.quantity_allocated >= req.quantity_requested ? "text-green-600" : "text-blue-600"}>{Number(req.quantity_allocated).toFixed(0)}</span> <span className="text-slate-400 mx-1">/</span>{Number(req.quantity_requested).toFixed(0)}</div>
                      <div className={`mt-2 text-xs font-bold px-2 py-1 rounded border inline-block ${getStatusColor(req.status)}`}>{req.status === 'done' ? 'ВИКОНАНО' : req.status === 'partial' ? 'ЧАСТКОВО' : 'НОВА'}</div>
                    </div>
                  </div>
                </div>
              ))}
              {requests.length === 0 && <div className="text-center text-slate-400 py-10">Немає активних заявок</div>}
            </div>
          </section>
        </div>

        <div className="flex justify-center py-4">
          <button onClick={handleDistribute} disabled={loading} className={`group relative px-10 py-5 rounded-full text-xl font-bold text-white shadow-xl transform transition-all ${loading ? 'bg-slate-400' : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:scale-105 hover:shadow-2xl active:scale-95'}`}>
            {loading ? "Обчислення..." : "🚀 ЗАПУСТИТИ РОЗПОДІЛ"}
          </button>
        </div>

        {plan && plan.items && (
          <div className="animate-fade-in-up bg-green-50 rounded-2xl border-2 border-green-200 p-8 shadow-sm">
            <h3 className="text-2xl font-bold text-green-800 mb-6">✅ План розподілу:</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {plan.items.map((item) => (
                <div key={item.id} className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-green-500">
                  <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">Трансфер</div>
                  <div className="mt-2 text-xl font-bold text-slate-800">{item.resource_name}</div>
                  <div className="text-sm text-slate-500 mt-1">Звідки: <span className="font-semibold text-slate-700">{item.warehouse_name}</span></div>
                  <div className="mt-4 pt-4 border-t border-slate-100 flex justify-between items-end">
                    <span className="text-sm text-slate-400">Кількість:</span>
                    <span className="text-3xl font-extrabold text-green-600">+{Number(item.amount).toFixed(0)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;