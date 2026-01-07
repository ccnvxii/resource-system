import React, { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  // Стейт (стан) для збереження даних з бекенду
  const [stocks, setStocks] = useState([]);
  const [requests, setRequests] = useState([]);
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);

  // Адреса вашого Django API
  // Якщо ви запускаєте на Windows/Docker, localhost працює завдяки прокиданню портів
  const API_URL = 'http://127.0.0.1:8000/api';

  // Функція для завантаження всіх даних (Склади і Заявки)
  const fetchData = async () => {
    try {
      // Робимо два запити паралельно
      const stockRes = await axios.get(`${API_URL}/stocks/`);
      const reqRes = await axios.get(`${API_URL}/requests/`);

      setStocks(stockRes.data);
      setRequests(reqRes.data);
    } catch (error) {
      console.error("Помилка з'єднання з сервером:", error);
    }
  };

  // Завантажуємо дані при першому запуску сторінки
  useEffect(() => {
    fetchData();
  }, []);

  // Функція для кнопки "Розподілити" (POST запит)
  const handleDistribute = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/distribute/`);
      setPlan(response.data); // Зберігаємо план розподілу
      fetchData(); // Оновлюємо таблиці (бо цифри зміняться)
    } catch (error) {
      alert("Помилка при розподілі ресурсів! Перевірте консоль.");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // Допоміжна функція для кольорів статусу
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

        {/* --- ОСНОВНИЙ КОНТЕНТ (СІТКА) --- */}
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
                  {stocks.map((stock) => (
                    <tr key={stock.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4 font-medium text-slate-700">{stock.warehouse_name}</td>
                      <td className="px-6 py-4">
                        <div className="font-semibold text-slate-800">{stock.resource_name}</div>
                        <div className="text-xs text-slate-500 mt-0.5">{stock.resource_category}</div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className="font-mono font-bold text-slate-700 bg-slate-100 px-2 py-1 rounded">
                          {Number(stock.amount).toFixed(0)}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {stocks.length === 0 && (
                    <tr>
                      <td colSpan="3" className="px-6 py-8 text-center text-slate-400">Склади порожні</td>
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
                  {/* Індикатор пріоритету зліва */}
                  <div className={`absolute left-0 top-0 bottom-0 w-1.5 ${req.priority > 7 ? 'bg-red-500' : 'bg-blue-400'}`}></div>

                  <div className="flex justify-between items-start pl-3">
                    <div>
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
              {requests.length === 0 && (
                <div className="text-center text-slate-400 py-10">Немає активних заявок</div>
              )}
            </div>
          </section>
        </div>

        {/* --- ПАНЕЛЬ ДІЙ (КНОПКА) --- */}
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
            {loading ? (
              <span className="flex items-center gap-3">
                <svg className="animate-spin h-6 w-6 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Обчислення...
              </span>
            ) : (
              "🚀 ЗАПУСТИТИ РОЗПОДІЛ"
            )}
          </button>
        </div>

        {/* --- БЛОК РЕЗУЛЬТАТІВ --- */}
        {plan && (
          <div className="animate-fade-in-up bg-green-50 rounded-2xl border-2 border-green-200 p-8 shadow-sm">
            <h3 className="text-2xl font-bold text-green-800 mb-6 flex items-center gap-3">
              ✅ План розподілу успішно створено
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {plan.items.map((item) => (
                <div key={item.id} className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-green-500 flex flex-col justify-between">
                  <div>
                    <div className="flex justify-between items-start">
                       <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Трансфер</span>
                       <span className="text-xs bg-green-100 text-green-700 font-bold px-2 py-1 rounded">ID: {item.id}</span>
                    </div>
                    <div className="mt-2 text-xl font-bold text-slate-800">{item.resource_name}</div>
                    <div className="text-sm text-slate-500 mt-1">
                      Звідки: <span className="font-semibold text-slate-700">{item.warehouse_name}</span>
                    </div>
                  </div>
                  <div className="mt-4 pt-4 border-t border-slate-100 flex justify-between items-end">
                    <span className="text-sm text-slate-400">Кількість:</span>
                    <span className="text-3xl font-extrabold text-green-600">+{Number(item.amount).toFixed(0)}</span>
                  </div>
                </div>
              ))}
            </div>
            {plan.items.length === 0 && (
               <p className="text-green-700 italic">Алгоритм завершив роботу, але нових переміщень не знайдено (можливо, не вистачає ресурсів або всі заявки виконані).</p>
            )}
          </div>
        )}

      </div>
    </div>
  );
}

export default App;