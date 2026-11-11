import React, { useState, useEffect, lazy, Suspense } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import { Home, Info, PackageSearch, ListChecks } from './components/UI/icons';

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
    const [activeAdminTab, setActiveAdminTab] = useState('stocks');

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
        toast.dismiss();
        toast.success(`Вітаємо, ${userData.first_name || 'користувачу'}!`, { id: 'auth-success-toast' });
    };

    const handleLogout = () => {
        authService.clearAuth();
        setCurrentUser(null);
        setIsLandingMode(true);
        setPlan(null);
        toast.dismiss();
        toast.success("Вихід виконано", { id: 'logout-toast' });
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

    const hasOpenModal = Object.values(modals).some(Boolean);

    return (
        <>
            <Toaster position="top-center" toastOptions={{ className: 'rounded-xl font-bold shadow-xl' }} />
            {isLandingMode ? (
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
                    <ScrollToTop />
                </>
            ) : (
                <Suspense fallback={<div className="min-h-screen bg-slate-50 flex items-center justify-center"><div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" /></div>}>
                    <div className="min-h-screen bg-slate-50 p-3 sm:p-6 md:p-10 relative">
                    {/* Всі модалки сайту (завантажуються ТІЛЬКИ коли модалка відкрита) */}
            {hasOpenModal && (
                <Suspense fallback={null}>
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
                </Suspense>
            )}

            {/* Семантичний тег main для покращення Accessibility (виправлення зауваження Lighthouse) */}
            <main className="max-w-7xl mx-auto space-y-4 sm:space-y-8 md:space-y-10 pb-16 sm:pb-24">
                <Header
                    onOpenForm={() => openModal('request')}
                    onOpenStockIn={currentUser?.is_admin ? () => openModal('stockIn') : null}
                    onAddResource={currentUser?.is_admin ? () => openModal('resource') : null}
                    onLogout={handleLogout}
                    currentUser={currentUser}
                />

                {/* Секція 1: Запаси та Заявки */}
                <div id="section-stocks">
                    {/* Мобільний тач-перемикач тільки для телефонів (ховається на md+) */}
                    {currentUser?.is_admin && (
                        <div className="md:hidden flex bg-slate-200/80 p-1 rounded-2xl mb-3 shadow-inner">
                            <button
                                onClick={() => setActiveAdminTab('stocks')}
                                className={`flex-1 py-2 rounded-xl text-xs font-black uppercase tracking-wider transition-all flex items-center justify-center gap-1.5 ${
                                    activeAdminTab === 'stocks'
                                        ? 'bg-white text-blue-600 shadow-sm'
                                        : 'text-slate-600 hover:text-slate-900'
                                }`}
                            >
                                <PackageSearch size={15} />
                                <span>Запаси ({data.stocks.length})</span>
                            </button>
                            <button
                                onClick={() => setActiveAdminTab('requests')}
                                className={`flex-1 py-2 rounded-xl text-xs font-black uppercase tracking-wider transition-all flex items-center justify-center gap-1.5 ${
                                    activeAdminTab === 'requests'
                                        ? 'bg-white text-blue-600 shadow-sm'
                                        : 'text-slate-600 hover:text-slate-900'
                                }`}
                            >
                                <ListChecks size={15} />
                                <span>Заявки ({data.requests.length})</span>
                            </button>
                        </div>
                    )}

                    <div className={`grid gap-4 sm:gap-6 md:gap-8 ${currentUser?.is_admin ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'}`}>
                        {currentUser?.is_admin && (
                            <div className={`w-full ${activeAdminTab === 'stocks' ? 'block' : 'hidden md:block'}`}>
                                <Suspense fallback={null}><StockTable stocks={data.stocks} resourcesMap={data.resourcesMap} onRefresh={fetchData} /></Suspense>
                            </div>
                        )}
                        <div className={`w-full ${currentUser?.is_admin && activeAdminTab !== 'requests' ? 'hidden md:block' : 'block'}`}>
                            <RequestList
                                requests={data.requests}
                                purposeMap={data.purposeMap}
                                onRefresh={fetchData}
                                currentUser={currentUser}
                                onDeleteRequest={handleDeleteRequest}
                            />
                        </div>
                    </div>
                </div>

                {/* Секція 2: Аналітика */}
                {currentUser?.is_admin && (
                    <div id="section-analytics" className="space-y-4 sm:space-y-6">
                        <Suspense fallback={null}><Dashboard stocks={data.stocks} requests={data.requests} resourcesMap={data.resourcesMap} /></Suspense>
                        <Suspense fallback={null}><AdminLogs logs={data.logs || []} /></Suspense>
                    </div>
                )}

                {/* Секція 3: Розподіл (Кнопка виклику модалки та результати) */}
                {currentUser?.is_admin && (
                    <div id="section-distribution" className="space-y-4 sm:space-y-6">
                        <div className="flex justify-center py-2 sm:py-3">
                            <button
                                onClick={() => openModal('distribute')}
                                className="w-full sm:w-auto px-8 sm:px-12 py-3.5 sm:py-4 bg-slate-900 text-white font-black rounded-2xl shadow-xl hover:bg-blue-600 transition-all active:scale-95 flex items-center justify-center gap-3 text-sm sm:text-base"
                            >
                                Налаштувати та запустити розподіл
                            </button>
                        </div>

                        {plan && (
                            <Suspense fallback={null}><DistributionPlan plan={plan} purposeMap={data.purposeMap} strategy={distributionStrategy} /></Suspense>
                        )}
                    </div>
                )}
            </main>

            {/* Бокове меню навігації */}
            {currentUser?.is_admin && <SidebarNav onNavigate={scrollToSection} />}

            {/* Кнопка повернення на головну */}
            <button
                onClick={() => setIsLandingMode(true)}
                aria-label="На головну"
                className="fixed bottom-6 left-6 w-12 h-12 sm:w-auto sm:h-auto sm:bottom-8 sm:left-8 flex items-center justify-center gap-2 sm:px-6 sm:py-4 bg-blue-600 shadow-xl shadow-blue-600/40 rounded-2xl border-2 border-blue-500 text-white hover:bg-blue-700 transition-all hover:-translate-y-1 active:scale-95 z-40"
            >
                <Home size={20} />
                <span className="text-xs font-black uppercase tracking-widest hidden sm:inline">Головна</span>
            </button>

            <ScrollToTop />
            </div>
        </Suspense>
        )}
        </>
    );
}

export default App;