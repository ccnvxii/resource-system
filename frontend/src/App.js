import React, { useState, useEffect, useCallback } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import {
  Home, ClipboardList, ArrowDownCircle, PackagePlus, Info, CheckCircle2
} from 'lucide-react';

// Сервіси та константи
import api from './services/api';
import { PURPOSE_MAP } from './type/purposes';
import authService from './services/authService';

// Компоненти
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

function App() {
  // --- СТАН ДАНИХ ---
  const [stocks, setStocks] = useState([]);
  const [requests, setRequests] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [resourcesList, setResourcesList] = useState([]);
  const [resourcesMap, setResourcesMap] = useState({});
  const [usersList, setUsersList] = useState([]);
  const [plan, setPlan] = useState(null);

  // --- СТАН ІНТЕРФЕЙСУ ---
  const [isLandingMode, setIsLandingMode] = useState(() => localStorage.getItem('isLandingMode') !== 'false');
  const [loading, setLoading] = useState(false);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isStockInOpen, setIsStockInOpen] = useState(false);
  const [isAddResourceOpen, setIsAddResourceOpen] = useState(false);
  const [requestTab, setRequestTab] = useState('active');
  const [selectedUserId, setSelectedUserId] = useState('');
  const [formRows, setFormRows] = useState([{ resource: '', quantity: '', purpose: 'personal' }]);
  const [isAuthOpen, setIsAuthOpen] = useState(false);

  const [currentUser, setCurrentUser] = useState(() => authService.getUser());

  // --- ЛОГІКА ЗАВАНТАЖЕННЯ ДАНИХ ---
  const fetchData = useCallback(async () => {
    try {
      const baseRequests = [
        api.get('/stocks/'),
        api.get('/requests/'),
        api.get('/resources/'),
        api.get('/warehouses/')
      ];

      if (currentUser?.is_admin) {
        baseRequests.push(api.get('/users/'));
      }

      const results = await Promise.all(baseRequests);
      const [stockRes, reqRes, resRes, whRes, userRes] = results;

      // Мапінг ресурсів для швидкого доступу за ID
      const resMap = {};
      resRes.data.forEach(r => { resMap[r.id] = r; });

      setResourcesMap(resMap);
      setResourcesList(resRes.data);
      setWarehouses(whRes.data);
      setStocks(stockRes.data);
      setRequests(reqRes.data);

      if (userRes) {
        setUsersList(userRes.data);
        if (currentUser.is_admin && userRes.data.length > 0) {
          setSelectedUserId(prev => prev || userRes.data[0].id.toString());
        }
      }
    } catch (error) {
      // Помилки вже обробляються в api.js через toast
      console.error("Data fetch failed", error);
    }
  }, [currentUser]);

  useEffect(() => {
    localStorage.setItem('isLandingMode', isLandingMode);
    if (!isLandingMode && currentUser) fetchData();
  }, [fetchData, isLandingMode, currentUser]);

  // --- АВТОРИЗАЦІЯ ---
  const handleAuthSuccess = (userData, tokens) => {
    authService.setTokens(tokens.access, tokens.refresh);

    const isAdmin = userData.email === 'admin@resq.ua' || userData.username === 'admin';
    const loggedUser = { ...userData, is_admin: isAdmin };

    authService.setUser(loggedUser); // Використовуємо сервіс
    setCurrentUser(loggedUser);
    setIsLandingMode(false);
    setIsAuthOpen(false);
  };

  const handleLogout = () => {
    authService.clearAuth(); // Очищуємо все через сервіс
    setCurrentUser(null);
    setIsLandingMode(true);
    setPlan(null);
  };

  // --- ОБРОБКА ФОРМ ---
  const handleSubmitRequest = async () => {
    setLoading(true);
    try {
      await Promise.all(formRows.map(row => {
        if (!row.resource || !row.quantity) return Promise.resolve();

        const payload = {
          resource: parseInt(row.resource),
          quantity_requested: parseFloat(row.quantity),
          purpose: row.purpose
        };

        // Тільки якщо selectedUserId існує (вибраний адміном), додаємо його
        if (selectedUserId) {
          payload.user = parseInt(selectedUserId);
        }

        return api.post('/requests/', payload);
      }));

      toast.success("Заявки успішно створено", { icon: <CheckCircle2 className="text-emerald-500" /> });
      setIsFormOpen(false);
      setFormRows([{ resource: '', quantity: '', purpose: 'personal' }]);
      fetchData();
    } catch (e) {
      // Помилка оброблена в api.js
    } finally { setLoading(false); }
  };

  const handleDistribute = async () => {
    const loadId = toast.loading("Розрахунок плану розподілу...");
    setLoading(true);
    try {
      const response = await api.post('/distribute/');
      if (response.data.message) {
        toast(response.data.message, { id: loadId, icon: <Info className="text-blue-500" /> });
        setPlan(null);
      } else {
        toast.success("План сформовано", { id: loadId });
        setPlan(response.data);
      }
      fetchData();
    } catch (err) {
      toast.dismiss(loadId);
    } finally { setLoading(false); }
  };

  // --- РЕНДЕР ---
  if (isLandingMode) {
    return (
      <>
        <Landing
          onEnter={() => currentUser ? setIsLandingMode(false) : setIsAuthOpen(true)}
          stats={{ stocks: stocks.length, requests: requests.length, warehouses: warehouses.length }}
        />
        <AuthModal isOpen={isAuthOpen} onClose={() => setIsAuthOpen(false)} onSuccess={handleAuthSuccess} />
        <Toaster position="top-center" />
      </>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-800 p-4 md:p-10 relative">
      <Toaster position="top-center" toastOptions={{ className: 'rounded-xl font-bold shadow-xl' }} />

      {/* МОДАЛЬНІ ВІКНА */}
      <Modal isOpen={isFormOpen} onClose={() => setIsFormOpen(false)} title="Нова заявка" icon={ClipboardList}>
        <RequestForm
          usersList={usersList} resourcesList={resourcesList}
          selectedUserId={selectedUserId} setSelectedUserId={setSelectedUserId}
          formRows={formRows} handleFormChange={(idx, f, v) => { const n = [...formRows]; n[idx][f] = v; setFormRows(n); }}
          addFormRow={() => setFormRows([...formRows, { resource: '', quantity: '', purpose: 'personal' }])}
          removeFormRow={(idx) => setFormRows(formRows.filter((_, i) => i !== idx))}
          handleSubmitRequest={handleSubmitRequest} loading={loading}
          onClose={() => setIsFormOpen(false)} currentUser={currentUser}
        />
      </Modal>

      <Modal isOpen={isStockInOpen} onClose={() => setIsStockInOpen(false)} title="Поповнення складів" icon={ArrowDownCircle} maxWidth="max-w-3xl">
        <StockInForm warehouses={warehouses} resources={resourcesList} onSubmit={fetchData} loading={loading} onClose={() => setIsStockInOpen(false)} />
      </Modal>

      <Modal isOpen={isAddResourceOpen} onClose={() => setIsAddResourceOpen(false)} title="Новий тип ресурсу" icon={PackagePlus} maxWidth="max-w-lg">
        <AddResourceForm onResourceAdded={() => { fetchData(); setIsAddResourceOpen(false); }} onClose={() => setIsAddResourceOpen(false)} />
      </Modal>

      {/* ОСНОВНИЙ КОНТЕНТ */}
      <div className="max-w-7xl mx-auto space-y-8 pb-24">
        <Header
          onOpenForm={() => setIsFormOpen(true)}
          onOpenStockIn={() => setIsStockInOpen(true)}
          onAddResource={() => setIsAddResourceOpen(true)}
          onRefresh={fetchData} onLogout={handleLogout} currentUser={currentUser}
        />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <StockTable stocks={stocks} resourcesMap={resourcesMap} onRefresh={fetchData} />
          <RequestList requests={requests} requestTab={requestTab} setRequestTab={setRequestTab} purposeMap={PURPOSE_MAP} />
        </div>

        {currentUser?.is_admin && (
          <div className="flex flex-col items-center py-8">
            <button
              onClick={handleDistribute}
              disabled={loading}
              className={`px-16 py-5 rounded-2xl text-xl font-black text-white shadow-2xl transition-all ${loading ? 'bg-slate-400' : 'bg-blue-600 hover:scale-105 active:scale-95'}`}
            >
              {loading ? "АНАЛІЗ ДАНИХ..." : "ВИКОНАТИ РОЗПОДІЛ"}
            </button>
          </div>
        )}

        {plan && <DistributionPlan plan={plan} purposeMap={PURPOSE_MAP} />}
      </div>

      {/* КНОПКА ПОВЕРНЕННЯ */}
      <button
        onClick={() => setIsLandingMode(true)}
        className="fixed bottom-8 left-8 flex items-center gap-2 px-6 py-4 bg-white shadow-2xl rounded-2xl border border-slate-100 text-slate-500 hover:text-blue-600 transition-all hover:scale-105 active:scale-95"
      >
        <Home size={20} /> <span className="text-xs font-black uppercase tracking-widest">Головна</span>
      </button>
    </div>
  );
}

export default App;