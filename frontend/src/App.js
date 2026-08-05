import React, {useState, useEffect} from 'react';
import {Toaster, toast} from 'react-hot-toast';
import {Home, ClipboardList, ArrowDownCircle, PackagePlus, Info, Scale, Zap} from 'lucide-react';

// Сервіси та кастомні хуки
import api from './services/api';
import authService from './services/authService';
import {useModal} from './hooks/useModal';
import {useFetchData} from './hooks/useFetchData';

// Компоненти
import Header from './components/Layout/Header';
import StockTable from './components/Features/StockTable';
import RequestList from './components/Features/RequestList';
import RequestForm from './components/Features/RequestForm';
import DistributionPlan from './components/Features/DistributionPlan';
import StockInForm from './components/Features/StockInForm';
import Landing from './components/Layout/Landing';
import AddResourceForm from './components/Features/AddResourceForm';
import Dashboard from './components/Features/Dashboard';
import AdminLogs from './components/Features/AdminLogs';
import Modal from './components/UI/Modal';
import AuthModal from './components/Auth/Auth';

function App() {
    const [currentUser, setCurrentUser] = useState(() => authService.getUser());
    const [isLandingMode, setIsLandingMode] = useState(() => localStorage.getItem('isLandingMode') !== 'false');
    const [loading, setLoading] = useState(false);
    const [plan, setPlan] = useState(null);

    //  Стан для зберігання обраної стратегії розподілу
    const [distributionStrategy, setDistributionStrategy] = useState('fairness');

    const {modals, openModal, closeModal} = useModal({
        request: false,
        stockIn: false,
        resource: false,
        auth: false
    });

    const {data, fetchData} = useFetchData(currentUser);

    useEffect(() => {
        localStorage.setItem('isLandingMode', isLandingMode);
        if (!isLandingMode && currentUser) {
            fetchData().catch(() => toast.error("Не вдалося оновити дані"));
        }
    }, [isLandingMode, currentUser]);

    const handleAuthSuccess = (userData, tokens) => {
        authService.setTokens(tokens.access, tokens.refresh);
        const isAdmin = userData.is_admin || userData.email === 'admin@resq.ua';
        const userWithRole = {...userData, is_admin: isAdmin};

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

    const handleDeleteRequest = async (requestId) => {
        const lid = toast.loading("Оновлення черги потреб...");
        setLoading(true);
        try {
            await api.delete(`/requests/${requestId}/`);
            toast.success("Заявку успішно видалено", { id: lid });
            setPlan(null);
            await fetchData();
        } catch (e) {
            console.error("Помилка при видаленні заявки:", e);
            toast.error("Не вдалося видалити заявку", { id: lid });
        } finally {
            setLoading(false);
        }
    };

    //  Передача обраної стратегії на бекенд
    const handleDistribute = async () => {
        const lid = toast.loading("Аналіз запасів та потреб...");
        setLoading(true);
        try {
            // Передаємо параметр strategy у тілі запиту
            const res = await api.post('/distribute/', { strategy: distributionStrategy });
            if (res.data.message) {
                toast(res.data.message, {id: lid, icon: <Info className="text-blue-500"/>});
                setPlan(null);
            } else {
                toast.success("План розподілу сформовано", {id: lid});
                setPlan(Array.isArray(res.data) ? {items: res.data} : res.data);
            }
            await fetchData();
        } catch (e) {
            toast.error("Помилка алгоритму розподілу", {id: lid});
        } finally {
            setLoading(false);
        }
    };

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
                <Toaster position="top-center"/>
            </>
        );
    }

    return (
        <div className="min-h-screen bg-slate-50 p-4 md:p-10 relative">
            <Toaster position="top-center" toastOptions={{className: 'rounded-xl font-bold shadow-xl'}}/>

            <Modal isOpen={modals.request} onClose={() => closeModal('request')} title="Нова заявка" icon={ClipboardList}>
                <RequestForm
                    usersList={data.usersList}
                    resourcesList={data.resourcesList}
                    stocks={data.stocks}
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
                    onResourceAdded={() => {
                        fetchData();
                        closeModal('resource');
                    }}
                    onClose={() => closeModal('resource')}
                />
            </Modal>

            <div className="max-w-7xl mx-auto space-y-8 pb-24">
                <Header
                    onOpenForm={() => openModal('request')}
                    onOpenStockIn={currentUser?.is_admin ? () => openModal('stockIn') : null}
                    onAddResource={currentUser?.is_admin ? () => openModal('resource') : null}
                    onRefresh={fetchData}
                    onLogout={handleLogout}
                    currentUser={currentUser}
                />
                <div className={`grid gap-8 ${currentUser?.is_admin ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1'}`}>
                    {currentUser?.is_admin && (
                        <StockTable
                            stocks={data.stocks}
                            resourcesMap={data.resourcesMap}
                            onRefresh={fetchData}
                        />
                    )}

                    <div className="w-full">
                        <RequestList
                            requests={data.requests}
                            purposeMap={data.purposeMap}
                            onRefresh={fetchData}
                            currentUser={currentUser}
                            onDeleteRequest={handleDeleteRequest}
                        />
                    </div>
                </div>

                {currentUser?.is_admin && (
                    <>
                        <Dashboard
                            stocks={data.stocks}
                            requests={data.requests}
                            resourcesMap={data.resourcesMap}
                        />
                        <AdminLogs logs={data.logs || []}/>
                    </>
                )}

                {/* Блок вибору стратегії та кнопка розподілу */}
                {currentUser?.is_admin && (
                    <div className="flex flex-col items-center py-8 space-y-6">

                        {/* Перемикач режимів */}
                        <div className="flex bg-slate-200 p-1.5 rounded-2xl shadow-inner border border-slate-300">
                            <button
                                onClick={() => setDistributionStrategy('fairness')}
                                className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold text-sm transition-all duration-300 ${
                                    distributionStrategy === 'fairness' 
                                    ? 'bg-white text-blue-600 shadow-md ring-1 ring-black/5' 
                                    : 'text-slate-500 hover:text-slate-700'
                                }`}
                            >
                                <Scale size={18} />
                                Max-Min Fairness (Симплекс)
                            </button>
                            <button
                                onClick={() => setDistributionStrategy('triage')}
                                className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold text-sm transition-all duration-300 ${
                                    distributionStrategy === 'triage' 
                                    ? 'bg-white text-red-600 shadow-md ring-1 ring-black/5' 
                                    : 'text-slate-500 hover:text-slate-700'
                                }`}
                            >
                                <Zap size={18} />
                                Тріаж (Жорсткий Пріоритет)
                            </button>
                        </div>

                        {/* Кнопка запуску */}
                        <button
                            onClick={handleDistribute}
                            disabled={loading}
                            className={`px-16 py-5 rounded-2xl text-xl font-black text-white shadow-2xl transition-all ${
                                loading ? 'bg-slate-400 cursor-not-allowed' 
                                : distributionStrategy === 'triage' 
                                    ? 'bg-red-600 hover:bg-red-700 hover:shadow-red-500/30 hover:scale-105 active:scale-95' 
                                    : 'bg-blue-600 hover:bg-blue-700 hover:shadow-blue-500/30 hover:scale-105 active:scale-95'
                            }`}
                        >
                            {loading ? "ОБРОБКА..." : "ВИКОНАТИ РОЗПОДІЛ"}
                        </button>
                    </div>
                )}

                {currentUser?.is_admin && plan && (
                    <DistributionPlan
                        plan={plan}
                        purposeMap={data.purposeMap}
                        strategy={distributionStrategy} // Передаємо стратегію у візуалізацію
                    />
                )}

            </div>

            <button
                onClick={() => setIsLandingMode(true)}
                className="fixed bottom-8 left-8 flex items-center gap-2 px-6 py-4 bg-white shadow-2xl rounded-2xl border border-slate-100 text-slate-500 hover:text-blue-600 transition-all hover:-translate-y-1 active:scale-95"
            >
                <Home size={20}/>
                <span className="text-xs font-black uppercase tracking-widest">Головна</span>
            </button>
        </div>
    );
}

export default App;