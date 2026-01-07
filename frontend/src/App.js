import React, { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  const [stocks, setStocks] = useState([]);
  const [requests, setRequests] = useState([]);
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);

  // ВАЖЛИВО: Додаємо стейт для довідника ресурсів
  const [resourcesMap, setResourcesMap] = useState({});

  const API_URL = 'http://127.0.0.1:8000/api';

  const fetchData = async () => {
    try {
      // 1. Завантажуємо все паралельно (Склади, Заявки і РЕСУРСИ)
      const [stockRes, reqRes, resRes] = await Promise.all([
        axios.get(`${API_URL}/stocks/`),
        axios.get(`${API_URL}/requests/`),
        axios.get(`${API_URL}/resources/`)
      ]);

      // 2. Створюємо "Словник" ресурсів: { 1: {name: "Аспірин", ...}, 2: {name: "Бинти", ...} }
      // Це потрібно, щоб швидко знаходити назву по ID
      const resMap = {};
      resRes.data.forEach(r => {
        resMap[r.id] = r;
      });
      setResourcesMap(resMap);

      setStocks(stockRes.data);
      setRequests(reqRes.data);
    } catch (error) {
      console.error("Помилка з'єднання з сервером:", error);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleDistribute = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/distribute/`);
      setPlan(response.data);
      fetchData();
    } catch (error) {
      alert("Помилка при розподілі ресурсів!");
      console.error(error);
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
    <div className="min-h-screen bg-slate-50 font-sans text-slate-800 p-6 md:p-10">
      <div className="max-w-7xl mx-auto space-y-10">

        {/* --- ЗАГОЛОВОК --- */}
        <header className="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <div>
            <h1 className="text-3xl font-extrabold text-blue-600 tracking-tight">
              Resource System
            </h1>
            <p className="text-slate-500 mt-1 font-medium">Система управління гуманітарною допомогою</p>
          </div>
          <button
            onClick={fetchData}
            className="mt-4 md:mt-0 px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-lg transition-all active:scale-95"
          >
            🔄 Оновити дані
          </button>
        </header>

        {/* --- ОСНОВНИЙ КОНТЕНТ --- */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

          {/* 1. Блок Складів */}
          <section className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="p-6 border-b border-slate-100 bg-slate-50/50">
              <h2 className="text-xl font-bold flex items-center gap-2">
                📦 Запаси на складах
                <span className="text-xs font-normal bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">{stocks.length} позицій</span>
              </h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="bg-slate-50 text-slate-500 uppercase text-xs font-bold">
                  <tr>
                    <th className="px-6 py-4">Склад</th>
                    <th className="px-6 py-4">Ресурс</th>
                    <th className="px-6 py-4 text-right">Кількість</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {stocks.map((stock) => {
                    // ТУТ ГОЛОВНА МАГІЯ: Знаходимо ресурс по ID
                    const resource = resourcesMap[stock.resource] || { name: 'Завантаження...', category_name: '...' };

                    return (
                      <tr key={stock.id} className="hover:bg-slate-50 transition-colors">
                        <td className="px-6 py-4 font-medium text-slate-700">{stock.warehouse_name}</td>
                        <td className="px-6 py-4">
                          <div className="font-semibold text-slate-800">{resource.name}</div>
                          <div className="text-xs text-slate-500 mt-0.5">{resource.category_name}</div>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <span className="font-mono font-bold text-slate-700 bg-slate-100 px-2 py-1 rounded">
                            {Number(stock.amount).toFixed(0)} <span className="text-xs text-gray-400">{resource.unit}</span>
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                  {stocks.length === 0 && (
                    <tr>
                      <td colSpan="3" className="px-6 py-8 text-center text-slate-400">Склади порожні або немає зв'язку з БД</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          {/* 2. Блок Заявок */}
          <section className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-[500px]">
             <div className="p-6 border-b border-slate-100 bg-slate-50/50">
              <h2 className="text-xl font-bold flex items-center gap-2">
                📋 Активні заявки
                <span className="text-xs font-normal bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full">{requests.length} шт</span>
              </h2>
            </div>
            <div className="overflow-y-auto flex-1 p-6 space-y-4 bg-slate-50/30">
              {requests.map((req) => (
                <div key={req.id} className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
                  <div className={`absolute left-0 top-0 bottom-0 w-1.5 ${req.priority > 7 ? 'bg-red-500' : 'bg-blue-400'}`}></div>

                  <div className="flex justify-between items-start pl-3">
                    <div>
                      {/* У заявках ім'я приходить відразу, бо ми так налаштували Serializer */}
                      <h3 className="font-bold text-lg text-slate-800">{req.resource_name}</h3>
                      <p className="text-sm text-slate-500 mt-1">
                        Користувач: <span className="font-medium text-slate-700">{req.username}</span>
                      </p>
                      <div className="mt-2 flex gap-2">
                         <span className="text-xs font-bold px-2 py-1 rounded bg-slate-100 text-slate-600 border border-slate-200">
                           Пріоритет: {req.priority}
                         </span>
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="text-xs text-slate-400 uppercase font-bold tracking-wider mb-1">Прогрес</div>
                      <div className="font-mono text-lg font-bold text-slate-700">
                        <span className={req.quantity_allocated >= req.quantity_requested ? "text-green-600" : "text-blue-600"}>
                          {Number(req.quantity_allocated).toFixed(0)}
                        </span>
                        <span className="text-slate-400 mx-1">/</span>
                        {Number(req.quantity_requested).toFixed(0)}
                      </div>
                      <div className={`mt-2 text-xs font-bold px-2 py-1 rounded border inline-block ${getStatusColor(req.status)}`}>
                        {req.status === 'done' ? 'ВИКОНАНО' : req.status === 'partial' ? 'ЧАСТКОВО' : 'НОВА'}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* --- ПАНЕЛЬ ДІЙ --- */}
        <div className="flex justify-center py-4">
          <button
            onClick={handleDistribute}
            disabled={loading}
            className={`
              group relative px-10 py-5 rounded-full text-xl font-bold text-white shadow-xl transform transition-all 
              ${loading 
                ? 'bg-slate-400 cursor-not-allowed' 
                : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:scale-105 hover:shadow-2xl hover:from-blue-500 hover:to-indigo-500 active:scale-95'}
            `}
          >
            {loading ? "Обчислення..." : "🚀 ЗАПУСТИТИ РОЗПОДІЛ"}
          </button>
        </div>

        {/* --- РЕЗУЛЬТАТИ --- */}
        {plan && (
          <div className="animate-fade-in-up bg-green-50 rounded-2xl border-2 border-green-200 p-8 shadow-sm">
            <h3 className="text-2xl font-bold text-green-800 mb-6">✅ План розподілу:</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {plan.items.map((item) => (
                <div key={item.id} className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-green-500">
                  <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">Трансфер</div>
                  <div className="mt-2 text-xl font-bold text-slate-800">{item.resource_name}</div>
                  <div className="text-sm text-slate-500 mt-1">
                    Звідки: <span className="font-semibold text-slate-700">{item.warehouse_name}</span>
                  </div>
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