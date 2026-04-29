import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Toaster, toast } from 'react-hot-toast';
import {
  Home,
  ShieldAlert,
  Stethoscope,
  Flame,
  Footprints,
  GraduationCap,
  User,
  FileText,
  ArrowDownCircle,
  PackagePlus,
  RefreshCw,
  ClipboardList,
  Info,
  AlertCircle,
  CheckCircle2,
  ShieldCheck
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

  useEffect(() => {
    localStorage.setItem('isLandingMode', isLandingMode);
  }, [isLandingMode]);

  const fetchData = useCallback(async () => {
    try {
      const [stockRes, reqRes, resRes, userRes, whRes] = await Promise.all([
        axios.get(`${API_URL}/stocks/`),
        axios.get(`${API_URL}/requests/`),
        axios.get(`${API_URL}/resources/`),
        axios.get(`${API_URL}/users/`),
        axios.get(`${API_URL}/warehouses/`)
      ]);
      const resMap = {};
      resRes.data.forEach(r => { resMap[r.id] = r; });
      setResourcesMap(resMap);
      setResourcesList(resRes.data);
      setUsersList(userRes.data);
      setWarehouses(whRes.data);
      setStocks(stockRes.data);
      setRequests(reqRes.data);
      if (userRes.data.length > 0) setSelectedUserId(prev => prev || userRes.data[0].id);
    } catch (error) {
      toast.error("Помилка з'єднання з API", { icon: <AlertCircle size={20} className="text-red-500" /> });
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleAuthSuccess = () => {
    setIsLandingMode(false);
    toast.success("Доступ дозволено", { icon: <ShieldCheck size={20} className="text-blue-500" /> });
  };

  const handleSubmitRequest = async () => {
    if (!selectedUserId) return toast.error("Оберіть заявника");
    setLoading(true);
    try {
      await Promise.all(formRows.map(row => {
        if (!row.resource || !row.quantity) return Promise.resolve();
        return axios.post(`${API_URL}/requests/`, {
          user: parseInt(selectedUserId),
          resource: parseInt(row.resource),
          quantity_requested: parseFloat(row.quantity),
          purpose: row.purpose,
          status: 'new'
        });
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
        toast(response.data.message, {
          id: loadId,
          icon: <Info size={20} className="text-blue-500" />,
          style: { border: '1px solid #dbeafe', color: '#1e40af' }
        });
        setPlan(null);
      } else {
        toast.success("План успішно сформовано", {
          id: loadId,
          icon: <GraduationCap size={20} className="text-indigo-500" />
        });
        setPlan(response.data);
      }
      fetchData();
    } catch (error) {
      toast.error("Помилка алгоритму", { id: loadId });
    } finally { setLoading(false); }
  };

  const totalItemsAmount = stocks.reduce((sum, item) => sum + Number(item.amount), 0);

  if (isLandingMode) {
    return (
      <>
        <Landing
          onEnter={() => setIsAuthOpen(true)}
          stats={{ stocks: totalItemsAmount, requests: requests.length, warehouses: warehouses.length }}
        />
        <AuthModal
          isOpen={isAuthOpen}
          onClose={() => setIsAuthOpen(false)}
          onSuccess={handleAuthSuccess}
        />
        <Toaster position="top-center" />
      </>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-800 p-4 md:p-10 relative overflow-x-hidden">
      <Toaster position="top-center" toastOptions={{ duration: 3000, className: 'rounded-xl font-bold text-sm shadow-xl' }} />

      <Modal isOpen={isFormOpen} onClose={() => setIsFormOpen(false)} title="Нова заявка" icon={ClipboardList}>
        <RequestForm usersList={usersList} resourcesList={resourcesList} selectedUserId={selectedUserId} setSelectedUserId={setSelectedUserId} formRows={formRows} handleFormChange={(idx, f, v) => { const newRows = [...formRows]; newRows[idx][f] = v; setFormRows(newRows); }} addFormRow={() => setFormRows([...formRows, { resource: '', quantity: '', purpose: 'personal' }])} removeFormRow={(idx) => setFormRows(formRows.filter((_, i) => i !== idx))} handleSubmitRequest={handleSubmitRequest} loading={loading} onClose={() => setIsFormOpen(false)} />
      </Modal>

      <Modal isOpen={isStockInOpen} onClose={() => setIsStockInOpen(false)} title="Поповнення складів" icon={ArrowDownCircle} maxWidth="max-w-3xl">
        <StockInForm warehouses={warehouses} resources={resourcesList} onSubmit={handleAddStock} loading={loading} onClose={() => setIsStockInOpen(false)} />
      </Modal>

      <Modal isOpen={isAddResourceOpen} onClose={() => setIsAddResourceOpen(false)} title="Новий тип ресурсу" icon={PackagePlus} maxWidth="max-w-lg">
        <AddResourceForm onResourceAdded={(newData) => { fetchData(); setIsAddResourceOpen(false); toast.success(`Ресурс додано`, { icon: <PackagePlus className="text-indigo-500" size={20} /> }); }} onClose={() => setIsAddResourceOpen(false)} />
      </Modal>

      <div className="max-w-7xl mx-auto space-y-8 pb-24">
        <Header onOpenForm={() => setIsFormOpen(true)} onOpenStockIn={() => setIsStockInOpen(true)} onAddResource={() => setIsAddResourceOpen(true)} onRefresh={fetchData} />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <StockTable stocks={stocks} resourcesMap={resourcesMap} onRefresh={fetchData} />
          <RequestList requests={requests} requestTab={requestTab} setRequestTab={setRequestTab} purposeMap={PURPOSE_MAP} />
        </div>

        <div className="flex flex-col items-center gap-4 py-8">
          <button onClick={handleDistribute} disabled={loading} className={`px-16 py-5 rounded-2xl text-xl font-black text-white shadow-2xl transition-all active:scale-95 ${loading ? 'bg-slate-400' : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:scale-105'}`}>
            {loading ? "Аналіз..." : "ВИКОНАТИ РОЗПОДІЛ"}
          </button>
        </div>

        {plan && <DistributionPlan plan={plan} purposeMap={PURPOSE_MAP} />}
      </div>

      <button onClick={() => setIsLandingMode(true)} className="fixed bottom-8 left-8 z-[60] flex items-center gap-2 px-6 py-4 bg-white shadow-2xl rounded-2xl border border-slate-100 text-slate-500 hover:text-blue-600 transition-all hover:scale-105 active:scale-95">
        <Home size={20} /> <span className="text-xs font-black uppercase tracking-widest">Головна</span>
      </button>
    </div>
  );
}

export default App;