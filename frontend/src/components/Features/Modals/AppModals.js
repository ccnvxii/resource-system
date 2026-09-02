import React from 'react';
import { ClipboardList, ArrowDownCircle, PackagePlus, Scale, Zap, GitFork } from 'lucide-react';
import Modal from '../../UI/Modal';
import RequestForm from '../Requests/RequestForm';
import StockInForm from '../Stocks/StockInForm';
import AddResourceForm from '../Stocks/AddResourceForm';

const AppModals = ({ modals, closeModal, data, fetchData, currentUser, distributionStrategy, setDistributionStrategy, onDistribute, loading }) => {
    return (
        <>
            {/* Модалка створення заявки */}
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

            {/* Модалка поповнення складу */}
            <Modal isOpen={modals.stockIn} onClose={() => closeModal('stockIn')} title="Поповнення складів" icon={ArrowDownCircle} maxWidth="max-w-3xl">
                <StockInForm
                    warehouses={data.warehouses}
                    resources={data.resourcesList}
                    onSubmit={fetchData}
                    onClose={() => closeModal('stockIn')}
                />
            </Modal>

            {/* Модалка нового ресурсу */}
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

            {/* Модалка налаштування та запуску алгоритму розподілу */}
            <Modal
                isOpen={modals.distribute}
                onClose={() => closeModal('distribute')}
                title="Параметри оптимізації розподілу"
                subtitle="Алгоритми прийняття рішень"
                icon={GitFork}
                maxWidth="max-w-xl"
            >
                <div className="flex flex-col items-center py-4 space-y-6">
                    {/* ПЕРЕМИКАЧ НА 3 КНОПКИ */}
                    <div className="flex flex-col sm:flex-row bg-slate-200 p-1.5 rounded-2xl shadow-inner border border-slate-300 w-full gap-2">
                        <button
                            onClick={() => setDistributionStrategy('fairness')}
                            className={`flex items-center justify-center gap-2 px-3 py-3 rounded-xl font-bold text-sm transition-all duration-300 flex-1 ${
                                distributionStrategy === 'fairness' 
                                ? 'bg-white text-blue-600 shadow-md ring-1 ring-black/5' 
                                : 'text-slate-500 hover:text-slate-700'
                            }`}
                        >
                            <Scale size={18} />
                            Fairness
                        </button>

                        <button
                            onClick={() => setDistributionStrategy('hybrid')}
                            className={`flex items-center justify-center gap-2 px-3 py-3 rounded-xl font-bold text-sm transition-all duration-300 flex-1 ${
                                distributionStrategy === 'hybrid' 
                                ? 'bg-white text-purple-600 shadow-md ring-1 ring-black/5' 
                                : 'text-slate-500 hover:text-slate-700'
                            }`}
                        >
                            <GitFork size={18} />
                            Гібридний (Auto)
                        </button>

                        <button
                            onClick={() => setDistributionStrategy('triage')}
                            className={`flex items-center justify-center gap-2 px-3 py-3 rounded-xl font-bold text-sm transition-all duration-300 flex-1 ${
                                distributionStrategy === 'triage' 
                                ? 'bg-white text-red-600 shadow-md ring-1 ring-black/5' 
                                : 'text-slate-500 hover:text-slate-700'
                            }`}
                        >
                            <Zap size={18} />
                            Тріаж
                        </button>
                    </div>

                    {/* ОПИС РЕЖИМІВ */}
                    <div className="text-center px-2 min-h-[40px] flex items-center justify-center">
                        <p className="text-xs text-slate-500 font-medium leading-relaxed">
                            {distributionStrategy === 'fairness' && '⚖️ Лексикографічний розподіл (Симплекс) забезпечує рівномірне та справедливе задоволення потреб усіх заявників.'}
                            {distributionStrategy === 'hybrid' && '🧬 Розумна маршрутизація: стратегічні вантажі йдуть у Тріаж, а товари життєзабезпечення — у Справедливість.'}
                            {distributionStrategy === 'triage' && '⚡ Режим екстреного тріажу (Жадібний) спрямовує всі ресурси на 100% закриття заявок з найвищим пріоритетом.'}
                        </p>
                    </div>

                    <button
                        onClick={() => {
                            onDistribute();
                            closeModal('distribute');
                        }}
                        disabled={loading}
                        className={`w-full py-5 rounded-2xl text-lg font-black text-white shadow-2xl transition-all ${
                            loading ? 'bg-slate-400 cursor-not-allowed' 
                            : distributionStrategy === 'triage' ? 'bg-red-600 hover:bg-red-700 hover:shadow-red-500/30 active:scale-95' 
                            : distributionStrategy === 'hybrid' ? 'bg-purple-600 hover:bg-purple-700 hover:shadow-purple-500/30 active:scale-95'
                            : 'bg-blue-600 hover:bg-blue-700 hover:shadow-blue-500/30 active:scale-95'
                        }`}
                    >
                        {loading ? "ОБРОБКА..." : "ЗАПУСТИТИ РОЗПОДІЛ"}
                    </button>
                </div>
            </Modal>
        </>
    );
};

export default AppModals;