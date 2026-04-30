import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import axios from 'axios';
import { toast } from 'react-hot-toast';
import { Mail, Lock, User, Phone, Building2, ArrowRight, ShieldCheck } from 'lucide-react';
import Modal from '../UI/Modal';

const nameRegex = /^[\p{L}\s'-]+$/u;

const schema = z.object({
  identifier: z.string().min(3, "Мінімум 3 символи"),
  password: z.string().min(4, "Пароль занадто короткий"),
  firstName: z.string().optional(),
  lastName: z.string().optional(),
  phone: z.string().optional(),
  organization: z.string().optional(),
}).superRefine((data, ctx) => {
  // Перевіряємо ці поля ТІЛЬКИ в режимі реєстрації
  if (!window.isLoginModeGlobal) {
    if (!data.firstName || !nameRegex.test(data.firstName)) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "Тільки літери", path: ['firstName'] });
    }
    if (!data.lastName || !nameRegex.test(data.lastName)) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "Тільки літери", path: ['lastName'] });
    }
    if (!data.phone || !/^\+?[0-9]{10,12}$/.test(data.phone)) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "Невірний формат (10-12 цифр)", path: ['phone'] });
    }
    // КРИТИЧНО: якщо цього поля немає в HTML, форма ніколи не відправиться
    if (!data.organization || data.organization.length < 2) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "Вкажіть підрозділ/організацію", path: ['organization'] });
    }
  }
});

const AuthModal = ({ isOpen, onClose, onSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  window.isLoginModeGlobal = isLogin;

  const { register, handleSubmit, formState: { errors, isSubmitting }, reset } = useForm({
    resolver: zodResolver(schema),
    mode: "onChange" // Допомагає бачити помилки одразу
  });

    const onSubmit = async (data) => {
    try {
      if (isLogin) {
        // --- СТАНДАРТНИЙ ВХІД ---
        const response = await axios.post('/api/token/', {
          username: data.identifier,
          password: data.password
        });

        onSuccess({ username: data.identifier, email: data.identifier }, response.data);
        onClose();
      } else {
        // --- РЕЄСТРАЦІЯ + АВТОМАТИЧНИЙ ВХІД ---
        const regData = {
          email: data.identifier,
          password: data.password,
          first_name: data.firstName,
          last_name: data.lastName,
          phone: data.phone,
          organization: data.organization
        };

        // 1. Реєструємо користувача
        await axios.post('/api/register/', regData);

        // 2. Одразу робимо запит на отримання токена (Login)
        // Ми використовуємо ті ж самі дані (email та password), що щойно відправили на реєстрацію
        const loginResponse = await axios.post('/api/token/', {
          username: data.identifier,
          password: data.password
        });

        toast.success("Реєстрація успішна! Ласкаво просимо.");

        // 3. Викликаємо onSuccess, щоб App.js зберіг токени та переключив інтерфейс
        onSuccess({
          username: data.identifier,
          email: data.identifier,
          first_name: data.firstName,
          last_name: data.lastName
        }, loginResponse.data);

        onClose(); // Закриваємо модалку
        reset();   // Очищуємо поля
      }
    } catch (e) {
      console.error("Auth error:", e);
      const msg = e.response?.data?.error || e.response?.data?.detail || "Помилка авторизації";
      toast.error(msg);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={isLogin ? 'Авторизація' : 'Реєстрація'} icon={ShieldCheck}>
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
              <label className="text-[10px] font-black uppercase text-slate-400 ml-1">Організація / Підрозділ</label>
              <div className="relative">
                <Building2 className="absolute left-3 top-3.5 text-slate-400" size={18} />
                <input {...register("organization")} placeholder="Назва підрозділу" className="w-full pl-10 pr-4 py-3 bg-slate-50 border-2 border-slate-100 rounded-xl font-bold focus:border-blue-500 outline-none transition-all" />
              </div>
              {errors.organization && <span className="text-[9px] text-red-500 font-bold">{errors.organization.message}</span>}
            </div>

            <div className="text-left">
              <label className="text-[10px] font-black uppercase text-slate-400 ml-1">Телефон</label>
              <div className="relative">
                <Phone className="absolute left-3 top-3.5 text-slate-400" size={18} />
                <input {...register("phone")} placeholder="+380..." className="w-full pl-10 pr-4 py-3 bg-slate-50 border-2 border-slate-100 rounded-xl font-bold focus:border-blue-500 outline-none transition-all" />
              </div>
              {errors.phone && <span className="text-[9px] text-red-500 font-bold">{errors.phone.message}</span>}
            </div>
          </>
        )}

        <div className="text-left">
          <label className="text-[10px] font-black uppercase text-slate-400 ml-1">{isLogin ? "Логін або Email" : "Email"}</label>
          <div className="relative">
            <Mail className="absolute left-3 top-3.5 text-slate-400" size={18} />
            <input {...register("identifier")} className="w-full pl-10 pr-4 py-3 bg-slate-50 border-2 border-slate-100 rounded-xl font-bold focus:border-blue-500 outline-none transition-all" placeholder="email@test.com" />
          </div>
          {errors.identifier && <span className="text-[9px] text-red-500 font-bold">{errors.identifier.message}</span>}
        </div>

        <div className="text-left">
          <label className="text-[10px] font-black uppercase text-slate-400 ml-1">Пароль</label>
          <div className="relative">
            <Lock className="absolute left-3 top-3.5 text-slate-400" size={18} />
            <input {...register("password")} type="password" className="w-full pl-10 pr-4 py-3 bg-slate-50 border-2 border-slate-100 rounded-xl font-bold focus:border-blue-500 outline-none transition-all" />
          </div>
          {errors.password && <span className="text-[9px] text-red-500 font-bold">{errors.password.message}</span>}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full bg-slate-900 text-white font-black py-4 rounded-2xl shadow-xl hover:bg-blue-600 disabled:bg-slate-400 transition-all active:scale-95 flex items-center justify-center gap-3 mt-4"
        >
          {isSubmitting ? 'ЗАЧЕКАЙТЕ...' : (isLogin ? 'УВІЙТИ' : 'ЗАРЕЄСТРУВАТИСЯ')}
          {!isSubmitting && <ArrowRight size={20} />}
        </button>

        <div className="text-center pt-2">
          <button type="button" onClick={() => { setIsLogin(!isLogin); reset(); }} className="text-sm font-bold text-slate-400 hover:text-blue-600 transition-colors">
            {isLogin ? "Немає профілю? Створити" : "Вже є профіль? Увійти"}
          </button>
        </div>
      </form>
    </Modal>
  );
};

export default AuthModal;