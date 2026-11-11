import React, {useState} from 'react';
import {useForm} from 'react-hook-form';
import {zodResolver} from '@hookform/resolvers/zod';
import * as z from 'zod';
import axios from 'axios';
import {toast} from 'react-hot-toast';
import {Mail, Lock, Phone, Building2, ArrowRight, ShieldCheck, CheckCircle2, Eye, EyeOff} from '../UI/icons';
import Modal from '../UI/Modal';

const nameRegex = /^[\p{L}\s'-]+$/u;

// Маска телефона: +380 (XX) XXX-XX-XX — приймає лише цифри
const phoneDigits = (v) => (v || '').replace(/\D/g, '');

const formatPhone = (raw) => {
    let d = phoneDigits(raw);
    if (d.startsWith('380')) d = d.slice(3);
    else if (d.startsWith('80')) d = d.slice(2);
    else if (d.startsWith('0')) d = d.slice(1);
    d = d.slice(0, 9);
    if (!d) return '';
    let out = '+380 (' + d.slice(0, 2);
    if (d.length > 2) out += ') ' + d.slice(2, 5);
    if (d.length > 5) out += '-' + d.slice(5, 7);
    if (d.length > 7) out += '-' + d.slice(7, 9);
    return out;
};

// Email: щось@домен.зона (без пробілів, з крапкою в домені)
const EMAIL_REGEX = /^[^\s@]+@[^\s@.]+(\.[^\s@.]+)+$/;

const schema = z.object({
    identifier: z.string().min(3, "Мінімум 3 символи"),
    password: z.string().min(4, "Пароль занадто короткий"),
    firstName: z.string().optional(),
    lastName: z.string().optional(),
    phone: z.string().optional(),
    organization: z.string().optional(),
}).superRefine((data, ctx) => {
    if (!window.isLoginModeGlobal) {
        if (!EMAIL_REGEX.test((data.identifier || '').trim())) {
            ctx.addIssue({code: z.ZodIssueCode.custom, message: "Введіть коректний email, наприклад name@example.com", path: ['identifier']});
        }
        if (!data.firstName || !nameRegex.test(data.firstName)) {
            ctx.addIssue({code: z.ZodIssueCode.custom, message: "Тільки літери", path: ['firstName']});
        }
        if (!data.lastName || !nameRegex.test(data.lastName)) {
            ctx.addIssue({code: z.ZodIssueCode.custom, message: "Тільки літери", path: ['lastName']});
        }
        if (!data.phone || phoneDigits(data.phone).length !== 12) {
            ctx.addIssue({code: z.ZodIssueCode.custom, message: "Введіть повний номер: +380 (XX) XXX-XX-XX", path: ['phone']});
        }
        if (!data.organization || data.organization.length < 2) {
            ctx.addIssue({
                code: z.ZodIssueCode.custom,
                message: "Вкажіть підрозділ/організацію",
                path: ['organization']
            });
        }
    }
});

// Поле пароля з кнопкою «показати/сховати»
const PasswordInput = ({value, onChange, onKeyDown, placeholder, autoFocus}) => {
    const [visible, setVisible] = useState(false);
    return (
        <div className="relative mt-1">
            <input
                type={visible ? 'text' : 'password'}
                value={value}
                onChange={onChange}
                onKeyDown={onKeyDown}
                placeholder={placeholder}
                autoFocus={autoFocus}
                autoComplete="new-password"
                className="w-full pl-4 pr-12 py-3 bg-slate-50 border-2 border-slate-100 rounded-xl font-bold focus:border-blue-500 outline-none transition-all"
            />
            <button
                type="button"
                onClick={() => setVisible(v => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-slate-400 hover:text-slate-700 transition-colors"
                aria-label={visible ? 'Сховати пароль' : 'Показати пароль'}
            >
                {visible ? <EyeOff size={18}/> : <Eye size={18}/>}
            </button>
        </div>
    );
};

const AuthModal = ({isOpen, onClose, onSuccess}) => {
    const [isLogin, setIsLogin] = useState(true);
    const [showPassword, setShowPassword] = useState(false);
    // Стан для відображення модалки успішної реєстрації з інструкцією
    const [showSuccessModal, setShowSuccessModal] = useState(false);
    const [showNotApprovedModal, setShowNotApprovedModal] = useState(false);
    const [registeredEmail, setRegisteredEmail] = useState('');

    const ADMIN_EMAIL = 'admin@resq.ua';
    const adminMailto = `mailto:${ADMIN_EMAIL}?subject=${encodeURIComponent('Підтвердження акаунта ResQ')}&body=${encodeURIComponent(`Доброго дня! Прошу підтвердити мій акаунт.\nМоя пошта: ${registeredEmail}\n`)}`;

    // Закриття вікна успіху завершує й головне вікно авторизації
    const closeSuccessModal = () => {
        setShowSuccessModal(false);
        onClose();
    };
    // Стан для форми скидання пароля
    const [showForgotModal, setShowForgotModal] = useState(false);
    const [forgotEmail, setForgotEmail] = useState('');
    const [isSendingReset, setIsSendingReset] = useState(false);

    window.isLoginModeGlobal = isLogin;

    const {register, handleSubmit, formState: {errors, isSubmitting}, reset} = useForm({
        resolver: zodResolver(schema),
        mode: "onChange"
    });

    const onSubmit = async (data) => {
        try {
            if (isLogin) {
                // --- СТАНДАРТНИЙ ВХІД ---
                const response = await axios.post('/api/token/', {
                    username: data.identifier,
                    password: data.password
                });

                // Не показуємо тост тут — App.js вже очистить тости та покаже одне "Вітаємо, ..."
                onSuccess({username: data.identifier, email: data.identifier}, response.data);
            } else {
                // --- РЕЄСТРАЦІЯ ---
                const regData = {
                    username: data.identifier.trim(),
                    email: data.identifier.trim(),
                    password: data.password,
                    first_name: data.firstName,
                    last_name: data.lastName,
                    phone: `+${phoneDigits(data.phone)}`,
                    organization: data.organization
                };

                // Зберігаємо дані в базу даних
                await axios.post('/api/register/', regData);

                // Очищуємо форму; головне вікно ховається, поки відкрите вікно успіху
                reset();

                // Зберігаємо email та відкриваємо красиве вікно-інструкцію
                setRegisteredEmail(data.identifier);
                setShowSuccessModal(true);
            }
        } catch (e) {
            console.error("Auth error details:", e.response);

            if (!e.response) {
                toast.error("Сервер не відповідає. Перевірте з'єднання або спробуйте пізніше.");
            } else if (e.response.status === 401) {
                const responseData = e.response.data;

                if (responseData?.code === "not_approved") {
                    setRegisteredEmail(data.identifier);
                    setShowNotApprovedModal(true);
                } else {
                    toast.error("Невірний логін або пароль. Перевірте дані.");
                }
            } else if (e.response.status === 400) {
                const serverData = e.response.data;
                const emailErr = [].concat(serverData.email || []).join(' ');
                if (emailErr) {
                    toast.error(/вже/.test(emailErr)
                        ? "Користувач з таким Email вже зареєстрований."
                        : "Введіть коректний email, наприклад name@example.com");
                } else if (serverData.username) {
                    // логін = email, тож зайнятий логін означає, що така пошта вже є
                    toast.error("Користувач з таким Email вже зареєстрований.");
                } else {
                    toast.error("Помилка даних. Перевірте правильність заповнення.");
                }
            } else if (e.response.status >= 500) {
                toast.error("Внутрішня помилка сервера. Ми вже лагодимо!");
            } else {
                toast.error(e.response.data?.detail || "Щось пішло не так. Спробуйте ще раз.");
            }
        }
    };

    // Скидання пароля: 1) email → 2) код → 3) новий пароль
    const [resetStep, setResetStep] = useState(1);
    const [resetCode, setResetCode] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [newPassword2, setNewPassword2] = useState('');
    const [cooldown, setCooldown] = useState(0);

    React.useEffect(() => {
        if (cooldown <= 0) return undefined;
        const t = setTimeout(() => setCooldown(c => c - 1), 1000);
        return () => clearTimeout(t);
    }, [cooldown]);

    const closeForgotModal = () => {
        setShowForgotModal(false);
        setResetStep(1);
        setResetCode('');
        setNewPassword('');
        setNewPassword2('');
    };

    const errText = (e, fallback) => e?.response?.data?.error || fallback;

    // Крок 1: надсилаємо код на пошту, вказану при реєстрації
    const handleForgotPassword = async () => {
        const email = forgotEmail.trim();
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            toast.error("Введіть коректний email, який ви вказували при реєстрації");
            return;
        }
        setIsSendingReset(true);
        try {
            await axios.post('/api/password-reset/', {email});
            toast.success("Якщо акаунт існує — код надіслано на вашу пошту");
            setResetStep(2);
            setCooldown(60);
        } catch (e) {
            toast.error(errText(e, "Не вдалося надіслати код. Спробуйте пізніше."));
        } finally {
            setIsSendingReset(false);
        }
    };

    // Крок 2: перевірка коду (пароль ще не змінюємо)
    const handleVerifyCode = async () => {
        if (!/^\d{6}$/.test(resetCode.trim())) {
            toast.error("Введіть 6-значний код з листа");
            return;
        }
        setIsSendingReset(true);
        try {
            await axios.post('/api/password-reset/verify/', {
                email: forgotEmail.trim(),
                code: resetCode.trim()
            });
            toast.success("Код підтверджено");
            setResetStep(3);
        } catch (e) {
            toast.error(errText(e, "Не вдалося перевірити код"));
        } finally {
            setIsSendingReset(false);
        }
    };

    // Крок 3: новий пароль (доступний лише після правильного коду)
    const handleConfirmReset = async () => {
        if (newPassword.length < 8) {
            toast.error("Пароль має містити щонайменше 8 символів");
            return;
        }
        if (newPassword !== newPassword2) {
            toast.error("Паролі не збігаються");
            return;
        }
        setIsSendingReset(true);
        try {
            await axios.post('/api/password-reset/confirm/', {
                email: forgotEmail.trim(),
                code: resetCode.trim(),
                new_password: newPassword
            });
            toast.success("Пароль змінено! Тепер увійдіть з новим паролем.");
            closeForgotModal();
            setForgotEmail('');
        } catch (e) {
            const msg = errText(e, "Не вдалося змінити пароль");
            toast.error(msg);
            // Якщо код вже недійсний — повертаємо на крок введення коду
            if (/Код недійсний|спроб/.test(msg)) {
                setResetCode('');
                setResetStep(2);
            }
        } finally {
            setIsSendingReset(false);
        }
    };

    return (
        <>
            {/* Головне вікно входу / реєстрації */}
            <Modal isOpen={isOpen && !showSuccessModal && !showNotApprovedModal} onClose={onClose} title={isLogin ? 'Авторизація' : 'Реєстрація'} icon={ShieldCheck}>
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">

                    {!isLogin && (
                        <>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                                <div className="text-left">
                                    <label className="text-[10px] font-black uppercase text-slate-400 ml-1">Ім'я</label>
                                    <input {...register("firstName")}
                                           className="w-full px-4 py-3 bg-slate-50 border-2 border-slate-100 rounded-xl font-bold focus:border-blue-500 outline-none transition-all"/>
                                    {errors.firstName && <span
                                        className="text-[9px] text-red-500 font-bold">{errors.firstName.message}</span>}
                                </div>
                                <div className="text-left">
                                    <label className="text-[10px] font-black uppercase text-slate-400 ml-1">Прізвище</label>
                                    <input {...register("lastName")}
                                           className="w-full px-4 py-3 bg-slate-50 border-2 border-slate-100 rounded-xl font-bold focus:border-blue-500 outline-none transition-all"/>
                                    {errors.lastName && <span
                                        className="text-[9px] text-red-500 font-bold">{errors.lastName.message}</span>}
                                </div>
                            </div>

                            <div className="text-left">
                                <label className="text-[10px] font-black uppercase text-slate-400 ml-1">Організація / Підрозділ</label>
                                <div className="relative">
                                    <Building2 className="absolute left-3 top-3.5 text-slate-400" size={18}/>
                                    <input {...register("organization")} placeholder="Назва підрозділу"
                                           className="w-full pl-10 pr-4 py-3 bg-slate-50 border-2 border-slate-100 rounded-xl font-bold focus:border-blue-500 outline-none transition-all"/>
                                </div>
                                {errors.organization && <span
                                    className="text-[9px] text-red-500 font-bold">{errors.organization.message}</span>}
                            </div>

                            <div className="text-left">
                                <label className="text-[10px] font-black uppercase text-slate-400 ml-1">Телефон</label>
                                <div className="relative">
                                    <Phone className="absolute left-3 top-3.5 text-slate-400" size={18}/>
                                    <input {...register("phone", {onChange: (e) => { e.target.value = formatPhone(e.target.value); }})}
                                           type="tel" inputMode="tel" autoComplete="tel" maxLength={19}
                                           onKeyDown={(e) => { if (e.key.length === 1 && !/[0-9+]/.test(e.key) && !e.ctrlKey && !e.metaKey) e.preventDefault(); }}
                                           placeholder="+380 (__) ___-__-__"
                                           className="w-full pl-10 pr-4 py-3 bg-slate-50 border-2 border-slate-100 rounded-xl font-bold focus:border-blue-500 outline-none transition-all"/>
                                </div>
                                {errors.phone &&
                                    <span className="text-[9px] text-red-500 font-bold">{errors.phone.message}</span>}
                            </div>
                        </>
                    )}

                    <div className="text-left">
                        <label className="text-[10px] font-black uppercase text-slate-400 ml-1">
                            {isLogin ? "Логін або Email" : "Email"}
                        </label>
                        <div className="relative">
                            <Mail className="absolute left-3 top-3.5 text-slate-400" size={18}/>
                            <input {...register("identifier")}
                                   className="w-full pl-10 pr-4 py-3 bg-slate-50 border-2 border-slate-100 rounded-xl font-bold focus:border-blue-500 outline-none transition-all"
                                   placeholder="email@test.com"/>
                        </div>
                        {errors.identifier &&
                            <span className="text-[9px] text-red-500 font-bold">{errors.identifier.message}</span>}
                    </div>

                    <div className="text-left">
                        <label className="text-[10px] font-black uppercase text-slate-400 ml-1">Пароль</label>
                        <div className="relative">
                            <Lock className="absolute left-3 top-3.5 text-slate-400" size={18}/>
                            <input {...register("password")} type={showPassword ? "text" : "password"}
                                   className="w-full pl-10 pr-11 py-3 bg-slate-50 border-2 border-slate-100 rounded-xl font-bold focus:border-blue-500 outline-none transition-all text-sm"/>
                            <button
                                type="button"
                                onClick={() => setShowPassword(prev => !prev)}
                                className="absolute right-3 top-3 text-slate-400 hover:text-slate-600 p-0.5 focus:outline-none transition-colors"
                                aria-label={showPassword ? "Сховати пароль" : "Показати пароль"}
                            >
                                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                        </div>
                        {errors.password &&
                            <span className="text-[9px] text-red-500 font-bold">{errors.password.message}</span>}
                    </div>

                    {/* Посилання "Забули пароль?" — тільки для форми входу */}
                    {isLogin && (
                        <div className="text-right -mt-2">
                            <button
                                type="button"
                                onClick={() => setShowForgotModal(true)}
                                className="text-[11px] font-bold text-slate-400 hover:text-blue-500 transition-colors"
                            >
                                Забули пароль?
                            </button>
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={isSubmitting}
                        className="w-full bg-slate-900 text-white font-black py-4 rounded-2xl shadow-xl hover:bg-blue-600 disabled:bg-slate-400 transition-all active:scale-95 flex items-center justify-center gap-3 mt-4"
                    >
                        {isSubmitting ? 'ЗАЧЕКАЙТЕ...' : (isLogin ? 'УВІЙТИ' : 'ЗАРЕЄСТРУВАТИСЯ')}
                        {!isSubmitting && <ArrowRight size={20}/>}
                    </button>

                    <div className="text-center pt-2">
                        <button type="button" onClick={() => {
                            setIsLogin(!isLogin);
                            reset();
                        }} className="text-sm font-bold text-slate-400 hover:text-blue-600 transition-colors">
                            {isLogin ? "Немає профілю? Створити" : "Вже є профіль? Увійти"}
                        </button>
                    </div>
                </form>
            </Modal>

            {/* Модальне вікно скидання пароля */}
            <Modal
                isOpen={showForgotModal}
                onClose={closeForgotModal}
                title="Скидання пароля"
                subtitle={resetStep === 1 ? "Крок 1 з 3 — підтвердження пошти" : resetStep === 2 ? "Крок 2 з 3 — код з листа" : "Крок 3 з 3 — новий пароль"}
                icon={Lock}
            >
                {resetStep === 1 ? (
                    <div className="space-y-5 text-left">
                        <p className="text-sm text-slate-500 leading-relaxed">
                            Введіть електронну пошту, яку ви вказували <b>при реєстрації</b>. Ми надішлемо на неї 6-значний код для скидання пароля.
                        </p>
                        <div className="text-left">
                            <label className="text-[10px] font-semibold uppercase text-slate-400 ml-1">Email з реєстрації</label>
                            <div className="relative mt-1">
                                <Mail className="absolute left-3 top-3.5 text-slate-400" size={18}/>
                                <input
                                    type="email"
                                    value={forgotEmail}
                                    onChange={e => setForgotEmail(e.target.value)}
                                    onKeyDown={e => { if (e.key === 'Enter') handleForgotPassword(); }}
                                    placeholder="email@test.com"
                                    autoFocus
                                    className="w-full pl-10 pr-4 py-3 bg-slate-50 border-2 border-slate-100 rounded-xl font-bold focus:border-blue-500 outline-none transition-all"
                                />
                            </div>
                        </div>
                        <button
                            type="button"
                            onClick={handleForgotPassword}
                            disabled={isSendingReset}
                            className="w-full bg-slate-900 text-white font-bold py-4 rounded-2xl shadow-xl hover:bg-blue-600 disabled:bg-slate-400 transition-all active:scale-95 flex items-center justify-center gap-3"
                        >
                            {isSendingReset ? 'НАДСИЛАННЯ...' : 'НАДІСЛАТИ КОД'}
                            {!isSendingReset && <ArrowRight size={20}/>}
                        </button>
                    </div>
                ) : resetStep === 2 ? (
                    <div className="space-y-5 text-left">
                        <p className="text-sm text-slate-500 leading-relaxed">
                            Код надіслано на <b className="text-slate-700">{forgotEmail}</b>. Він дійсний 10 хвилин. Якщо листа немає — перевірте «Спам» і правильність пошти.
                        </p>
                        <div>
                            <label className="text-[10px] font-semibold uppercase text-slate-400 ml-1">Код з листа</label>
                            <input
                                type="text"
                                inputMode="numeric"
                                maxLength={6}
                                value={resetCode}
                                onChange={e => setResetCode(e.target.value.replace(/\D/g, ''))}
                                onKeyDown={e => { if (e.key === 'Enter') handleVerifyCode(); }}
                                placeholder="••••••"
                                autoFocus
                                className="mt-1 w-full px-4 py-3 bg-slate-50 border-2 border-slate-100 rounded-xl font-bold text-center text-xl tracking-[0.5em] focus:border-blue-500 outline-none transition-all"
                            />
                        </div>
                        <button
                            type="button"
                            onClick={handleVerifyCode}
                            disabled={isSendingReset}
                            className="w-full bg-slate-900 text-white font-bold py-4 rounded-2xl shadow-xl hover:bg-blue-600 disabled:bg-slate-400 transition-all active:scale-95 flex items-center justify-center gap-3"
                        >
                            {isSendingReset ? 'ПЕРЕВІРКА...' : 'ПІДТВЕРДИТИ КОД'}
                            {!isSendingReset && <ArrowRight size={20}/>}
                        </button>
                        <div className="flex items-center justify-between text-xs font-medium text-slate-500">
                            <button type="button" onClick={() => { setResetStep(1); setResetCode(''); }} className="hover:text-slate-800 underline">
                                Змінити пошту
                            </button>
                            <button
                                type="button"
                                disabled={cooldown > 0 || isSendingReset}
                                onClick={handleForgotPassword}
                                className="text-blue-600 hover:text-blue-800 disabled:text-slate-400 disabled:no-underline underline"
                            >
                                {cooldown > 0 ? `Надіслати код ще раз (${cooldown} с)` : 'Надіслати код ще раз'}
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="space-y-5 text-left">
                        <div className="bg-green-50 border border-green-100 text-green-700 text-xs font-medium p-3 rounded-xl flex items-center gap-2">
                            <CheckCircle2 size={16} className="shrink-0"/> Код підтверджено. Придумайте новий пароль.
                        </div>
                        <div>
                            <label className="text-[10px] font-semibold uppercase text-slate-400 ml-1">Новий пароль</label>
                            <PasswordInput
                                value={newPassword}
                                onChange={e => setNewPassword(e.target.value)}
                                placeholder="Мінімум 8 символів"
                                autoFocus
                            />
                        </div>
                        <div>
                            <label className="text-[10px] font-semibold uppercase text-slate-400 ml-1">Повторіть пароль</label>
                            <PasswordInput
                                value={newPassword2}
                                onChange={e => setNewPassword2(e.target.value)}
                                onKeyDown={e => { if (e.key === 'Enter') handleConfirmReset(); }}
                            />
                        </div>
                        <button
                            type="button"
                            onClick={handleConfirmReset}
                            disabled={isSendingReset}
                            className="w-full bg-slate-900 text-white font-bold py-4 rounded-2xl shadow-xl hover:bg-blue-600 disabled:bg-slate-400 transition-all active:scale-95 flex items-center justify-center gap-3"
                        >
                            {isSendingReset ? 'ЗБЕРЕЖЕННЯ...' : 'ЗМІНИТИ ПАРОЛЬ'}
                            {!isSendingReset && <ArrowRight size={20}/>}
                        </button>
                    </div>
                )}
                )}
            </Modal>

            {/* Модалка після успішної реєстрації */}
            <Modal
                isOpen={showSuccessModal}
                onClose={closeSuccessModal}
                title="Реєстрацію завершено!"
                subtitle="Очікування підтвердження"
                icon={CheckCircle2}
            >
                <div className="space-y-5 text-left">
                    <div className="bg-green-50 border-2 border-green-100 p-4 rounded-2xl flex items-start gap-4">
                        <div className="bg-green-500 text-white p-2 rounded-xl mt-1 shrink-0">
                            <CheckCircle2 size={20}/>
                        </div>
                        <div>
                            <h4 className="font-bold text-green-900 text-base">Ви успішно зареєстровані</h4>
                            <p className="text-xs text-green-700 mt-1 leading-relaxed">
                                Акаунт створено з поштою <span className="font-bold">{registeredEmail}</span>.
                            </p>
                        </div>
                    </div>

                    <div className="text-sm text-slate-600 leading-relaxed space-y-2">
                        <p>
                            З вами зв’яжеться адміністратор для <b>підтвердження прав користування</b> системою. Він може попросити
                            надіслати документи, що підтверджують вашу організацію чи підрозділ, та уточнити інші деталі.
                        </p>
                        <p>До підтвердження вхід у систему буде недоступний.</p>
                    </div>

                    <div className="border-t border-slate-100 pt-4">
                        <h5 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Можна не чекати</h5>
                        <p className="text-sm text-slate-600 leading-relaxed">
                            Напишіть адміністратору самостійно та прикріпіть підтверджуючі документи — це прискорить перевірку:
                        </p>
                        <a
                            href={adminMailto}
                            className="mt-3 flex items-center justify-center gap-2 p-3 bg-blue-600 hover:bg-blue-700 rounded-xl font-bold text-white text-center transition-all active:scale-95"
                        >
                            <Mail size={18}/> Написати адміністратору
                        </a>
                        <p className="text-[11px] text-slate-400 text-center mt-2">{ADMIN_EMAIL}</p>
                    </div>

                    <button
                        type="button"
                        onClick={closeSuccessModal}
                        className="w-full bg-slate-900 text-white font-bold py-4 rounded-2xl shadow-xl hover:bg-blue-600 transition-all active:scale-95"
                    >
                        ЗРОЗУМІЛО
                    </button>
                </div>
            </Modal>

            {/* Модалка: акаунт ще не підтверджено адміністратором */}
            <Modal
                isOpen={showNotApprovedModal}
                onClose={() => setShowNotApprovedModal(false)}
                title="Акаунт не підтверджено"
                subtitle="Очікування адміністратора"
                icon={ShieldCheck}
                maxWidth="max-w-md"
            >
                <div className="space-y-5 text-left">
                    <div className="bg-amber-50 border-2 border-amber-100 p-4 rounded-2xl">
                        <h4 className="font-bold text-amber-900 text-base">Ваш обліковий запис ще не підтверджено адміністратором.</h4>
                        <p className="text-xs text-amber-700 mt-2 leading-relaxed">
                            Вхід стане доступним після перевірки. Якщо ви ще не надсилали документи, що підтверджують вашу організацію, —
                            напишіть адміністратору, і він прискорить підтвердження.
                        </p>
                    </div>
                    <a
                        href={adminMailto}
                        className="flex items-center justify-center gap-2 p-3.5 bg-blue-600 hover:bg-blue-700 rounded-xl font-bold text-white text-center transition-all active:scale-95"
                    >
                        <Mail size={18}/> Написати адміністратору
                    </a>
                    <p className="text-[11px] text-slate-400 text-center -mt-2">{ADMIN_EMAIL}</p>
                    <button
                        type="button"
                        onClick={() => setShowNotApprovedModal(false)}
                        className="w-full bg-slate-100 text-slate-600 font-semibold py-3.5 rounded-2xl hover:bg-slate-200 transition-all active:scale-95"
                    >
                        Закрити
                    </button>
                </div>
            </Modal>
        </>
    );
};

export default AuthModal;