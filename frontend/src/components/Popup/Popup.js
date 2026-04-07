import React from 'react';

const Popup = ({ isOpen, type, title, message, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fade-in">
      <div className={`bg-white rounded-2xl shadow-2xl max-w-sm w-full mx-4 p-6 border-t-4 ${type === 'error' ? 'border-red-500' : 'border-blue-500'}`}>
        <h3 className="text-lg font-bold mb-2">{title}</h3>
        <p className="text-slate-600 mb-6 text-sm">{message}</p>
        <div className="flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 text-white font-medium rounded-lg hover:bg-slate-700 transition-colors"
          >
            ОК
          </button>
        </div>
      </div>
    </div>
  );
};

export default Popup;