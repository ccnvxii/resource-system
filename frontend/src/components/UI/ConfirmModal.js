import React from 'react';
import Modal from './Modal';
import { AlertCircle } from './icons';

/**
 * Модальне підтвердження небезпечної дії (замість window.confirm).
 * Рендерити ПІСЛЯ іншого вікна, якщо відкривається поверх нього.
 */
const ConfirmModal = ({
    isOpen,
    title = 'Підтвердіть дію',
    message,
    details,
    confirmText = 'Підтвердити',
    cancelText = 'Скасувати',
    loading = false,
    onConfirm,
    onCancel,
}) => (
    <Modal isOpen={isOpen} onClose={onCancel} title={title} subtitle="Дію не можна скасувати" icon={AlertCircle} maxWidth="max-w-md">
        <div className="space-y-5 text-left">
            <div className="bg-red-50 border border-red-100 rounded-2xl p-4">
                <p className="text-sm text-red-900 font-semibold leading-relaxed">{message}</p>
                {details && <p className="text-xs text-red-700 mt-2 leading-relaxed">{details}</p>}
            </div>
            <div className="flex flex-col-reverse sm:flex-row gap-2.5 sm:gap-3 justify-end pt-1">
                <button
                    type="button"
                    onClick={onCancel}
                    disabled={loading}
                    className="w-full sm:w-auto px-5 py-2.5 text-slate-500 font-medium hover:text-slate-700 transition-colors text-sm"
                >
                    {cancelText}
                </button>
                <button
                    type="button"
                    onClick={onConfirm}
                    disabled={loading}
                    className="w-full sm:w-auto px-6 py-2.5 bg-red-600 hover:bg-red-700 disabled:bg-slate-400 text-white font-bold rounded-xl shadow-lg transition-all active:scale-95 text-sm"
                >
                    {loading ? 'ВИКОНАННЯ...' : confirmText}
                </button>
            </div>
        </div>
    </Modal>
);

export default ConfirmModal;
