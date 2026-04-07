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
        <div className="flex items-center gap-2">
          <div className="bg-blue-600 p-2 rounded-lg">
            <Zap className="text-white" size={20} />
          </div>
          <span className="text-xl font-black tracking-tight">ResQ <span className="text-blue-600">System</span></span>
        </div>
        <button
          onClick={onEnter}
          className="text-sm font-bold bg-slate-900 text-white px-6 py-2.5 rounded-full hover:bg-slate-800 transition-all"
        >
          Увійти в кабінет
        </button>
      </nav>

      {/* HERO SECTION */}
      <header className="relative pt-16 pb-32 overflow-hidden">
        <div className="max-w-7xl mx-auto px-8 grid lg:grid-cols-2 gap-12 items-center">
          <div className="relative z-10">
            <span className="inline-block px-4 py-1.5 bg-blue-50 text-blue-600 rounded-full text-xs font-black uppercase tracking-widest mb-6">
              Platform v3.0
            </span>
            <h1 className="text-6xl lg:text-7xl font-black text-slate-900 leading-[1.1] mb-8">
              Оптимізація <br />
              <span className="text-blue-600">критичних</span> ресурсів.
            </h1>
            <p className="text-lg text-slate-500 max-w-lg mb-10 leading-relaxed">
              Інтелектуальна система підтримки прийняття рішень для розподілу обмежених ресурсів на основі матриці пріоритетів та Weighted Max-Min Fairness.
            </p>
            <div className="flex flex-wrap gap-4">
              <button
                onClick={onEnter}
                className="group flex items-center gap-3 px-8 py-4 bg-blue-600 text-white font-bold rounded-2xl hover:bg-blue-700 shadow-xl shadow-blue-200 transition-all hover:-translate-y-1"
              >
                Почати розподіл
                <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          </div>

          <div className="relative">
            <div className="absolute -inset-4 bg-blue-400/20 blur-3xl rounded-full"></div>
            <div className="relative bg-white border border-slate-200 rounded-3xl shadow-2xl p-4 overflow-hidden transform rotate-2">
               <img
                 src="https://images.unsplash.com/photo-1582139329536-e7284fece509?auto=format&fit=crop&q=80&w=800"
                 alt="Dashboard Preview"
                 className="rounded-2xl"
               />
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
              <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">Точність алгоритму</div>
            </div>
          </div>
        </div>
      </section>

      {/* FEATURES SECTION */}
      <section className="py-32">
        <div className="max-w-7xl mx-auto px-8">
          <div className="text-center max-w-2xl mx-auto mb-20">
            <h2 className="text-4xl font-black text-slate-900 mb-6">Чому обирають ResQ?</h2>
            <p className="text-slate-500 font-medium">Система розроблена для вирішення проблеми дефіциту під час гуманітарних криз.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: <BarChart3 className="text-blue-600" />,
                title: "Матриця Пріоритетів",
                desc: "Військові потреби та медицина отримують найвищий коефіцієнт в алгоритмі автоматично."
              },
              {
                icon: <ShieldCheck className="text-emerald-600" />,
                title: "Прозорий Облік",
                desc: "Кожна одиниця товару відстежується від моменту приходу на склад до видачі заявнику."
              },
              {
                icon: <Zap className="text-amber-500" />,
                title: "Миттєвий Розподіл",
                desc: "Обчислення складних математичних моделей за частки секунди замість годин ручної роботи."
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

      {/* FOOTER */}
      <footer className="py-12 border-t border-slate-100 text-center">
        <p className="text-slate-400 text-sm">© 2026 ResQ Humanitarian Systems. Всі права захищено.</p>
      </footer>
    </div>
  );
};

export default Landing;