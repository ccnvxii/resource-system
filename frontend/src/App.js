import React, { useState, useEffect, lazy, Suspense } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import { Home, Info } from './components/UI/icons';

// Сервіси та кастомні хуки
import api from './services/api';
import authService from './services/authService';
import { useModal } from './hooks/useModal';
import { useFetchData } from './hooks/useFetchData';

// Компоненти (базові/легкі та стартова сторінка для виключення waterfall на мобільних)
import Header from './components/Layout/Header';
import SidebarNav from './components/Layout/SidebarNav';
import RequestList from './components/Features/Requests/RequestList';
import ScrollToTop from './components/UI/ScrollToTop';
import Landing from './components/Layout/Landing';

// Ліниве завантаження важких внутрішніх модулів (завантажуються тільки після входу)
const Dashboard = lazy(() => import('./components/Features/Analytics/Dashboard'));
const AdminLogs = lazy(() => import('./components/Features/Analytics/AdminLogs'));
const StockTable = lazy(() => import('./components/Features/Stocks/StockTable'));
const DistributionPlan = lazy(() => import('./components/Features/Distribution/DistributionPlan'));
const AppModals = lazy(() => import('./components/Features/Modals/AppModals'));
const AuthModal = lazy(() => import('./components/Auth/Auth'));

function App() {
    const [currentUser, setCurrentUser] = useState(() => authService.getUser());
    const [isLandingMode, setIsLandingMode] = useState(() => localStorage.getItem('isLandingMode') !== 'false');
    const [loading, setLoading] = useState(false);
    const [plan, setPlan] = useState(null);
    const [distributionStrategy, setDistributionStrategy] = useState('hybrid');

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
                {modals.auth && (
                    <Suspense fallback={null}>
                        <AuthModal isOpen={modals.auth} onClose={() => closeModal('auth')} onSuccess={handleAuthSuccess} />
                    </Suspense>
                )}
                <Toaster position="top-center" />
                <ScrollToTop />
            </>
        );
    }

    const hasOpenModal = Object.values(modals).some(Boolean);

    return (
        <Suspense fallback={<div className="min-h-screen bg-slate-50 flex items-center justify-center"><div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" /></div>}>
            <div className="min-h-screen bg-slate-50 p-4 md:p-10 relative">
            <Toaster position="top-center" toastOptions={{ className: 'rounded-xl font-bold shadow-xl' }} />

            {/* Всі модалки сайту (завантажуються ТІЛЬКИ коли модалка відкрита) */}
            {hasOpenModal && (
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
            )}

            {/* Семантичний тег main для покращення Accessibility (виправлення зауваження Lighthouse) */}
            <main className="max-w-7xl mx-auto space-y-12 pb-24">
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
            </main>

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
        </Suspense>
    );
}

export default App;