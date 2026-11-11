import React from 'react';
import {
    PlusCircle,
    ClipboardList,
    ShieldCheck,
    User,
    LogOut
} from '../UI/icons';

const Header = ({onOpenForm, onOpenStockIn, onAddResource, currentUser, onLogout}) => {
    // Визначаємо, чи є користувач адміном
    const isAdmin = currentUser?.is_admin || currentUser?.username === 'admin';

    return (
        <header
            className="bg-white p-3.5 sm:p-5 md:p-6 rounded-2xl shadow-sm border border-slate-200 space-y-3.5 md:space-y-0 md:flex md:justify-between md:items-center">
            
            {/* Верхній блок (логотип, користувач, бейдж та мобільні утиліти) */}
            <div className="flex items-center justify-between gap-3 w-full md:w-auto">
                <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
                    <div
                        className="bg-white p-1 rounded-xl shadow-xs border border-blue-100 flex items-center justify-center overflow-hidden w-9 h-9 sm:w-11 sm:h-11 shrink-0">
                        <img
                            src={process.env.PUBLIC_URL + '/logo.ico'}
                            alt="ResQ Logo"
                            className="w-full h-full object-contain"
                        />
                    </div>

                    <div className="min-w-0 text-left">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                            <h1 className="text-xl sm:text-2xl font-bold text-slate-800 tracking-tight leading-none">
                                <span className="text-blue-600">ResQ</span> System
                            </h1>

                            {/* ПЛАШКА СТАТУСУ */}
                            {isAdmin ? (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-600 text-white rounded-full text-[9px] font-semibold uppercase tracking-wider shrink-0">
                                    <ShieldCheck size={10} className="fill-white/20"/>
                                    Admin
                                </span>
                            ) : (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full text-[9px] font-semibold uppercase tracking-wider border border-slate-200 shrink-0">
                                    <User size={10}/>
                                    Волонтер
                                </span>
                            )}
                        </div>

                        <div className="flex items-center gap-1.5 text-slate-500 mt-1 font-medium text-xs leading-none">
                            <span className="font-semibold text-slate-700 truncate max-w-[140px] sm:max-w-[220px] md:max-w-none">
                                {currentUser?.username || 'Користувач'}
                            </span>
                            <span className="text-slate-300">•</span>
                            <span className="text-[11px] text-slate-400">
                                {isAdmin ? 'Повний доступ' : 'Обмежений'}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Швидкі кнопки оновлення та виходу для мобільних екранів (< md) */}
                <div className="flex md:hidden items-center gap-1.5 shrink-0">
                    <button
                        onClick={onLogout}
                        className="p-2 bg-red-50 text-red-600 rounded-xl border border-red-100 hover:bg-red-100 active:scale-95 transition-all shadow-2xs"
                        title="Вийти з акаунту"
                        aria-label="Вийти"
                    >
                        <LogOut size={16}/>
                    </button>
                </div>
            </div>

            {/* Блок основних дій */}
            <div className="flex items-center gap-2 sm:gap-2.5 w-full md:w-auto">
                {/* Поставка — для адміна */}
                {isAdmin && (
                    <button
                        onClick={onOpenStockIn}
                        className="flex-1 md:flex-initial flex items-center justify-center gap-1.5 px-3 sm:px-4 py-2 sm:py-2.5 rounded-xl font-bold text-xs sm:text-sm bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 active:scale-95 transition-all shadow-2xs"
                    >
                        <PlusCircle size={16}/>
                        <span>Поставка</span>
                    </button>
                )}

                {/* Створення заявки */}
                <button
                    onClick={onOpenForm}
                    className="flex-1 md:flex-initial flex items-center justify-center gap-1.5 px-3.5 sm:px-5 py-2 sm:py-2.5 rounded-xl font-bold text-xs sm:text-sm bg-blue-600 text-white hover:bg-slate-900 active:scale-95 transition-all shadow-md shadow-blue-100"
                >
                    <ClipboardList size={16}/>
                    <span>Створити заявку</span>
                </button>

                {/* Десктопні кнопки оновлення та виходу (тільки >= md) */}
                <div className="hidden md:flex items-center gap-2 ml-2 pl-3 border-l border-slate-200">
                    <button
                        onClick={onLogout}
                        className="p-2.5 bg-red-50 text-red-500 rounded-xl border border-red-100 hover:bg-red-100 transition-all active:scale-95 shadow-2xs"
                        title="Вийти з акаунту"
                    >
                        <LogOut size={18}/>
                    </button>
                </div>
            </div>
        </header>
    );
};

export default Header;