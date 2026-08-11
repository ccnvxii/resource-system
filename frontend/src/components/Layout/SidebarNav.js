import React, { useState, useEffect } from 'react';
import { Database, BarChart3, GitFork } from 'lucide-react';

const SidebarNav = ({ onNavigate }) => {
    const [activeSection, setActiveSection] = useState('section-stocks');

    useEffect(() => {
        const sections = ['section-stocks', 'section-analytics', 'section-distribution'];

        const observerCallback = (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    setActiveSection(entry.target.id);
                }
            });
        };

        const observerOptions = {
            root: null,
            // Зміщуємо область спостереження, щоб активність спрацьовувала ближче до центру екрана
            rootMargin: '-20% 0px -60% 0px',
            threshold: 0
        };

        const observer = new IntersectionObserver(observerCallback, observerOptions);

        sections.forEach((id) => {
            const element = document.getElementById(id);
            if (element) observer.observe(element);
        });

        return () => {
            sections.forEach((id) => {
                const element = document.getElementById(id);
                if (element) observer.unobserve(element);
            });
        };
    }, []);

    // Стиль для активної кнопки (темний фон, біла іконка, невеликий тіньовий ефект)
    const getButtonStyle = (sectionId) => {
        if (activeSection === sectionId) {
            return "p-3 bg-slate-900 text-white rounded-xl shadow-lg shadow-slate-900/20 scale-105 transition-all flex items-center justify-center group relative";
        }
        return "p-3 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-xl transition-all flex items-center justify-center group relative";
    };

    return (
        <div className="fixed left-6 top-1/2 -translate-y-1/2 z-40 hidden xl:flex flex-col gap-3 bg-white/80 backdrop-blur-md p-2 rounded-2xl shadow-2xl border border-slate-200">
            <button
                onClick={() => onNavigate('section-stocks')}
                title="Запаси на складах"
                className={getButtonStyle('section-stocks')}
            >
                <Database size={20} />
                <span className="absolute left-full ml-3 px-3 py-1.5 bg-slate-900 text-white text-[11px] font-bold rounded-xl whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity shadow-lg pointer-events-none">
                    Запаси на складах
                </span>
            </button>

            <button
                onClick={() => onNavigate('section-analytics')}
                title="Аналітика та Журнал"
                className={getButtonStyle('section-analytics')}
            >
                <BarChart3 size={20} />
                <span className="absolute left-full ml-3 px-3 py-1.5 bg-slate-900 text-white text-[11px] font-bold rounded-xl whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity shadow-lg pointer-events-none">
                    Аналітика (Дашборди)
                </span>
            </button>

            <button
                onClick={() => onNavigate('section-distribution')}
                title="Розподіл ресурсів"
                className={getButtonStyle('section-distribution')}
            >
                <GitFork size={20} />
                <span className="absolute left-full ml-3 px-3 py-1.5 bg-slate-900 text-white text-[11px] font-bold rounded-xl whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity shadow-lg pointer-events-none">
                    Розподіл
                </span>
            </button>
        </div>
    );
};

export default SidebarNav;