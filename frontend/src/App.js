import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Toaster, toast } from 'react-hot-toast';
import {
  Home, ShieldAlert, Stethoscope, Flame, Footprints, GraduationCap,
  User, ArrowDownCircle, PackagePlus, ClipboardList, Info, CheckCircle2,
} from 'lucide-react';

// Імпорт компонентів
import Header from './components/Header/Header';
import StockTable from './components/StockTable/StockTable';
import RequestList from './components/RequestList/RequestList';
import RequestForm from './components/RequestForm/RequestForm';
import DistributionPlan from './components/DistributionPlan/DistributionPlan';
import StockInForm from './components/StockInForm/StockInForm';
import Landing from './components/Landing';
import AddResourceForm from './components/AddResourceForm';
import Modal from './components/Modal';
import AuthModal from './components/Auth';

const API_URL = '/api';

// --- НАЛАШТУВАННЯ AXIOS ---
axios.defaults.baseURL = 'http://localhost:8000';

// Додавання токена до кожного запиту
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

const PURPOSE_MAP = {
  'military': { label: 'Військові', icon: <ShieldAlert size={14} />, color: 'bg-red-100 text-red-800' },
  'hospital': { label: 'Лікарня', icon: <Stethoscope size={14} />, color: 'bg-blue-100 text-blue-800' },
  'disaster': { label: 'Катастрофа', icon: <Flame size={14} />, color: 'bg-orange-100 text-orange-800' },
  'refugees': { label: 'ВПО', icon: <Footprints size={14} />, color: 'bg-yellow-100 text-yellow-800' },
  'school':   { label: 'Школа', icon: <GraduationCap size={14} />, color: 'bg-purple-100 text-purple-800' },
  'personal': { label: 'Особисте', icon: <User size={14} />, color: 'bg-gray-100 text-gray-800' },
};

function App() {
  const [stocks, setStocks] = useState([]);
  const [requests, setRequests] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [resourcesList, setResourcesList] = useState([]);
  const [resourcesMap, setResourcesMap] = useState({});
  const [usersList, setUsersList] = useState([]);
  const [plan, setPlan] = useState(null);

  const [isLandingMode, setIsLandingMode] = useState(() => {
    const saved = localStorage.getItem('isLandingMode');
    return saved === null ? true : saved === 'true';
  });

  const [loading, setLoading] = useState(false);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isStockInOpen, setIsStockInOpen] = useState(false);
  const [isAddResourceOpen, setIsAddResourceOpen] = useState(false);
  const [requestTab, setRequestTab] = useState('active');
  const [selectedUserId, setSelectedUserId] = useState('');
  const [formRows, setFormRows] = useState([{ resource: '', quantity: '', purpose: 'personal' }]);
  const [isAuthOpen, setIsAuthOpen] = useState(false);

  const [currentUser, setCurrentUser] = useState(() => {
    const savedUser = localStorage.getItem('currentUser');
    return savedUser ? JSON.parse(savedUser) : null;
  });

  // Автоматичне оновлення токена при 401 (Unauthorized)
  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          try {
            const refreshToken = localStorage.getItem('refresh_token');
            const res = await axios.post(`${API_URL}/token/refresh/`, { refresh: refreshToken });
            localStorage.setItem('access_token', res.data.access);
            return axios(originalRequest);
          } catch (err) {
            handleLogout();
            return Promise.reject(err);
          }
        }
        return Promise.reject(error);
      }
    );
    return () => axios.interceptors.response.eject(interceptor);
  }, []);

  const fetchData = useCallback(async () => {
    try {
      // 1. Запити, які доступні всім авторизованим користувачам
      const baseRequests = [
        axios.get(`${API_URL}/stocks/`),
        axios.get(`${API_URL}/requests/`),
        axios.get(`${API_URL}/resources/`),
        axios.get(`${API_URL}/warehouses/`)
      ];

      // 2. Список користувачів вантажимо тільки якщо це адмін
      if (currentUser?.is_admin) {
        baseRequests.push(axios.get(`${API_URL}/users/`));
      } else {
        // Якщо волонтер — робимо фейковий проміс, щоб структура масиву результатів не ламалася
        baseRequests.push(Promise.resolve({ data: [] }));
      }

      const [stockRes, reqRes, resRes, whRes, userRes] = await Promise.all(baseRequests);

      const resMap = {};
      resRes.data.forEach(r => { resMap[r.id] = r; });
      setResourcesMap(resMap);
      setResourcesList(resRes.data);
      setWarehouses(whRes.data);
      setStocks(stockRes.data);
      setRequests(reqRes.data);
      setUsersList(userRes.data);

      // 3. АВТОМАТИЧНИЙ ВИБІР ЗАЯВНИКА
      if (currentUser) {
        if (currentUser.is_admin) {
          // Якщо адмін — вибираємо першого юзера зі списку для форми
          if (userRes.data.length > 0) {
            setSelectedUserId(prev => prev || userRes.data[0].id.toString());
          }
        } else {
          // Якщо волонтер — робимо запит до списку користувачів (якщо права дозволяють)
          // або використовуємо ID, який ми отримали при логіні.
          // Для надійності шукаємо за email у списку
          const me = userRes.data.find(u => u.email === currentUser.email);
          if (me) setSelectedUserId(me.id.toString());
        }
      }
    } catch (error) {
      console.error("Fetch error:", error);
    }
  }, [currentUser]);

  useEffect(() => {
    if (!isLandingMode && currentUser) fetchData();
  }, [fetchData, isLandingMode, currentUser]);

  const handleAuthSuccess = (userData, tokens) => {
    localStorage.setItem('access_token', tokens.access);
    localStorage.setItem('refresh_token', tokens.refresh);

    // Визначаємо адміна за поштою (тимчасово) або за полем з бекенду
    const isAdmin = userData.email === 'admin@resq.ua' || userData.username === 'admin';
    const loggedUser = {
      ...userData,
      is_admin: isAdmin
    };

    setCurrentUser(loggedUser);
    localStorage.setItem('currentUser', JSON.stringify(loggedUser));
    setIsLandingMode(false);
    setIsAuthOpen(false);
    toast.success(`Вітаємо, ${loggedUser.username}!`);
  };

  const handleLogout = () => {
    setCurrentUser(null);
    localStorage.removeItem('currentUser');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setIsLandingMode(true);
    setPlan(null);
    toast.success("Вихід успішний");
  };

  const handleSubmitRequest = async () => {
    // Додаємо перевірку: якщо це адмін, він МАЄ обрати юзера
    if (currentUser?.is_admin && !selectedUserId) return toast.error("Оберіть заявника");

    setLoading(true);
    try {
      await Promise.all(formRows.map(row => {
        if (!row.resource || !row.quantity) return Promise.resolve();

        // Формуємо об'єкт запиту
        const payload = {
          resource: parseInt(row.resource),
          quantity_requested: parseFloat(row.quantity),
          purpose: row.purpose,
          status: 'new'
        };

        // Додаємо юзера в payload ТІЛЬКИ якщо він вибраний (для адміна)
        if (selectedUserId) {
          payload.user = parseInt(selectedUserId);
        }

        return axios.post(`${API_URL}/requests/`, payload);
      }));
      toast.success("Заявки зареєстровано", { icon: <CheckCircle2 size={20} className="text-emerald-500" /> });
      setIsFormOpen(false);
      setFormRows([{ resource: '', quantity: '', purpose: 'personal' }]);
      fetchData();
    } catch (e) {
      toast.error("Помилка при створенні");
    } finally { setLoading(false); }
  };

  const handleAddStock = async (formData) => {
    setLoading(true);
    try {
      await Promise.all(formData.items.map(item =>
        axios.post(`${API_URL}/stocks/add_resource/`, {
          warehouse: parseInt(formData.warehouse),
          resource: parseInt(item.resource),
          amount: parseFloat(item.amount)
        })
      ));
      toast.success("Запаси оновлено", { icon: <ArrowDownCircle size={20} className="text-emerald-500" /> });
      setIsStockInOpen(false);
      fetchData();
    } catch (e) { toast.error("Помилка поповнення"); }
    finally { setLoading(false); }
  };

  const handleDistribute = async () => {
    const loadId = toast.loading("Розрахунок плану розподілу...");
    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/distribute/`);
      if (response.data.message) {
        toast(response.data.message, { id: loadId, icon: <Info size={20} className="text-blue-500" /> });
        setPlan(null);
      } else {
        toast.success("План сформовано", { id: loadId });
        setPlan(response.data);
      }
      fetchData();
    } catch (error) {
      toast.error("Помилка алгоритму", { id: loadId });
    } finally { setLoading(false); }
  };

  if (isLandingMode) {
    return (
      <>
        <Landing onEnter={() => currentUser ? setIsLandingMode(false) : setIsAuthOpen(true)} stats={{ stocks: stocks.length, requests: requests.length, warehouses: warehouses.length }} />
        <AuthModal isOpen={isAuthOpen} onClose={() => setIsAuthOpen(false)} onSuccess={handleAuthSuccess} />
        <Toaster position="top-center" />
      </>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-800 p-4 md:p-10 relative">
      <Toaster position="top-center" toastOptions={{ className: 'rounded-xl font-bold shadow-xl' }} />

      <Modal isOpen={isFormOpen} onClose={() => setIsFormOpen(false)} title="Нова заявка" icon={ClipboardList}>
        <RequestForm
          usersList={usersList}
          resourcesList={resourcesList}
          selectedUserId={selectedUserId}
          setSelectedUserId={setSelectedUserId}
          formRows={formRows}
          handleFormChange={(idx, f, v) => { const n = [...formRows]; n[idx][f] = v; setFormRows(n); }}
          addFormRow={() => setFormRows([...formRows, { resource: '', quantity: '', purpose: 'personal' }])}
          removeFormRow={(idx) => setFormRows(formRows.filter((_, i) => i !== idx))}
          handleSubmitRequest={handleSubmitRequest}
          loading={loading}
          onClose={() => setIsFormOpen(false)}
          currentUser={currentUser}
        />
      </Modal>

      <Modal isOpen={isStockInOpen} onClose={() => setIsStockInOpen(false)} title="Поповнення складів" icon={ArrowDownCircle} maxWidth="max-w-3xl">
        <StockInForm warehouses={warehouses} resources={resourcesList} onSubmit={handleAddStock} loading={loading} onClose={() => setIsStockInOpen(false)} />
      </Modal>

      <Modal isOpen={isAddResourceOpen} onClose={() => setIsAddResourceOpen(false)} title="Новий тип ресурсу" icon={PackagePlus} maxWidth="max-w-lg">
        <AddResourceForm onResourceAdded={() => { fetchData(); setIsAddResourceOpen(false); }} onClose={() => setIsAddResourceOpen(false)} />
      </Modal>

      <div className="max-w-7xl mx-auto space-y-8 pb-24">
        <Header
          onOpenForm={() => setIsFormOpen(true)}
          onOpenStockIn={() => setIsStockInOpen(true)}
          onAddResource={() => setIsAddResourceOpen(true)}
          onRefresh={fetchData}
          onLogout={handleLogout}
          currentUser={currentUser}
        />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <StockTable stocks={stocks} resourcesMap={resourcesMap} onRefresh={fetchData} />
          <RequestList requests={requests} requestTab={requestTab} setRequestTab={setRequestTab} purposeMap={PURPOSE_MAP} />
        </div>

        {currentUser?.is_admin && (
          <div className="flex flex-col items-center py-8">
            <button onClick={handleDistribute} disabled={loading} className={`px-16 py-5 rounded-2xl text-xl font-black text-white shadow-2xl transition-all ${loading ? 'bg-slate-400' : 'bg-blue-600 hover:scale-105'}`}>
              {loading ? "Аналіз..." : "ВИКОНАТИ РОЗПОДІЛ"}
            </button>
          </div>
        )}

        {plan && <DistributionPlan plan={plan} purposeMap={PURPOSE_MAP} />}
      </div>

      <button onClick={() => setIsLandingMode(true)} className="fixed bottom-8 left-8 flex items-center gap-2 px-6 py-4 bg-white shadow-2xl rounded-2xl border border-slate-100 text-slate-500 hover:text-blue-600 transition-all">
        <Home size={20} /> <span className="text-xs font-black uppercase tracking-widest">Головна</span>
      </button>
    </div>
  );
}

export default App;