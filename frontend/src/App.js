import React, { useState, useEffect, useCallback } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import { Home, ClipboardList, ArrowDownCircle, PackagePlus, Info, CheckCircle2 } from 'lucide-react';

import api from './services/api';
import authService from './services/authService';
import { PURPOSE_MAP } from './type/purposes';

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
  const [stocks, setStocks] = useState([]);
  const [requests, setRequests] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [resourcesList, setResourcesList] = useState([]);
  const [resourcesMap, setResourcesMap] = useState({});
  const [usersList, setUsersList] = useState([]);
  const [plan, setPlan] = useState(null);

  // 3NF Дані
  const [units, setUnits] = useState([]);
  const [purposes, setPurposes] = useState([]);
  const [purposeMap, setPurposeMap] = useState({});

  const [isLandingMode, setIsLandingMode] = useState(() => localStorage.getItem('isLandingMode') !== 'false');
  const [loading, setLoading] = useState(false);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isStockInOpen, setIsStockInOpen] = useState(false);
  const [isAddResourceOpen, setIsAddResourceOpen] = useState(false);
  const [requestTab, setRequestTab] = useState('active');
  const [selectedUserId, setSelectedUserId] = useState('');
  const [formRows, setFormRows] = useState([{ resource: '', quantity: '', purpose: '' }]);
  const [isAuthOpen, setIsAuthOpen] = useState(false);

  const [currentUser, setCurrentUser] = useState(() => authService.getUser());

  const fetchData = useCallback(async () => {
    try {
      const baseRequests = [
        api.get('/stocks/'), api.get('/requests/'), api.get('/resources/'),
        api.get('/warehouses/'), api.get('/units/'), api.get('/purposes/')
      ];

      if (currentUser?.is_admin) baseRequests.push(api.get('/users/'));

      const results = await Promise.all(baseRequests);
      const [stockRes, reqRes, resRes, whRes, unitRes, purpRes, userRes] = results;

      const resMap = {};
      resRes.data.forEach(r => { resMap[r.id] = r; });

      const pMap = {};
      purpRes.data.forEach(p => {
        const config = PURPOSE_MAP[p.code] || PURPOSE_MAP['default'];
        pMap[p.id] = {
          label: p.name,
          icon: config.icon,
          color: config.color
        };
      });

      setResourcesMap(resMap);
      setResourcesList(resRes.data);
      setWarehouses(whRes.data);
      setStocks(stockRes.data);
      setRequests(reqRes.data);
      setUnits(unitRes.data);
      setPurposes(purpRes.data);
      setPurposeMap(pMap);

      if (userRes) {
        setUsersList(userRes.data);
        if (currentUser.is_admin && userRes.data.length > 0) {
          setSelectedUserId(prev => prev || userRes.data[0].id.toString());
        }
      }
    } catch (error) { console.error("Fetch error", error); }
  }, [currentUser]);

  useEffect(() => {
    localStorage.setItem('isLandingMode', isLandingMode);
    if (!isLandingMode && currentUser) fetchData();
  }, [fetchData, isLandingMode, currentUser]);

  const handleAuthSuccess = (userData, tokens) => {
    authService.setTokens(tokens.access, tokens.refresh);
    const isAdmin = userData.is_admin || userData.email === 'admin@resq.ua';
    authService.setUser({ ...userData, is_admin: isAdmin });
    setCurrentUser({ ...userData, is_admin: isAdmin });
    setIsLandingMode(false);
    setIsAuthOpen(false);
  };

  const handleLogout = () => {
    authService.clearAuth();
    setCurrentUser(null);
    setIsLandingMode(true);
    setPlan(null);
  };

  const handleSubmitRequest = async () => {
    if (formRows.some(r => !r.resource || !r.quantity || !r.purpose)) {
      return toast.error("Заповніть всі поля");
    }
    setLoading(true);
    try {
      await Promise.all(formRows.map(row => {
        const payload = {
          resource: parseInt(row.resource),
          quantity_requested: parseFloat(row.quantity),
          purpose: parseInt(row.purpose) // ID з RequestPurpose
        };
        if (selectedUserId) payload.user = parseInt(selectedUserId);
        return api.post('/requests/', payload);
      }));
      toast.success("Заявки створено");
      setIsFormOpen(false);
      setFormRows([{ resource: '', quantity: '', purpose: '' }]);
      fetchData();
    } catch (e) {} finally { setLoading(false); }
  };

  const handleDistribute = async () => {
    const lid = toast.loading("Розрахунок...");
    setLoading(true);
    try {
      const res = await api.post('/distribute/');
      if (res.data.message) {
        toast(res.data.message, { id: lid, icon: <Info /> });
      } else {
        toast.success("План готовий", { id: lid });
        setPlan(res.data);
      }
      fetchData();
    } catch (e) { toast.dismiss(lid); } finally { setLoading(false); }
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
    <div className="min-h-screen bg-slate-50 p-4 md:p-10 relative">
      <Toaster position="top-center" toastOptions={{ className: 'rounded-xl font-bold shadow-xl' }} />

      <Modal isOpen={isFormOpen} onClose={() => setIsFormOpen(false)} title="Нова заявка" icon={ClipboardList}>
        <RequestForm
          usersList={usersList} resourcesList={resourcesList} purposes={purposes}
          selectedUserId={selectedUserId} setSelectedUserId={setSelectedUserId}
          formRows={formRows} handleFormChange={(idx, f, v) => { const n = [...formRows]; n[idx][f] = v; setFormRows(n); }}
          addFormRow={() => setFormRows([...formRows, { resource: '', quantity: '', purpose: '' }])}
          removeFormRow={(idx) => setFormRows(formRows.filter((_, i) => i !== idx))}
          handleSubmitRequest={handleSubmitRequest} loading={loading} onClose={() => setIsFormOpen(false)} currentUser={currentUser}
        />
      </Modal>

      <Modal isOpen={isStockInOpen} onClose={() => setIsStockInOpen(false)} title="Поповнення" icon={ArrowDownCircle} maxWidth="max-w-3xl">
        <StockInForm warehouses={warehouses} resources={resourcesList} onSubmit={fetchData} loading={loading} onClose={() => setIsStockInOpen(false)} />
      </Modal>

      <Modal isOpen={isAddResourceOpen} onClose={() => setIsAddResourceOpen(false)} title="Новий ресурс" icon={PackagePlus} maxWidth="max-w-lg">
        <AddResourceForm units={units} onResourceAdded={() => { fetchData(); setIsAddResourceOpen(false); }} onClose={() => setIsAddResourceOpen(false)} />
      </Modal>

      <div className="max-w-7xl mx-auto space-y-8 pb-24">
        <Header onOpenForm={() => setIsFormOpen(true)} onOpenStockIn={() => setIsStockInOpen(true)} onAddResource={() => setIsAddResourceOpen(true)} onRefresh={fetchData} onLogout={handleLogout} currentUser={currentUser} />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <StockTable stocks={stocks} resourcesMap={resourcesMap} onRefresh={fetchData} />
          <RequestList requests={requests} requestTab={requestTab} setRequestTab={setRequestTab} purposeMap={purposeMap} />
        </div>

        {currentUser?.is_admin && (
          <div className="flex justify-center py-8">
            <button onClick={handleDistribute} disabled={loading} className={`px-16 py-5 rounded-2xl text-xl font-black text-white shadow-2xl transition-all ${loading ? 'bg-slate-400' : 'bg-blue-600 hover:scale-105 active:scale-95'}`}>
              {loading ? "АНАЛІЗ..." : "ВИКОНАТИ РОЗПОДІЛ"}
            </button>
          </div>
        )}

        {plan && <DistributionPlan plan={plan} purposeMap={purposeMap} />}
      </div>

      <button onClick={() => setIsLandingMode(true)} className="fixed bottom-8 left-8 flex items-center gap-2 px-6 py-4 bg-white shadow-2xl rounded-2xl border border-slate-100 text-slate-500 hover:text-blue-600 transition-all hover:scale-105 active:scale-95">
        <Home size={20} /> <span className="text-xs font-black uppercase">Головна</span>
      </button>
    </div>
  );
}

export default App;