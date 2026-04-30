import React, { useState, useEffect } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import { Home, ClipboardList, ArrowDownCircle, PackagePlus, Info } from 'lucide-react';

// Сервіси та кастомні хуки
import api from './services/api';
import authService from './services/authService';
import { useModal } from './hooks/useModal';
import { useFetchData } from './hooks/useFetchData';

// Компоненти
import Header from './components/Layout/Header';
import StockTable from './components/Features/StockTable';
import RequestList from './components/Features/RequestList';
import RequestForm from './components/Features/RequestForm';
import DistributionPlan from './components/Features/DistributionPlan';
import StockInForm from './components/Features/StockInForm';
import Landing from './components/Layout/Landing';
import AddResourceForm from './components/Features/AddResourceForm';
import Modal from './components/UI/Modal';
import AuthModal from './components/Auth/Auth';

function App() {
  // --- СТАН КОРИСТУВАЧА ТА ІНТЕРФЕЙСУ ---
  const [currentUser, setCurrentUser] = useState(() => authService.getUser());
  const [isLandingMode, setIsLandingMode] = useState(() => localStorage.getItem('isLandingMode') !== 'false');
  const [loading, setLoading] = useState(false);
  const [plan, setPlan] = useState(null);

  // --- КАСТОМНІ ХУКИ ---
  // Управління модалками: передаємо початкові стани для кожного вікна
  const { modals, openModal, closeModal } = useModal({
    request: false,
    stockIn: false,
    resource: false,
    auth: false
  });

  // Завантаження даних: повертає об'єкт data з усіма списками та функцію fetchData
  const { data, fetchData } = useFetchData(currentUser);

  // --- ЕФЕКТИ ---
  useEffect(() => {
    localStorage.setItem('isLandingMode', isLandingMode);
    // Завантажуємо дані лише якщо ми не на лендінгу і користувач авторизований
    if (!isLandingMode && currentUser) {
      fetchData().catch(() => toast.error("Не вдалося оновити дані"));
    }
  }, [fetchData, isLandingMode, currentUser]);

  // --- ОБРОБНИКИ ПОДІЙ ---
  const handleAuthSuccess = (userData, tokens) => {
    authService.setTokens(tokens.access, tokens.refresh);
    // Перевірка на адміна за email або прапорцем з бази
    const isAdmin = userData.is_admin || userData.email === 'admin@resq.ua';
    const userWithRole = { ...userData, is_admin: isAdmin };

    authService.setUser(userWithRole);
    setCurrentUser(userWithRole);
    setIsLandingMode(false);
    closeModal('auth');
    toast.success(`Вітаємо, ${userData.first_name || 'користувачу'}!`);
  };

  const handleLogout = () => {
    authService.clearAuth();
    setCurrentUser(null);
    setIsLandingMode(true);
    setPlan(null);
    toast.success("Вихід виконано");
  };

  const handleDistribute = async () => {
    const lid = toast.loading("Аналіз запасів та потреб...");
    setLoading(true);
    try {
      const res = await api.post('/distribute/');
      if (res.data.message) {
        toast(res.data.message, { id: lid, icon: <Info className="text-blue-500" /> });
        setPlan(null);
      } else {
        toast.success("План розподілу сформовано", { id: lid });
        setPlan(res.data);
      }
      fetchData(); // Оновлюємо запаси та статуси заявок після розподілу
    } catch (e) {
      toast.error("Помилка алгоритму розподілу", { id: lid });
    } finally {
      setLoading(false);
    }
  };

  // --- РЕНДЕР ЛЕНДІНГУ ---
  if (isLandingMode) {
    return (
      <>
        <Landing
          onEnter={() => currentUser ? setIsLandingMode(false) : openModal('auth')}
          stats={{
            stocks: data.stocks.length,
            requests: data.requests.length,
            warehouses: data.warehouses.length
          }}
        />
        <AuthModal
          isOpen={modals.auth}
          onClose={() => closeModal('auth')}
          onSuccess={handleAuthSuccess}
        />
        <Toaster position="top-center" />
      </>
    );
  }

  // --- РЕНДЕР ОСНОВНОГО ІНТЕРФЕЙСУ ---
  return (
    <div className="min-h-screen bg-slate-50 p-4 md:p-10 relative">
      <Toaster position="top-center" toastOptions={{ className: 'rounded-xl font-bold shadow-xl' }} />

      {/* МОДАЛЬНІ ВІКНА */}
      <Modal isOpen={modals.request} onClose={() => closeModal('request')} title="Нова заявка" icon={ClipboardList}>
        <RequestForm
          usersList={data.usersList}
          resourcesList={data.resourcesList}
          purposes={data.purposes}
          onClose={() => closeModal('request')}
          fetchData={fetchData}
          currentUser={currentUser}
        />
      </Modal>

      <Modal isOpen={modals.stockIn} onClose={() => closeModal('stockIn')} title="Поповнення складів" icon={ArrowDownCircle} maxWidth="max-w-3xl">
        <StockInForm
          warehouses={data.warehouses}
          resources={data.resourcesList}
          onSubmit={fetchData}
          onClose={() => closeModal('stockIn')}
        />
      </Modal>

      <Modal isOpen={modals.resource} onClose={() => closeModal('resource')} title="Новий тип ресурсу" icon={PackagePlus} maxWidth="max-w-lg">
        <AddResourceForm
          units={data.units}
          onResourceAdded={() => { fetchData(); closeModal('resource'); }}
          onClose={() => closeModal('resource')}
        />
      </Modal>

      {/* ОСНОВНИЙ КОНТЕНТ */}
      <div className="max-w-7xl mx-auto space-y-8 pb-24 animate-in fade-in duration-500">
        <Header
          onOpenForm={() => openModal('request')}
          onOpenStockIn={() => openModal('stockIn')}
          onAddResource={() => openModal('resource')}
          onRefresh={fetchData}
          onLogout={handleLogout}
          currentUser={currentUser}
        />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Таблиця залишків */}
          <StockTable
            stocks={data.stocks}
            resourcesMap={data.resourcesMap}
            onRefresh={fetchData}
          />
          {/* Список заявок */}
          <RequestList
            requests={data.requests}
            purposeMap={data.purposeMap}
          />
        </div>

        {/* ПАНЕЛЬ УПРАВЛІННЯ ДЛЯ АДМІНІСТРАТОРА */}
        {currentUser?.is_admin && (
          <div className="flex flex-col items-center py-8">
            <button
              onClick={handleDistribute}
              disabled={loading}
              className={`px-16 py-5 rounded-2xl text-xl font-black text-white shadow-2xl transition-all 
                ${loading ? 'bg-slate-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 hover:scale-105 active:scale-95'}`}
            >
              {loading ? "ЙДЕ РОЗРАХУНОК..." : "ВИКОНАТИ РОЗПОДІЛ"}
            </button>
          </div>
        )}

        {/* ВІДОБРАЖЕННЯ РЕЗУЛЬТАТІВ РОЗПОДІЛУ */}
        {plan && <DistributionPlan plan={plan} purposeMap={data.purposeMap} />}
      </div>

      {/* КНОПКА ПОВЕРНЕННЯ НА ЛЕНДІНГ */}
      <button
        onClick={() => setIsLandingMode(true)}
        className="fixed bottom-8 left-8 flex items-center gap-2 px-6 py-4 bg-white shadow-2xl rounded-2xl border border-slate-100 text-slate-500 hover:text-blue-600 transition-all hover:-translate-y-1 active:scale-95"
      >
        <Home size={20} />
        <span className="text-xs font-black uppercase tracking-widest">Головна</span>
      </button>
    </div>
  );
}

export default App;