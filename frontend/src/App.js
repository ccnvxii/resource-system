import React, { useState, useEffect } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import { Home, Info } from 'lucide-react';

// Сервіси та кастомні хуки
import api from './services/api';
import authService from './services/authService';
import { useModal } from './hooks/useModal';
import { useFetchData } from './hooks/useFetchData';

// Компоненти
import Header from './components/Layout/Header';
import SidebarNav from './components/Layout/SidebarNav';
import StockTable from './components/Features/Stocks/StockTable';
import RequestList from './components/Features/Requests/RequestList';
import DistributionPlan from './components/Features/Distribution/DistributionPlan';
import Landing from './components/Layout/Landing';
import Dashboard from './components/Features/Analytics/Dashboard';
import AdminLogs from './components/Features/Analytics/AdminLogs';
import AuthModal from './components/Auth/Auth';
import ScrollToTop from './components/UI/ScrollToTop';
import AppModals from './components/Features/Modals/AppModals';

function App() {
    const [currentUser, setCurrentUser] = useState(() => authService.getUser());
    const [isLandingMode, setIsLandingMode] = useState(() => localStorage.getItem('isLandingMode') !== 'false');
    const [loading, setLoading] = useState(false);
    const [plan, setPlan] = useState(null);
    const [distributionStrategy, setDistributionStrategy] = useState('fairness');

    // Керування станом усіх модалок в одному місці
    const { modals, openModal, closeModal } = useModal({
        request: false,
        stockIn: false,
        resource: false,
        auth: false,
        distribute: false
    });

    const { data, fetchData } = useFetchData(currentUser);

    useEffect(() => {
        localStorage.setItem('isLandingMode', isLandingMode);
        if (!isLandingMode && currentUser) {
            fetchData().catch(() => toast.error("Не вдалося оновити дані"));
        }
    }, [isLandingMode, currentUser]);

    const handleAuthSuccess = (userData, tokens) => {
        authService.setTokens(tokens.access, tokens.refresh);
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

    const handleDeleteRequest = async (requestId) => {
        const lid = toast.loading("Оновлення черги потреб...");
        setLoading(true);
        try {
            await api.delete(`/requests/${requestId}/`);
            toast.success("Заявку успішно видалено", { id: lid });
            setPlan(null);
            await fetchData();
        } catch (e) {
            toast.error("Не вдалося видалити заявку", { id: lid });
        } finally {
            setLoading(false);
        }
    };

    const handleDistribute = async () => {
        const lid = toast.loading("Аналіз запасів та потреб...");
        setLoading(true);
        try {
            const res = await api.post('/distribute/', { strategy: distributionStrategy });
            if (res.data.message) {
                toast(res.data.message, { id: lid, icon: <Info className="text-blue-500" /> });
                setPlan(null);
            } else {
                toast.success("План розподілу сформовано", { id: lid });
                setPlan(Array.isArray(res.data) ? { items: res.data } : res.data);
            }
            await fetchData();
        } catch (e) {
            toast.error("Помилка алгоритму розподілу", { id: lid });
        } finally {
            setLoading(false);
        }
    };

    const scrollToSection = (id) => {
        if (id === 'section-distribution') {
            openModal('distribute'); // При кліку на розподіл у боковому меню автоматично відкривається модалка налаштувань
        }
        const element = document.getElementById(id);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
                <AuthModal isOpen={modals.auth} onClose={() => closeModal('auth')} onSuccess={handleAuthSuccess} />
                <Toaster position="top-center" />
                <ScrollToTop />
            </>
        );
    }

    return (
        <div className="min-h-screen bg-slate-50 p-4 md:p-10 relative">
            <Toaster position="top-center" toastOptions={{ className: 'rounded-xl font-bold shadow-xl' }} />

            {/* Всі модалки сайту (форми + налаштування розподілу) */}
            <AppModals
                modals={modals}
                closeModal={closeModal}
                data={data}
                fetchData={fetchData}
                currentUser={currentUser}
                distributionStrategy={distributionStrategy}
                setDistributionStrategy={setDistributionStrategy}
                onDistribute={handleDistribute}
                loading={loading}
            />

            <div className="max-w-7xl mx-auto space-y-12 pb-24">
                <Header
                    onOpenForm={() => openModal('request')}
                    onOpenStockIn={currentUser?.is_admin ? () => openModal('stockIn') : null}
                    onAddResource={currentUser?.is_admin ? () => openModal('resource') : null}
                    onRefresh={fetchData}
                    onLogout={handleLogout}
                    currentUser={currentUser}
                />

                {/* Секція 1: Запаси та Заявки */}
                <div id="section-stocks" className={`grid gap-8 pt-4 ${currentUser?.is_admin ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1'}`}>
                    {currentUser?.is_admin && (
                        <StockTable stocks={data.stocks} resourcesMap={data.resourcesMap} onRefresh={fetchData} />
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

                {/* Секція 2: Аналітика */}
                {currentUser?.is_admin && (
                    <div id="section-analytics" className="space-y-8 pt-6">
                        <Dashboard stocks={data.stocks} requests={data.requests} resourcesMap={data.resourcesMap} />
                        <AdminLogs logs={data.logs || []} />
                    </div>
                )}

                {/* Секція 3: Розподіл (Кнопка виклику модалки та результати) */}
                {currentUser?.is_admin && (
                    <div id="section-distribution" className="space-y-8 pt-6 border-t border-slate-200">
                        <div className="flex justify-center py-4">
                            <button
                                onClick={() => openModal('distribute')}
                                className="px-12 py-4 bg-slate-900 text-white font-black rounded-2xl shadow-xl hover:bg-blue-600 transition-all active:scale-95 flex items-center gap-3"
                            >
                                Налаштувати та запустити розподіл
                            </button>
                        </div>

                        {plan && (
                            <DistributionPlan plan={plan} purposeMap={data.purposeMap} strategy={distributionStrategy} />
                        )}
                    </div>
                )}
            </div>

            {/* Бокове меню навігації */}
            {currentUser?.is_admin && <SidebarNav onNavigate={scrollToSection} />}

            {/* Кнопка повернення на головну */}
            <button
                onClick={() => setIsLandingMode(true)}
                className="fixed bottom-8 left-8 flex items-center gap-2 px-6 py-4 bg-white shadow-2xl rounded-2xl border border-slate-100 text-slate-500 hover:text-blue-600 transition-all hover:-translate-y-1 active:scale-95 z-40"
            >
                <Home size={20} />
                <span className="text-xs font-black uppercase tracking-widest">Головна</span>
            </button>

            <ScrollToTop />
        </div>
    );
}

export default App;