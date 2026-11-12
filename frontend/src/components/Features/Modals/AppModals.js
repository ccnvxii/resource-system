import React from 'react';
import { ClipboardList, ArrowDownCircle, PackagePlus, Scale, Zap, GitFork, Play, Sliders } from '../../UI/icons';
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
                icon={Sliders}
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
                            Справедливий
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
                            Жорсткий пріоритет
                        </button>
                    </div>

                    {/* ОПИС РЕЖИМІВ З ІКОНКАМИ LUCIDE-REACT */}
                    <div className="w-full bg-slate-50 border border-slate-200/80 rounded-2xl p-4 min-h-[64px] flex items-center justify-center text-left">
                        {distributionStrategy === 'fairness' && (
                            <div className="flex items-center gap-3 animate-in fade-in duration-200">
                                <div className="p-2 bg-blue-100 text-blue-600 rounded-xl shrink-0">
                                    <Scale size={20} />
                                </div>
                                <p className="text-xs text-slate-600 font-medium leading-relaxed">
                                    <strong className="text-slate-800">Справедливий розподіл (Fairness):</strong> лексикографічна оптимізація (симплекс-метод) забезпечує рівномірне та справедливе задоволення потреб усіх заявників.
                                </p>
                            </div>
                        )}
                        {distributionStrategy === 'hybrid' && (
                            <div className="flex items-center gap-3 animate-in fade-in duration-200">
                                <div className="p-2 bg-purple-100 text-purple-600 rounded-xl shrink-0">
                                    <GitFork size={20} />
                                </div>
                                <p className="text-xs text-slate-600 font-medium leading-relaxed">
                                    <strong className="text-slate-800">Розумна маршрутизація:</strong> стратегічні ресурси розподіляються за жорстким пріоритетом (Тріаж), решта - за справедливим розподілом.
                                </p>
                            </div>
                        )}
                        {distributionStrategy === 'triage' && (
                            <div className="flex items-center gap-3 animate-in fade-in duration-200">
                                <div className="p-2 bg-red-100 text-red-600 rounded-xl shrink-0">
                                    <Zap size={20} />
                                </div>
                                <p className="text-xs text-slate-600 font-medium leading-relaxed">
                                    <strong className="text-slate-800">Жорсткий розподіл за пріоритетом (Тріаж):</strong> усі ресурси спершу повністю закривають заявки з найвищим пріоритетом. У гібридному режимі діє лише для стратегічних ресурсів.
                                </p>
                            </div>
                        )}
                    </div>

                    <button
                        onClick={() => {
                            onDistribute();
                            closeModal('distribute');
                        }}
                        disabled={loading}
                        className={`w-full py-4 sm:py-5 rounded-2xl text-base sm:text-lg font-black text-white shadow-2xl transition-all flex items-center justify-center gap-3 ${
                            loading ? 'bg-slate-400 cursor-not-allowed' 
                            : distributionStrategy === 'triage' ? 'bg-red-600 hover:bg-red-700 hover:shadow-red-500/30 active:scale-95' 
                            : distributionStrategy === 'hybrid' ? 'bg-purple-600 hover:bg-purple-700 hover:shadow-purple-500/30 active:scale-95'
                            : 'bg-blue-600 hover:bg-blue-700 hover:shadow-blue-500/30 active:scale-95'
                        }`}
                    >
                        <Play size={20} className="fill-current" />
                        <span>{loading ? "ОБРОБКА..." : "ЗАПУСТИТИ РОЗПОДІЛ"}</span>
                    </button>
                </div>
            </Modal>
        </>
    );
};

export default AppModals;