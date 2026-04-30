import React, { useEffect } from 'react';
import { X } from 'lucide-react';

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
      className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm overflow-y-auto"
      onClick={onClose}
    >
      <div
        className={`bg-white rounded-2xl shadow-2xl w-full ${maxWidth} relative animate-in zoom-in duration-300 my-auto border border-slate-100`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Кнопка закриття */}
        <button
          onClick={onClose}
          className="absolute top-6 right-6 p-2 hover:bg-slate-100 rounded-full text-slate-400 transition-colors z-10"
        >
          <X size={24} />
        </button>

        {/* Контент модалки */}
        <div className="p-6 md:p-8">
          {/* Шапка */}
          {(title || Icon) && (
            <div className="flex items-center gap-3 mb-8 pr-10 border-b border-slate-50 pb-6">
              {Icon && (
                <div className="bg-slate-100 p-2.5 rounded-xl">
                  <Icon className="text-slate-600" size={24} />
                </div>
              )}
              <div>
                <h2 className="text-2xl font-bold text-slate-800 tracking-tight">{title}</h2>
                {subtitle && (
                  <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-0.5">
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