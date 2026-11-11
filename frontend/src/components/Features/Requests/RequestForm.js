import React, {useState, useEffect, useMemo} from 'react';
import {
    User, Package, Hash, Target, Plus, Trash2, Save,
    AlertCircle, CheckCircle2, Truck, Home, Calendar, RefreshCw
} from '../../UI/icons';
import {toast} from 'react-hot-toast';
import api, { extractErrorMessage } from '../../../services/api';

// Допоміжна функція для генерації дати за замовчуванням (Сьогодні + 5 днів)
const getFutureDate = (daysAhead = 5) => {
    const date = new Date();
    date.setDate(date.getDate() + daysAhead);
    return date.toISOString().split('T')[0];
};

const RequestForm = ({
                         usersList = [], resourcesList = [], stocks = [], purposes = [],
                         onClose, fetchData, currentUser
                     }) => {
    // --- СТАН ЛОКАЦІЇ ---
    const [cities, setCities] = useState([]);
    const [warehouses, setWarehouses] = useState([]);

    const [streets, setStreets] = useState([]);
    const [selectedStreet, setSelectedStreet] = useState(null);

    const [selectedCity, setSelectedCity] = useState(null);
    const [selectedWarehouse, setSelectedWarehouse] = useState(null);

    const [citySearch, setCitySearch] = useState('');
    const [streetSearch, setStreetSearch] = useState('');
    const [houseNumber, setHouseNumber] = useState('');

    const [showCityDropdown, setShowCityDropdown] = useState(false);
    const [showStreetDropdown, setShowStreetDropdown] = useState(false);

    const [langError, setLangError] = useState(false);

    const [isWarehousesLoading, setIsWarehousesLoading] = useState(false);
    const [isStreetsLoading, setIsStreetsLoading] = useState(false);

    const [deliveryType, setDeliveryType] = useState('warehouse');

    // --- FORM ---
    const [selectedUserId, setSelectedUserId] = useState('');
    const [dueDate, setDueDate] = useState(() => getFutureDate(5)); // Початковий стан: сьогодні + 5 днів
    const [autoExtend, setAutoExtend] = useState(true); // ❗ Новий стан для автопродовження
    const [isSubmitting, setIsSubmitting] = useState(false);

    const [formRows, setFormRows] = useState([
        {
            id: Date.now(),
            resource: '',
            quantity: '',
            purpose: ''
        }
    ]);

    // Значення поточної дати для обмеження вибору "минулих" дат у календарі
    const todayStr = useMemo(() => new Date().toISOString().split('T')[0], []);

    // Перевірка чи доступна доставка в місто (чи є там відділення)
    const isDeliveryAvailable = useMemo(() => {
        if (!selectedCity) return true;
        return warehouses.length > 0 || isWarehousesLoading;
    }, [selectedCity, warehouses, isWarehousesLoading]);

    // --- ПОШУК МІСТ ---
    const handleCityInput = (val) => {
        setCitySearch(val);
        const isEnglish = /[a-zA-Z]/.test(val);
        setLangError(isEnglish);
        if (isEnglish) setShowCityDropdown(false);
        setSelectedCity(null);
        setWarehouses([]);
    };

    const handleStreetInput = (val) => {
        setStreetSearch(val);
        setSelectedStreet(null); // Скидаємо об'єкт вибору, якщо користувач знову почав редагувати текст
    };

    const fetchCities = async (search) => {
        if (search.length < 2 || langError) return;
        try {
            const response = await api.post('/novaposhta/', {action: 'get_cities', search});
            setCities(Array.isArray(response.data) ? response.data : []);
            setShowCityDropdown(true);
        } catch (err) {
            console.error(err);
        }
    };

    const fetchCityDetails = async (city) => {
        // Зберігаємо оригінальні поля міста (включно з Ref та SettlementRef для пошуку вулиць)
        const cityBase = {...city};
        try {
            const response = await api.post('/novaposhta/', {
                action: 'get_warehouses',
                city_ref: city.SettlementRef || city.Ref
            });
            if (response.data && response.data.length > 0) {
                const centerData = response.data[0];
                setSelectedCity({
                    ...cityBase,
                    Latitude: centerData.Latitude,
                    Longitude: centerData.Longitude
                });
            } else {
                setSelectedCity(cityBase);
            }
        } catch (err) {
            setSelectedCity(cityBase);
        }
    };

    const fetchWarehouses = async (cityRef) => {
        if (!cityRef) return;
        setIsWarehousesLoading(true);
        try {
            const response = await api.post('/novaposhta/', {action: 'get_warehouses', city_ref: cityRef});
            const data = Array.isArray(response.data) ? response.data : [];
            setWarehouses(data);
            if (data.length === 0) setDeliveryType('warehouse');
        } catch (err) {
            setWarehouses([]);
        } finally {
            setIsWarehousesLoading(false);
        }
    };

    // ---------------- FETCH STREETS ----------------

    const fetchStreets = async (cityRef, search) => {
        if (!cityRef || search.length < 2) return;
        setIsStreetsLoading(true);

        try {
            const response = await api.post('/novaposhta/', {
                action: 'get_streets',
                city_ref: cityRef,
                search
            });

            console.log('STREETS RAW FROM BACKEND:', response.data);

            const data = Array.isArray(response.data)
                ? response.data.filter(s => s && (s.Description || s.Presentation))
                : [];

            setStreets(data);
            setShowStreetDropdown(true);
        } catch (err) {
            console.error(err);
            setStreets([]);
            setShowStreetDropdown(false);
        } finally {
            setIsStreetsLoading(false);
        }
    };

    useEffect(() => {
        const timer = setTimeout(() => {
            if (citySearch && !selectedCity && !langError) fetchCities(citySearch);
        }, 500);
        return () => clearTimeout(timer);
    }, [citySearch, selectedCity, langError]);

    useEffect(() => {
        if (selectedCity) {
            fetchWarehouses(selectedCity.SettlementRef || selectedCity.Ref);
        }
    }, [selectedCity]);

    useEffect(() => {
        const timer = setTimeout(() => {
            if (
                deliveryType === 'address' &&
                selectedCity &&
                streetSearch.length >= 2 &&
                !selectedStreet
            ) {
                // НП searchSettlementStreets очікує SettlementRef (Ref самого населеного пункту)
                // searchSettlements повертає: Ref (Ref населеного пункту) та SettlementRef (може бути Ref батьківського)
                // Для вулиць завжди використовуємо Ref або SettlementRef в правильному порядку
                const cityUuid = selectedCity.Ref || selectedCity.SettlementRef || selectedCity.DeliveryCity;
                if (cityUuid) {
                    fetchStreets(cityUuid, streetSearch);
                } else {
                    console.warn("У вибраного міста відсутній Ref/SettlementRef!", selectedCity);
                }
            }
        }, 400);
        return () => clearTimeout(timer);
    }, [streetSearch, selectedCity, deliveryType, selectedStreet]);

    const availabilityMap = useMemo(() => {
        return stocks.reduce((acc, s) => {
            acc[s.resource] = (acc[s.resource] || 0) + parseFloat(s.amount);
            return acc;
        }, {});
    }, [stocks]);

    const handleFormChange = (index, field, value) => {
        const newRows = [...formRows];
        if (field === 'quantity') {
            const cleanValue = value.replace(/[^0-9]/g, '');
            newRows[index][field] = cleanValue;
        } else {
            newRows[index][field] = value;
        }
        setFormRows(newRows);
    };

    const handleSubmit = async () => {
        // 1. Перевірка заявника для адміна
        if (currentUser?.is_admin && !selectedUserId) {
            toast.dismiss();
            return toast.error("Оберіть заявника зі списку (для кого створюється заявка)", { id: 'req-form-toast' });
        }
        const targetUserId = selectedUserId || currentUser?.id;
        if (!targetUserId) {
            toast.dismiss();
            return toast.error("Не вдалося визначити заявника. Оберіть користувача зі списку", { id: 'req-form-toast' });
        }

        // 2. Перевірка терміну виконання
        if (!dueDate) {
            toast.dismiss();
            return toast.error("Вкажіть термін виконання (поле 'Виконати до')", { id: 'req-form-toast' });
        }
        if (dueDate < todayStr) {
            toast.dismiss();
            return toast.error("Граничний термін виконання не може бути у минулому", { id: 'req-form-toast' });
        }

        // 3. Перевірка міста
        if (!selectedCity) {
            toast.dismiss();
            if (citySearch && citySearch.trim().length > 0) {
                return toast.error("Оберіть місто зі списку підказок під полем вводу", { id: 'req-form-toast' });
            }
            return toast.error("Вкажіть та оберіть місто зі списку", { id: 'req-form-toast' });
        }
        if (!isDeliveryAvailable) {
            toast.dismiss();
            return toast.error("Доставка в цей населений пункт тимчасово недоступна", { id: 'req-form-toast' });
        }

        // 4. Перевірка способу отримання
        const isAddressMode = deliveryType === 'address';
        if (isAddressMode) {
            if (!streetSearch || !streetSearch.trim()) {
                toast.dismiss();
                return toast.error("Вкажіть назву вулиці для адресної доставки", { id: 'req-form-toast' });
            }
            if (!houseNumber || !houseNumber.trim()) {
                toast.dismiss();
                return toast.error("Вкажіть номер будинку", { id: 'req-form-toast' });
            }
        } else {
            if (!selectedWarehouse || !selectedWarehouse.Ref) {
                toast.dismiss();
                return toast.error("Оберіть відділення Нової Пошти зі списку", { id: 'req-form-toast' });
            }
        }

        const finalAddress = isAddressMode
            ? `вул. ${streetSearch.trim()}, буд. ${houseNumber.trim()}`
            : selectedWarehouse?.Description;

        if (!finalAddress) {
            toast.dismiss();
            return toast.error("Вкажіть коректну адресу отримання", { id: 'req-form-toast' });
        }

        // 5. Перевірка позицій ресурсів
        if (!formRows || formRows.length === 0) {
            toast.dismiss();
            return toast.error("Додайте хоча б один ресурс до заявки", { id: 'req-form-toast' });
        }

        for (let i = 0; i < formRows.length; i++) {
            const row = formRows[i];
            const num = formRows.length > 1 ? ` (позиція #${i + 1})` : '';

            if (!row.resource) {
                toast.dismiss();
                return toast.error(`Оберіть ресурс зі списку${num}`, { id: 'req-form-toast' });
            }
            const qty = parseInt(row.quantity, 10);
            if (!row.quantity || isNaN(qty) || qty <= 0) {
                toast.dismiss();
                return toast.error(`Вкажіть кількість більше нуля${num}`, { id: 'req-form-toast' });
            }
            if (!row.purpose) {
                toast.dismiss();
                return toast.error(`Оберіть ціль призначення${num}`, { id: 'req-form-toast' });
            }
        }

        setIsSubmitting(true);
        try {
            await Promise.all(formRows.map(row => api.post('/requests/', {
                resource: parseInt(row.resource, 10),
                quantity_requested: parseInt(row.quantity, 10),
                purpose: parseInt(row.purpose, 10),
                user: targetUserId,
                city: selectedCity.Present || selectedCity.Description,
                warehouse_address: finalAddress,
                warehouse_ref: isAddressMode ? 'ADDRESS_DELIVERY' : selectedWarehouse?.Ref,
                latitude: isAddressMode ? (selectedCity?.Latitude || null) : (selectedWarehouse?.Latitude || null),
                longitude: isAddressMode ? (selectedCity?.Longitude || null) : (selectedWarehouse?.Longitude || null),
                due_date: dueDate,
                auto_extend: Boolean(autoExtend)
            }, { _suppressToast: true })));

            toast.dismiss();
            toast.success("Заявку успішно створено!", { id: 'req-form-toast' });
            if (typeof fetchData === 'function') fetchData();
            if (typeof onClose === 'function') onClose();
        } catch (err) {
            toast.dismiss();
            const errorText = extractErrorMessage(err, "Помилка при збереженні заявки");
            toast.error(errorText, { id: 'req-form-toast' });
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="space-y-6 text-left relative">

            {/* 1. СТРУКТУРНИЙ БЛОК: АДМІНІСТРУВАННЯ ТА ТЕРМІНОВІСТЬ */}
            <div className="grid grid-cols-1 gap-4">
                {/* ЗАЯВНИК — Тільки для admin */}
                {currentUser?.is_admin && (
                    <div className="bg-blue-50/40 p-5 rounded-2xl border border-blue-100 shadow-sm flex flex-col justify-between gap-3">
                        <label
                            className="text-[10px] font-black uppercase text-blue-500 italic block tracking-widest">1.
                            Оберіть заявника (Admin)</label>
                        <div className="flex items-center gap-3">
                            <div className="bg-blue-600 p-2.5 rounded-xl text-white shadow-lg shadow-blue-100"><User
                                size={20}/></div>
                            <select
                                value={selectedUserId || ''}
                                onChange={(e) => setSelectedUserId(e.target.value)}
                                className="w-full px-4 py-2.5 bg-white border border-blue-100 rounded-xl font-bold text-sm outline-none focus:ring-2 focus:ring-blue-500/20"
                            >
                                <option value="">Виберіть користувача зі списку...</option>
                                {usersList.map(u => <option key={u.id}
                                                            value={u.id}>{u.full_name || u.username}</option>)}
                            </select>
                        </div>
                    </div>
                )}

                {/* ГРАНИЧНИЙ ТЕРМІН ВИКОНАННЯ ТА АВТОПРОДОВЖЕННЯ */}
                <div
                    className={`bg-amber-50/40 p-5 rounded-2xl border border-amber-100 shadow-sm flex flex-col justify-between gap-3 `}>
                    <div>
                        <label
                            className="text-[10px] font-black uppercase text-amber-600 italic mb-2 block tracking-widest">
                            {currentUser?.is_admin ? '1.1' : '1.'} Виконати до
                        </label>
                        <div className="flex items-center gap-2">
                            <div className="bg-amber-500 p-2.5 rounded-xl text-white shadow-lg shadow-amber-100">
                                <Calendar size={20}/></div>
                            <input
                                type="date"
                                value={dueDate}
                                min={todayStr}
                                onChange={(e) => setDueDate(e.target.value)}
                                className="w-full px-3 py-2 bg-white border border-amber-100 rounded-xl font-black text-xs text-slate-700 outline-none focus:ring-2 focus:ring-amber-500/20"
                            />
                        </div>
                    </div>

                    {/* ІНТЕРАКТИВНИЙ ЧЕКБОКС АВТОПРОДОВЖЕННЯ */}
                    <label
                        className="flex items-center gap-2.5 cursor-pointer bg-white/60 p-2 rounded-xl border border-amber-200/50 hover:bg-white transition-all select-none">
                        <input
                            type="checkbox"
                            checked={autoExtend}
                            onChange={(e) => setAutoExtend(e.target.checked)}
                            className="w-4 h-4 text-amber-600 border-amber-300 rounded focus:ring-amber-500/20 focus:ring-2 accent-amber-500"
                        />
                        <div className="flex flex-col text-left">
                            <span
                                className="text-[10px] font-black text-amber-900 uppercase leading-none mb-0.5 flex items-center gap-1">
                                <RefreshCw size={10} className={autoExtend ? "animate-spin-slow" : ""}/> Автопродовження
                            </span>
                            <span className="text-[9px] font-medium text-slate-400 leading-none">Продовжити на +5 днів у разі дефіциту</span>
                        </div>
                    </label>
                </div>
            </div>

            {/* 2. ЛОКАЦІЯ ТА ДОСТАВКА */}
            <div className="bg-slate-50 p-5 rounded-3xl border border-slate-200 space-y-4 shadow-inner">
                <label className="text-[10px] font-black uppercase text-slate-400 italic block tracking-widest">
                    {currentUser?.is_admin ? '2.' : '2.'} Локація та доставка
                </label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="relative">
                        <label className="text-[9px] font-bold uppercase text-slate-500 mb-1 ml-1 block">Місто</label>
                        <input type="text" value={citySearch || ''}
                               onChange={(e) => {
                                   handleCityInput(e.target.value);
                                   setSelectedCity(null);
                               }}
                               placeholder="Пошук міста..."
                               className="w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl font-bold text-sm outline-none focus:border-blue-400 transition-all"/>
                        {showCityDropdown && !selectedCity && cities.length > 0 && (
                            <div
                                className="absolute left-0 right-0 z-[9999] mt-1 max-h-52 overflow-y-auto bg-white border-2 border-blue-100 rounded-xl shadow-xl">
                                {cities.map((city, idx) => (
                                    <div key={idx}
                                         className="px-4 py-3 hover:bg-blue-50 cursor-pointer text-sm font-bold border-b last:border-none"
                                         onClick={() => {
                                             setCitySearch(city.Present || city.Description);
                                             setShowCityDropdown(false);
                                             fetchCityDetails(city);
                                         }}>
                                        {city.Present || city.Description}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                    <div>
                        <label className="text-[9px] font-bold uppercase text-slate-500 mb-1 ml-1 block">Спосіб
                            отримання</label>
                        <div className="flex bg-white p-1 rounded-xl border border-slate-200 h-[42px]">
                            <button type="button" onClick={() => setDeliveryType('warehouse')}
                                    className={`flex-1 flex items-center justify-center gap-2 rounded-lg text-[10px] font-black uppercase transition-all ${deliveryType === 'warehouse' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400'}`}>
                                <Truck size={14}/>Відділення
                            </button>
                            <button
                                type="button"
                                disabled={!isDeliveryAvailable}
                                onClick={() => setDeliveryType('address')}
                                className={`flex-1 flex items-center justify-center gap-2 rounded-lg text-[10px] font-black uppercase transition-all ${deliveryType === 'address' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400'} disabled:opacity-30 disabled:grayscale disabled:cursor-not-allowed`}
                                title={!isDeliveryAvailable ? "Адресна доставка неможлива" : ""}
                            >
                                <Home size={14}/>Адреса
                            </button>
                        </div>
                    </div>
                </div>

                <div className="bg-white/50 p-4 rounded-2xl border border-slate-100">
                    {!isDeliveryAvailable && selectedCity ? (
                        <div
                            className="p-4 bg-red-50 border-2 border-dashed border-red-200 rounded-2xl flex flex-col items-center text-center gap-2 text-red-600 animate-in fade-in slide-in-from-top-2 duration-500">
                            <AlertCircle size={24}/>
                            <div>
                                <p className="text-xs font-black uppercase tracking-wider">Логістичне обмеження</p>
                                <p className="text-[11px] font-bold opacity-80 uppercase mt-1">Доставка в цей населений
                                    пункт тимчасово недоступна. Будь ласка, оберіть інше місто.</p>
                            </div>
                        </div>
                    ) : (
                        deliveryType === 'warehouse' ? (
                            <div className="space-y-2">
                                <label className="text-[9px] font-bold text-slate-500 uppercase">Оберіть
                                    відділення</label>
                                <select
                                    disabled={!selectedCity || isWarehousesLoading}
                                    value={selectedWarehouse?.Ref || ''}
                                    onChange={(e) => setSelectedWarehouse(warehouses.find(w => w.Ref === e.target.value))}
                                    className="w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl font-bold text-sm outline-none disabled:bg-slate-50"
                                >
                                    <option value="">
                                        {isWarehousesLoading ? "Завантаження списку..." : (selectedCity ? "Оберіть зі списку..." : "Спочатку вкажіть місто")}
                                    </option>
                                    {warehouses.map((w, idx) => <option key={idx}
                                                                        value={w.Ref}>{w.Description}</option>)}
                                </select>
                            </div>
                        ) : (
                            /* АДРЕСНА ДОСТАВКА З ВИПАДАЮЧИМ МЕНЮ ВУЛИЦЬ */
                            <div
                                className="grid grid-cols-1 sm:grid-cols-3 gap-3 animate-in slide-in-from-top-2 duration-300 relative">
                                <div className="sm:col-span-2 relative">
                                    <label
                                        className="text-[9px] font-bold text-slate-500 uppercase mb-1 block ml-1">Вулиця</label>
                                    <input
                                        type="text"
                                        value={streetSearch}
                                        disabled={!selectedCity}
                                        onChange={(e) => handleStreetInput(e.target.value)}
                                        placeholder={selectedCity ? "Почніть вводити..." : "Спочатку оберіть місто"}
                                        className="w-full px-4 py-2 bg-white border border-slate-200 rounded-xl font-bold text-sm outline-none focus:border-blue-400 disabled:bg-slate-50"
                                    />

                                    {/* ШВИДКИЙ ЛОАДЕР ВУЛИЦЬ */}
                                    {isStreetsLoading && (
                                        <div
                                            className="absolute right-3 top-9 text-[10px] text-blue-500 font-bold animate-pulse">Пошук...</div>
                                    )}

                                    {/* ДРОПДАУН ВУЛИЦЬ */}
                                    {showStreetDropdown && selectedCity && !selectedStreet && (
                                        <div
                                            className="absolute left-0 right-0 z-[99999] mt-1 max-h-56 overflow-y-auto bg-white border-2 border-blue-100 rounded-xl shadow-2xl">
                                            {streets.length === 0 ? (
                                                <div className="px-4 py-3 text-sm text-gray-400">Нічого не
                                                    знайдено</div>
                                            ) : (
                                                streets.map((street, idx) => {
                                                    const streetName = street.Presentation || street.Description;
                                                    return (
                                                        <div
                                                            key={idx}
                                                            className="px-4 py-3 hover:bg-blue-50 cursor-pointer text-sm font-bold border-b last:border-none text-left"
                                                            onClick={() => {
                                                                setStreetSearch(streetName);
                                                                setSelectedStreet(street);
                                                                setShowStreetDropdown(false);
                                                            }}
                                                        >
                                                            {streetName}
                                                        </div>
                                                    );
                                                })
                                            )}
                                        </div>
                                    )}
                                </div>

                                {/* БУДИНОК */}
                                <div>
                                    <label
                                        className="text-[9px] font-bold text-slate-500 uppercase mb-1 block ml-1">Будинок</label>
                                    <input
                                        type="text"
                                        value={houseNumber}
                                        onChange={(e) => setHouseNumber(e.target.value)}
                                        placeholder="№"
                                        className="w-full px-4 py-2 bg-white border border-slate-200 rounded-xl font-bold text-sm outline-none focus:border-blue-400"
                                    />
                                </div>
                            </div>
                        )
                    )}
                </div>
            </div>

            {/* 3. ПЕРЕЛІК РЕСУРСІВ */}
            <div className="space-y-4">
                <label className="text-[10px] font-black uppercase text-slate-400 italic block tracking-widest">
                    3. Перелік ресурсів
                </label>
                {formRows.map((row, index) => {
                    const availableCount = availabilityMap[row.resource] || 0;

                    // Шукаємо вибраний ресурс у списку, щоб отримати його одиницю виміру
                    const selectedResourceObj = resourcesList.find(r => r.id === parseInt(row.resource));
                    const unitSuffix = selectedResourceObj?.unit_name || selectedResourceObj?.unit || 'од.';

                    return (
                        <div key={row.id}
                             className="bg-white p-4 sm:p-5 rounded-2xl border hover:border-blue-100 transition-all shadow-sm">
                            <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-end">
                                <div className="flex-1 w-full text-left">
                                    <label
                                        className="text-[10px] font-bold text-slate-400 uppercase block mb-1 ml-1"><Package
                                        size={12} className="inline mr-1"/>Ресурс</label>
                                    <select value={row.resource || ''}
                                            onChange={(e) => handleFormChange(index, 'resource', e.target.value)}
                                            className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm font-bold outline-none">
                                        <option value="">Оберіть ресурс...</option>
                                        {resourcesList.map(r => {
                                            const rUnit = r.unit_name || r.unit;
                                            return (
                                                <option key={r.id} value={r.id}>
                                                    {r.name} {rUnit ? `(${rUnit})` : ''}
                                                </option>
                                            );
                                        })}
                                    </select>
                                </div>
                                <div className="w-full sm:w-28 text-left">
                                    <label
                                        className="text-[10px] font-bold text-slate-400 uppercase block mb-1 ml-1"><Hash
                                        size={12} className="inline mr-1"/>К-сть</label>
                                    <input type="text" inputMode="numeric" value={row.quantity || ''}
                                           onKeyDown={(e) => {
                                               if (['.', ',', 'e', 'E', '+', '-'].includes(e.key)) e.preventDefault();
                                           }}
                                           onChange={(e) => handleFormChange(index, 'quantity', e.target.value)}
                                           placeholder="0"
                                           className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm font-black outline-none text-center"/>
                                </div>
                                <div className="flex-1 w-full text-left">
                                    <label
                                        className="text-[10px] font-bold text-slate-400 uppercase block mb-1 ml-1"><Target
                                        size={12} className="inline mr-1"/>Ціль</label>
                                    <select value={row.purpose || ''}
                                            onChange={(e) => handleFormChange(index, 'purpose', e.target.value)}
                                            className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm font-medium outline-none">
                                        <option value="">Ціль...</option>
                                        {purposes.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                                    </select>
                                </div>
                                {formRows.length > 1 && (
                                    <div className="flex justify-end sm:self-end">
                                        <button onClick={() => setFormRows(formRows.filter(r => r.id !== row.id))}
                                                className="text-slate-400 hover:text-red-500 p-2 transition-colors flex items-center gap-1 text-xs font-bold"
                                                aria-label="Видалити позицію">
                                            <Trash2 size={18}/>
                                            <span className="sm:hidden text-xs">Видалити</span>
                                        </button>
                                    </div>
                                )}
                            </div>

                            {/* ПІДКАЗКИ ЗНИЗУ */}
                            {row.resource && (
                                currentUser?.is_admin ? (
                                    /* Повна інформація для Адміна */
                                    <div
                                        className={`mt-3 px-3 py-1.5 rounded-lg text-[10px] font-black uppercase flex items-center gap-2 ${availableCount > 0 ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'}`}>
                                        {availableCount > 0 ? <CheckCircle2 size={12}/> : <AlertCircle size={12}/>}
                                        {availableCount > 0 ? `На складі: ${availableCount.toFixed(0)} ${unitSuffix}` : 'На даний момент немає на складах'}
                                    </div>
                                ) : (
                                    /* Чиста підказка одиниці виміру для Волонтера */
                                    <div
                                        className="mt-3 px-3 py-1.5 rounded-lg text-[10px] font-black uppercase flex items-center gap-2 bg-slate-50 text-slate-500">
                                        <CheckCircle2 size={12} className="text-blue-500"/>
                                        Вимірюється в: {unitSuffix}
                                    </div>
                                )
                            )}
                        </div>
                    );
                })}
            </div>

            <button type="button" onClick={() => setFormRows([...formRows, {
                id: Date.now(),
                resource: '',
                quantity: '',
                purpose: ''
            }])}
                    className="flex items-center gap-2 text-blue-600 font-black text-[10px] uppercase tracking-widest hover:bg-blue-50 px-6 py-4 rounded-2xl border-2 border-dashed border-blue-100 w-full justify-center transition-all active:scale-95">
                <Plus size={16}/> Додати ще одну позицію
            </button>

            <div className="flex flex-col-reverse sm:flex-row gap-3 justify-end pt-4 border-t border-slate-100">
                <button type="button" onClick={onClose}
                        className="w-full sm:w-auto px-6 py-3 text-slate-400 font-bold hover:text-slate-600 transition-colors text-center text-sm">
                    Скасувати
                </button>
                <button type="button" onClick={handleSubmit} disabled={isSubmitting || !isDeliveryAvailable}
                        className="w-full sm:w-auto px-8 py-3.5 bg-blue-600 text-white font-black rounded-2xl hover:bg-slate-900 shadow-xl shadow-blue-200 active:scale-95 transition-all disabled:bg-slate-300 disabled:shadow-none flex items-center justify-center gap-2 text-sm">
                    {isSubmitting ? "ЗБЕРЕЖЕННЯ..." :
                        <><Save size={18}/><span>ЗБЕРЕГТИ ЗАЯВКУ</span></>}
                </button>
            </div>
        </div>
    );
};

export default RequestForm;