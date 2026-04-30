import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Mail, Lock, User, Phone, Building2, ArrowRight, ShieldCheck } from 'lucide-react';
import Modal from './Modal'; // Імпортуємо твій базовий компонент

// Схема валідації
const nameRegex = /^[\p{L}\s'-]+$/u;

const schema = z.object({
  email: z.string().email("Некоректний email"),
  password: z.string().min(6, "Пароль має бути мін. 6 символів"),
  firstName: z.string().optional(),
  lastName: z.string().optional(),
  phone: z.string().optional(),
  organization: z.string().optional(),
}).superRefine((data, ctx) => {
  if (!window.isLoginModeGlobal) {
    // Перевірка імені (тільки літери)
    if (!data.firstName || !nameRegex.test(data.firstName)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Дозволені лише літери",
        path: ['firstName']
      });
    }
    // Перевірка прізвища (тільки літери)
    if (!data.lastName || !nameRegex.test(data.lastName)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Дозволені лише літери",
        path: ['lastName']
      });
    }
    // Телефон
    if (!data.phone || !/^\+?[0-9]{10,12}$/.test(data.phone)) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "Невірний формат", path: ['phone'] });
    }
    // Організація
    if (!data.organization) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "Вкажіть підрозділ", path: ['organization'] });
    }
  }
});

const AuthModal = ({ isOpen, onClose, onSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  window.isLoginModeGlobal = isLogin;

  const { register, handleSubmit, formState: { errors, isSubmitting }, reset } = useForm({
    resolver: zodResolver(schema)
  });

  const onSubmit = async (data) => {
    try {
      console.log("Відправка даних:", data);
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Передаємо дані форми у функцію успіху
      onSuccess(data);
      onClose();
    } catch (e) {
      console.error("Помилка авторизації");
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isLogin ? 'Авторизація' : 'Реєстрація'}
      subtitle={isLogin ? 'Доступ до панелі керування' : 'Створення кабінету волонтера'}
      icon={ShieldCheck}
      maxWidth="max-w-md"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {!isLogin && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-left">
                <label className="text-[10px] font-black uppercase text-slate-400 ml-1">Ім'я</label>
                <input {...register("firstName")} className="w-full px-4 py-3 bg-slate-50 border-2 border-slate-100 rounded-xl font-bold focus:border-blue-500 outline-none transition-all" />
                {errors.firstName && <span className="text-[9px] text-red-500 font-bold">{errors.firstName.message}</span>}
              </div>
              <div className="text-left">
                <label className="text-[10px] font-black uppercase text-slate-400 ml-1">Прізвище</label>
                <input {...register("lastName")} className="w-full px-4 py-3 bg-slate-50 border-2 border-slate-100 rounded-xl font-bold focus:border-blue-500 outline-none transition-all" />
                {errors.lastName && <span className="text-[9px] text-red-500 font-bold">{errors.lastName.message}</span>}
              </div>
            </div>
            <div className="text-left">
              <label className="text-[10px] font-black uppercase text-slate-400 ml-1">Телефон</label>
              <input {...register("phone")} placeholder="+380..." className="w-full px-4 py-3 bg-slate-50 border-2 border-slate-100 rounded-xl font-bold focus:border-blue-500 outline-none transition-all" />
              {errors.phone && <span className="text-[9px] text-red-500 font-bold">{errors.phone.message}</span>}
            </div>
            <div className="text-left">
              <label className="text-[10px] font-black uppercase text-slate-400 ml-1">Організація</label>
              <input {...register("organization")} placeholder="В/Ч або назва фонду" className="w-full px-4 py-3 bg-slate-50 border-2 border-slate-100 rounded-xl font-bold focus:border-blue-500 outline-none transition-all" />
              {errors.organization && <span className="text-[9px] text-red-500 font-bold">{errors.organization.message}</span>}
            </div>
          </>
        )}

        <div className="text-left">
          <label className="text-[10px] font-black uppercase text-slate-400 ml-1">Email</label>
          <input {...register("email")} type="email" className="w-full px-4 py-3 bg-slate-50 border-2 border-slate-100 rounded-xl font-bold focus:border-blue-500 outline-none transition-all" />
          {errors.email && <span className="text-[9px] text-red-500 font-bold">{errors.email.message}</span>}
        </div>

        <div className="text-left">
          <label className="text-[10px] font-black uppercase text-slate-400 ml-1">Пароль</label>
          <input {...register("password")} type="password" className="w-full px-4 py-3 bg-slate-50 border-2 border-slate-100 rounded-xl font-bold focus:border-blue-500 outline-none transition-all" />
          {errors.password && <span className="text-[9px] text-red-500 font-bold">{errors.password.message}</span>}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full bg-slate-900 text-white font-black py-4 rounded-2xl shadow-xl hover:bg-blue-600 transition-all active:scale-95 flex items-center justify-center gap-3 mt-4"
        >
          {isSubmitting ? 'ОБРОБКА...' : (isLogin ? 'УВІЙТИ' : 'ЗАРЕЄСТРУВАТИСЯ')}
          {!isSubmitting && <ArrowRight size={20} />}
        </button>

        <div className="text-center pt-4">
          <button
            type="button"
            onClick={() => { setIsLogin(!isLogin); reset(); }}
            className="text-sm font-bold text-slate-400 hover:text-blue-600 transition-colors"
          >
            {isLogin ? "Немає профілю? Створити" : "Вже є профіль? Авторизуватись"}
          </button>
        </div>
      </form>
    </Modal>
  );
};

export default AuthModal;