import React, { useState, useEffect } from 'react';
import { ArrowUp } from 'lucide-react';

const ScrollToTop = () => {
    const [isVisible, setIsVisible] = useState(false);

    // Слідкуємо за скролом сторінки
    useEffect(() => {
        const toggleVisibility = () => {
            if (window.pageYOffset > 300) {
                setIsVisible(true);
            } else {
                setIsVisible(false);
            }
        };

        window.addEventListener('scroll', toggleVisibility);
        return () => window.removeEventListener('scroll', toggleVisibility);
    }, []);

    // Функція плавної прокрутки вгору
    const scrollToTop = () => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    };

    if (!isVisible) {
        return null;
    }

    return (
        <button
            onClick={scrollToTop}
            aria-label="Прокрутити вгору"
            className="fixed bottom-6 right-6 z-50 bg-slate-900 text-white p-3.5 rounded-2xl shadow-2xl hover:bg-blue-600 border-2 border-slate-800 hover:border-blue-500 transition-all duration-300 flex items-center justify-center group active:scale-95 animate-fade-in"
        >
            <ArrowUp size={20} className="transition-transform group-hover:-translate-y-1" />
        </button>
    );
};

export default ScrollToTop;