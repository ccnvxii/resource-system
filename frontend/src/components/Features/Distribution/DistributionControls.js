import React from 'react';
import { Scale, Zap, GitFork } from 'lucide-react';

const DistributionControls = ({ strategy, setStrategy, onDistribute, loading }) => {
    return (
        <div className="flex flex-col items-center py-4 space-y-6">
            {/* Перемикач режимів */}
            <div className="flex bg-slate-200 p-1.5 rounded-2xl shadow-inner border border-slate-300">
                <button
                    onClick={() => setStrategy('fairness')}
                    className={`flex items-center gap-2 px-5 py-3 rounded-xl font-bold text-sm transition-all duration-300 ${
                        strategy === 'fairness' 
                        ? 'bg-white text-blue-600 shadow-md ring-1 ring-black/5' 
                        : 'text-slate-500 hover:text-slate-700'
                    }`}
                >
                    <Scale size={18} />
                    Справедливість
                </button>

                <button
                    onClick={() => setStrategy('hybrid')}
                    className={`flex items-center gap-2 px-5 py-3 rounded-xl font-bold text-sm transition-all duration-300 ${
                        strategy === 'hybrid' 
                        ? 'bg-white text-purple-600 shadow-md ring-1 ring-black/5' 
                        : 'text-slate-500 hover:text-slate-700'
                    }`}
                >
                    <GitFork size={18} />
                    Гібридний (Auto)
                </button>

                <button
                    onClick={() => setStrategy('triage')}
                    className={`flex items-center gap-2 px-5 py-3 rounded-xl font-bold text-sm transition-all duration-300 ${
                        strategy === 'triage' 
                        ? 'bg-white text-red-600 shadow-md ring-1 ring-black/5' 
                        : 'text-slate-500 hover:text-slate-700'
                    }`}
                >
                    <Zap size={18} />
                    Жорсткий Тріаж
                </button>
            </div>

            {/* Кнопка запуску */}
            <button
                onClick={onDistribute}
                disabled={loading}
                className={`px-16 py-5 rounded-2xl text-xl font-black text-white shadow-2xl transition-all ${
                    loading ? 'bg-slate-400 cursor-not-allowed' 
                    : strategy === 'triage' ? 'bg-red-600 hover:bg-red-700 hover:shadow-red-500/30 hover:scale-105 active:scale-95' 
                    : strategy === 'hybrid' ? 'bg-purple-600 hover:bg-purple-700 hover:shadow-purple-500/30 hover:scale-105 active:scale-95'
                    : 'bg-blue-600 hover:bg-blue-700 hover:shadow-blue-500/30 hover:scale-105 active:scale-95'
                }`}
            >
                {loading ? "ОБРОБКА..." : "ВИКОНАТИ РОЗПОДІЛ"}
            </button>
        </div>
    );
};

export default DistributionControls;