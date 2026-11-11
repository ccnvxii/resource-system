import React, { useEffect } from 'react';
import { X } from './icons';

const Modal = ({ isOpen, onClose, title, subtitle, icon: Icon, children, maxWidth = "max-w-4xl" }) => {
  // Закриття на Escape
  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-2.5 sm:p-4 md:p-6 bg-slate-900/60 backdrop-blur-sm overflow-y-auto"
      onClick={onClose}
    >
      <div
        className={`bg-white rounded-3xl sm:rounded-2xl shadow-2xl w-full ${maxWidth} relative animate-in zoom-in duration-300 my-auto border border-slate-100 max-h-[94vh] flex flex-col overflow-hidden`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Кнопка закриття */}
        <button
          onClick={onClose}
          className="absolute top-3.5 right-3.5 sm:top-5 sm:right-5 p-2 hover:bg-slate-100 rounded-full text-slate-400 hover:text-slate-600 transition-colors z-20"
          aria-label="Закрити вікно"
        >
          <X size={20} />
        </button>

        {/* Контент модалки зі скролом у межах модалки */}
        <div className="p-4 sm:p-6 md:p-8 overflow-y-auto custom-scrollbar flex-1">
          {/* Шапка */}
          {(title || Icon) && (
            <div className="flex items-center gap-3 mb-5 sm:mb-7 pr-10 border-b border-slate-100 pb-4 sm:pb-5">
              {Icon && (
                <div className="bg-slate-100 p-2 sm:p-2.5 rounded-xl shrink-0">
                  <Icon className="text-slate-600" size={20} />
                </div>
              )}
              <div className="min-w-0">
                <h2 className="text-lg sm:text-2xl font-bold text-slate-800 tracking-tight truncate">{title}</h2>
                {subtitle && (
                  <p className="text-[10px] text-slate-400 font-normal uppercase tracking-widest mt-0.5 truncate">
                    {subtitle}
                  </p>
                )}
              </div>
            </div>
          )}

          {children}
        </div>
      </div>
    </div>
  );
};

export default Modal;
