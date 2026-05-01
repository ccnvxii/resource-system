import React from 'react';
import {
    PlusCircle,
    RefreshCw,
    ClipboardList,
    PackagePlus,
    ShieldCheck,
    User,
    LogOut
} from 'lucide-react';

const Header = ({onOpenForm, onOpenStockIn, onRefresh, onAddResource, currentUser, onLogout}) => {
    const btnBase = "flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm transition-all active:scale-95 border-2 shadow-sm";

    // Визначаємо, чи є користувач адміном
    const isAdmin = currentUser?.is_admin || currentUser?.username === 'admin';

    return (
        <header
            className="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <div className="flex items-center gap-4">
                <div
                    className="hidden sm:flex bg-white p-1 rounded-xl shadow-sm border-2 border-blue-100 items-center justify-center overflow-hidden w-12 h-12 shrink-0">
                    <img
                        src={process.env.PUBLIC_URL + '/logo.ico'}
                        alt="ResQ Logo"
                        className="w-full h-full object-contain"
                    />
                </div>

                <div>
                    <div className="flex items-center gap-3">
                        <h1 className="text-3xl font-extrabold text-slate-800 tracking-tight">
                            <span className="text-blue-600">ResQ</span> System
                        </h1>

                        {/* ПЛАШКА СТАТУСУ */}
                        {isAdmin ? (
                            <div
                                className="flex items-center gap-1.5 px-3 py-1 bg-blue-600 text-white rounded-full shadow-lg shadow-blue-100">
                                <ShieldCheck size={12} className="fill-white/20"/>
                                <span
                                    className="text-[10px] font-black uppercase tracking-wider text-white">Адміністратор</span>
                            </div>
                        ) : (
                            <div
                                className="flex items-center gap-1.5 px-3 py-1 bg-slate-100 text-slate-600 rounded-full border border-slate-200">
                                <User size={12}/>
                                <span className="text-[10px] font-black uppercase tracking-wider">Волонтер</span>
                            </div>
                        )}
                    </div>
                    <p className="text-slate-500 mt-0.5 font-medium text-xs md:text-sm italic">
                        {currentUser?.username || 'Користувач'}: {isAdmin ? 'Повний доступ' : 'Обмежений доступ'}
                    </p>
                </div>
            </div>

            <div className="flex flex-wrap justify-center gap-3 mt-6 md:mt-0">
                {/* Поставка — зазвичай тільки для адміна або складу */}
                {isAdmin && (
                    <button
                        onClick={onOpenStockIn}
                        className={`${btnBase} bg-emerald-50 text-emerald-700 border-emerald-100 hover:bg-emerald-100 hover:border-emerald-200`}
                    >
                        <PlusCircle size={18}/>
                        Поставка
                    </button>
                )}

                {/* Заявка — відкрита для ВСІХ авторизованих користувачів */}
                <button
                    onClick={onOpenForm}
                    className={`${btnBase} bg-blue-50 text-blue-700 border-blue-100 hover:bg-blue-100 hover:border-blue-200`}
                >
                    <ClipboardList size={18}/>
                    Заявка
                </button>

                {/* Ресурси — тільки для адміна */}
                {isAdmin && (
                    <button
                        onClick={onAddResource}
                        className={`${btnBase} bg-indigo-50 text-indigo-700 border-indigo-100 hover:bg-indigo-100 hover:border-indigo-200`}
                    >
                        <PackagePlus size={18}/>
                        Ресурси
                    </button>
                )}

                <div className="flex gap-2 ml-2 pl-4 border-l-2 border-slate-100">
                    <button
                        onClick={onRefresh}
                        className="p-2.5 bg-slate-50 text-slate-500 rounded-xl border-2 border-slate-100 hover:bg-slate-100 hover:border-slate-200 transition-all active:scale-95 shadow-sm"
                        title="Оновити дані"
                    >
                        <RefreshCw size={20}/>
                    </button>

                    <button
                        onClick={onLogout}
                        className="p-2.5 bg-red-50 text-red-500 rounded-xl border-2 border-red-100 hover:bg-red-100 hover:border-red-200 transition-all active:scale-95 shadow-sm"
                        title="Вийти з аккаунту"
                    >
                        <LogOut size={20}/>
                    </button>
                </div>
            </div>
        </header>
    );
};

export default Header;