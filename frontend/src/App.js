import React, {useState, useEffect} from 'react';
import {Toaster, toast} from 'react-hot-toast';
import {Home, ClipboardList, ArrowDownCircle, PackagePlus, Info} from 'lucide-react';

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
    // --- СТАН КОРИСТУВАЧА ТА ІНТЕРФЕЙСУ ---
    const [currentUser, setCurrentUser] = useState(() => authService.getUser());
    const [isLandingMode, setIsLandingMode] = useState(() => localStorage.getItem('isLandingMode') !== 'false');
    const [loading, setLoading] = useState(false);
    const [plan, setPlan] = useState(null);

    // --- КАСТОМНІ ХУКИ ---
    const {modals, openModal, closeModal} = useModal({
        request: false,
        stockIn: false,
        resource: false,
        auth: false
    });

    const {data, fetchData} = useFetchData(currentUser);

    // --- ЕФЕКТИ ---
    useEffect(() => {
        localStorage.setItem('isLandingMode', isLandingMode);
        if (!isLandingMode && currentUser) {
            fetchData().catch(() => toast.error("Не вдалося оновити дані"));
        }
        // КРИТИЧНО: Прибираємо fetchData з залежностей, щоб розірвати нескінченний цикл рендерингу!
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isLandingMode, currentUser]);

    // --- ОБРОБНИКИ ПОДІЙ ---
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

    // ЦЕНТРАЛІЗОВАНЕ БЕЗПЕЧНЕ ВИДАЛЕННЯ ЗАЯВКИ
    const handleDeleteRequest = async (requestId) => {
        const lid = toast.loading("Оновлення черги потреб...");
        setLoading(true);
        try {
            await api.delete(`/requests/${requestId}/`);
            toast.success("Заявку успішно видалено", { id: lid });

            // Обов'язково скидаємо старий план розподілу, оскільки матриця потреб змінилася
            setPlan(null);

            // Оновлюємо таблиці та графіки дашборду
            await fetchData();
        } catch (e) {
            console.error("Помилка при видаленні заявки:", e);
            toast.error("Не вдалося видалити заявку", { id: lid });
        } finally {
            setLoading(false);
        }
    };

    const handleDistribute = async () => {
        const lid = toast.loading("Аналіз запасів та потреб...");
        setLoading(true);
        try {
            const res = await api.post('/distribute/');
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

            {/* МОДАЛЬНІ ВІКНА */}
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

            {/* ОСНОВНИЙ КОНТЕНТ */}
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
                            onDeleteRequest={handleDeleteRequest} // Передаємо виправлену функцію
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

                {currentUser?.is_admin && (
                    <div className="flex justify-center py-8">
                        <button
                            onClick={handleDistribute}
                            disabled={loading}
                            className={`px-16 py-5 rounded-2xl text-xl font-black text-white shadow-2xl transition-all ${loading ? 'bg-slate-400 cursor-not-allowed' : 'bg-blue-600 hover:scale-105 active:scale-95'}`}
                        >
                            {loading ? "ОБРОБКА..." : "ВИКОНАТИ РОЗПОДІЛ"}
                        </button>
                    </div>
                )}

                {/* --- ПЛАН РОЗПОДІЛУ (ВІДОБРАЖАЄТЬСЯ ПРИ НАЯВНОСТІ) --- */}
                {currentUser?.is_admin && plan && (
                    <DistributionPlan
                        plan={plan}
                        purposeMap={data.purposeMap}
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