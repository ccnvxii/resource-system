import React from 'react';
import {
  ShieldCheck,
  Zap,
  BarChart3,
  ArrowRight,
  Users,
  Package,
  ClipboardCheck
} from 'lucide-react';

const Landing = ({ onEnter, stats }) => {
  return (
    <div className="min-h-screen bg-white font-sans text-slate-900">
        {/* NAVIGATION */}
        <nav className="flex justify-between items-center px-8 py-6 max-w-7xl mx-auto">
          <div className="flex items-center gap-3">
            <div className="bg-white p-1 rounded-xl shadow-sm border-2 border-blue-100 flex items-center justify-center overflow-hidden w-10 h-10 transition-colors hover:border-blue-400">
              <img
                src={process.env.PUBLIC_URL + '/logo.ico'}
                alt="ResQ Logo"
                className="w-full h-full object-contain"
              />
            </div>
            <span className="text-xl font-black tracking-tight text-slate-800">
              ResQ <span className="text-blue-600">System</span>
            </span>
          </div>
        <button
          onClick={onEnter}
          className="text-sm font-bold bg-slate-900 text-white px-6 py-2.5 rounded-full hover:bg-slate-800 transition-all active:scale-95"
        >
          Увійти в кабінет
        </button>
      </nav>

      {/* HERO SECTION */}
      <header className="relative pt-16 pb-32 overflow-hidden">
        <div className="max-w-7xl mx-auto px-8 grid lg:grid-cols-2 gap-12 items-center">
          <div className="relative z-10">
            <span className="inline-block px-4 py-1.5 bg-blue-50 text-blue-600 rounded-full text-xs font-black uppercase tracking-widest mb-6 border border-blue-100">
              Humanitarian Response v3.0
            </span>
            <h1 className="text-6xl lg:text-7xl font-black text-slate-900 leading-[1.1] mb-8">
              Справедливий <br />
              <span className="text-blue-600">розподіл</span> допомоги.
            </h1>
            <p className="text-lg text-slate-500 max-w-lg mb-10 leading-relaxed">
              Інтелектуальна система підтримки прийняття рішень для розподілу гуманітарних ресурсів в Україні на основі матриці пріоритетів та Weighted Max-Min Fairness.
            </p>
            <div className="flex flex-wrap gap-4">
              <button
                onClick={onEnter}
                className="group flex items-center gap-3 px-8 py-4 bg-blue-600 text-white font-bold rounded-2xl hover:bg-blue-700 shadow-xl shadow-blue-200 transition-all hover:-translate-y-1"
              >
                Залишити заявку
                <ClipboardCheck size={20} className="group-hover:scale-110 transition-transform" />
              </button>

              <button
                onClick={onEnter}
                className="flex items-center gap-3 px-8 py-4 bg-white border-2 border-slate-200 text-slate-700 font-bold rounded-2xl hover:bg-slate-50 transition-all"
              >
                Панель управління
                <ArrowRight size={18} className="text-slate-400" />
              </button>
            </div>
          </div>

          <div className="relative">
            <div className="absolute -inset-4 bg-blue-400/20 blur-3xl rounded-full"></div>
            <div className="relative bg-white border border-slate-200 rounded-3xl shadow-2xl p-4 overflow-hidden transform rotate-2">
               {/* Фото: Волонтери в Україні (гуманітарна допомога) */}
               <img
                 src="https://images.unsplash.com/photo-1593113598332-cd288d649433?auto=format&fit=crop&q=80&w=800"
                 alt="Humanitarian Aid Ukraine"
                 className="rounded-2xl grayscale-[20%] hover:grayscale-0 transition-all duration-500"
               />
               <div className="absolute bottom-8 left-8 right-8 bg-white/90 backdrop-blur p-4 rounded-xl border border-slate-100 shadow-lg">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
                    <p className="text-[10px] font-black uppercase tracking-tighter text-slate-600">Моніторинг хабів у реальному часі</p>
                  </div>
               </div>
            </div>
          </div>
        </div>
      </header>

      {/* STATS SECTION */}
      <section className="bg-slate-50 py-24">
        <div className="max-w-7xl mx-auto px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <div className="text-center">
              <div className="text-4xl font-black text-slate-900 mb-2">{stats.stocks || 0}</div>
              <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">Товарів на складі</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-black text-blue-600 mb-2">{stats.requests || 0}</div>
              <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">Активних заявок</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-black text-slate-900 mb-2">{stats.warehouses || 0}</div>
              <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">Локальних хабів</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-black text-emerald-500 mb-2">99.9%</div>
              <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">Точність розподілу</div>
            </div>
          </div>
        </div>
      </section>

      {/* FEATURES SECTION */}
      <section className="py-32">
        <div className="max-w-7xl mx-auto px-8">
          <div className="text-center max-w-2xl mx-auto mb-20">
            <h2 className="text-4xl font-black text-slate-900 mb-6">Чому обирають ResQ?</h2>
            <p className="text-slate-500 font-medium">Цифрова платформа для координації логістики під час дефіциту критичних ресурсів.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: <BarChart3 className="text-blue-600" />,
                title: "Матриця Пріоритетів",
                desc: "Військові підрозділи та медицина отримують найвищий коефіцієнт в алгоритмі автоматично."
              },
              {
                icon: <ShieldCheck className="text-emerald-600" />,
                title: "Прозорий Облік",
                desc: "Кожна одиниця допомоги відстежується від приходу на склад до кінцевого отримувача."
              },
              {
                icon: <Zap className="text-amber-500" />,
                title: "Миттєвий Аналіз",
                desc: "Обчислення оптимальних квот для всіх заявників за частки секунди без людського фактору."
              }
            ].map((f, i) => (
              <div key={i} className="p-8 rounded-3xl border border-slate-100 hover:border-blue-100 hover:shadow-xl hover:shadow-blue-50 transition-all group">
                <div className="bg-slate-50 w-14 h-14 rounded-2xl flex items-center justify-center mb-6 group-hover:bg-blue-50 transition-colors">
                  {f.icon}
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-4">{f.title}</h3>
                <p className="text-slate-500 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* HOW IT WORKS SECTION */}
      <section className="py-24 bg-slate-900 text-white overflow-hidden relative">
        <div className="absolute top-0 left-0 w-full h-full opacity-10 pointer-events-none">
          <div className="absolute top-10 left-10 w-64 h-64 bg-blue-500 rounded-full blur-[100px]"></div>
          <div className="absolute bottom-10 right-10 w-64 h-64 bg-indigo-500 rounded-full blur-[100px]"></div>
        </div>

        <div className="max-w-7xl mx-auto px-8 relative z-10">
          <div className="flex flex-col md:flex-row justify-between items-end mb-16 gap-6">
            <div className="max-w-xl">
              <h2 className="text-4xl font-black mb-6">Алгоритм справедливості</h2>
              <p className="text-slate-400 font-medium">Ми автоматизували процес прийняття рішень, щоб виключити корупцію та помилки при розподілі ресурсів.</p>
            </div>
            <div className="hidden md:block">
              <span className="text-[100px] font-black text-white/5 leading-none select-none">STEP-BY-STEP</span>
            </div>
          </div>

          <div className="grid md:grid-cols-4 gap-12">
            {[
              { step: "01", title: "Реєстрація", desc: "Заявник подає запит із вказанням мети (Військові, ВПО, Медицина)." },
              { step: "02", title: "Пріоритезація", desc: "Система призначає ваговий коефіцієнт на основі категорії терміновості." },
              { step: "03", title: "Max-Min Розрахунок", desc: "Алгоритм обчислює оптимальну частку для кожного запиту при дефіциті." },
              { step: "04", title: "Видача", desc: "Формується автоматичний накладний лист для відвантаження зі складу." }
            ].map((s, i) => (
              <div key={i} className="relative">
                <div className="text-6xl font-black text-blue-500/20 mb-4">{s.step}</div>
                <h3 className="text-xl font-bold mb-3">{s.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{s.desc}</p>
                {i < 3 && <div className="hidden lg:block absolute top-8 -right-6 text-blue-500/30"><ArrowRight size={24}/></div>}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ SECTION */}
      <section className="py-32 bg-white">
        <div className="max-w-4xl mx-auto px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-black text-slate-900 mb-4">Часті запитання</h2>
            <div className="h-1 w-20 bg-blue-600 mx-auto rounded-full"></div>
          </div>

          <div className="space-y-6">
            {[
              {
                q: "Хто має найвищий пріоритет у системі?",
                a: "Найвищий коефіцієнт автоматично отримують запити для ЗСУ та екстреної медицини."
              },
              {
                q: "Як система бореться з дефіцитом?",
                a: "Якщо товару менше, ніж загальний запит, вмикається алгоритм розподілу Weighted Max-Min Fairness, який задовольняє мінімальні потреби кожного згідно з пріоритетом."
              },
              {
                q: "Чи можна змінити рішення системи вручну?",
                a: "Адміністратор може переглядати план, але алгоритм гарантує математичну обґрунтованість кожної операції, що мінімізує втручання."
              }
            ].map((item, i) => (
              <div key={i} className="p-6 rounded-2xl bg-slate-50 border border-slate-100 hover:border-blue-200 transition-colors">
                <h4 className="text-lg font-bold text-slate-900 mb-3 flex items-center gap-2">
                  <div className="w-1.5 h-1.5 bg-blue-600 rounded-full"></div>
                  {item.q}
                </h4>
                <p className="text-slate-500 text-sm ml-3.5 leading-relaxed">{item.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FINAL CTA SECTION */}
      <section className="pb-32 px-8">
        <div className="max-w-5xl mx-auto bg-gradient-to-r from-slate-900 to-blue-900 rounded-[2.5rem] p-12 md:p-20 text-center text-white relative overflow-hidden shadow-2xl shadow-blue-900/20">
          {/* Декоративна сітка */}
          <div className="absolute top-0 left-0 w-full h-full opacity-10">
            <div className="absolute top-[-50%] left-[-10%] w-[100%] h-[200%] bg-[radial-gradient(circle,white_1px,transparent_1px)] [background-size:30px_30px]"></div>
          </div>

          <h2 className="text-4xl md:text-5xl font-black mb-8 relative z-10 uppercase tracking-tight">
            Контроль. Прозорість. <br />
            <span className="text-blue-400">Результат.</span>
          </h2>

          <p className="text-slate-300 mb-10 max-w-2xl mx-auto font-medium relative z-10 text-lg leading-relaxed">
            Система доступна для верифікованих логістів та офіційних запитувачів.
            Авторизуйтесь для управління запасами або подання екстреної заявки на ресурси.
          </p>

          <div className="flex flex-col items-center justify-center gap-4 relative z-10">
            {/* КНОПКА */}
            <button
              onClick={onEnter}
              className="px-12 py-4 bg-blue-600 text-white font-black rounded-2xl hover:bg-blue-500 transition-all hover:scale-105 active:scale-95 shadow-xl shadow-blue-600/40"
            >
              УВІЙТИ В КАБІНЕТ
            </button>

            {/* ПРИМІТКА ПІД КНОПКОЮ */}
            <div className="text-slate-500 text-[10px] font-black uppercase tracking-[0.2em] mt-2 opacity-80">
              Тільки для верифікованих осіб
            </div>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="py-12 bg-slate-900 text-center">
        <div className="max-w-7xl mx-auto px-8">
          <div className="flex items-center justify-center gap-3 mb-6">
             {/* invert-0 або invert залежно від кольорів вашого лого,
                 якщо лого занадто темне — додаємо фільтр invert */}
             <img
               src={process.env.PUBLIC_URL + '/logo.ico'}
               alt="Logo"
               className="w-6 h-6 brightness-110 shadow-sm"
             />
             <span className="text-xl font-black tracking-tight text-white">
               ResQ <span className="text-blue-500">System</span>
             </span>
          </div>
          <p className="text-slate-400 text-sm">© 2026 ResQ Humanitarian Systems Ukraine. Всі права захищено.</p>
        </div>
      </footer>
    </div>
  );
};

export default Landing;