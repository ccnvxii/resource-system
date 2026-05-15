import React, {useState, useEffect, useMemo} from 'react';
import {
    User, Package, Hash, Target, Plus, Trash2, Save,
    AlertCircle, CheckCircle2, MapPin, Truck, Map as MapIcon, X, Home
} from 'lucide-react';
import {toast} from 'react-hot-toast';
import api from '../../services/api';

const RequestForm = ({
                         usersList = [], resourcesList = [], stocks = [], purposes = [],
                         onClose, fetchData, currentUser
                     }) => {
    // --- СТАН ЛОКАЦІЇ ---
    const [cities, setCities] = useState([]);
    const [warehouses, setWarehouses] = useState([]);
    const [selectedCity, setSelectedCity] = useState(null);
    const [selectedWarehouse, setSelectedWarehouse] = useState(null);

    const [citySearch, setCitySearch] = useState('');
    const [streetSearch, setStreetSearch] = useState('');
    const [houseNumber, setHouseNumber] = useState('');

    const [showCityDropdown, setShowCityDropdown] = useState(false);
    const [langError, setLangError] = useState(false);
    const [isWarehousesLoading, setIsWarehousesLoading] = useState(false);

    const [deliveryType, setDeliveryType] = useState('warehouse');

    // --- СТАН ФОРМИ ---
    const [selectedUserId, setSelectedUserId] = useState('');
    const [formRows, setFormRows] = useState([{id: Date.now(), resource: '', quantity: '', purpose: ''}]);
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Перевірка чи доступна доставка в місто (чи є там відділення)
    const isDeliveryAvailable = useMemo(() => {
        if (!selectedCity) return true; // Поки не вибрано місто — не лякаємо користувача
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

    const fetchCities = async (search) => {
        if (search.length < 2 || langError) return;
        try {
            const response = await api.post('/novaposhta/', {action: 'get_cities', search});
            setCities(Array.isArray(response.data) ? response.data : []);
            setShowCityDropdown(true);
        } catch (err) { console.error(err); }
    };

    const fetchCityDetails = async (city) => {
        try {
            const response = await api.post('/novaposhta/', {
                action: 'get_warehouses',
                city_ref: city.SettlementRef || city.Ref
            });
            if (response.data && response.data.length > 0) {
                const centerData = response.data[0];
                setSelectedCity({
                    ...city,
                    Latitude: centerData.Latitude,
                    Longitude: centerData.Longitude
                });
            } else {
                setSelectedCity(city);
            }
        } catch (err) { setSelectedCity(city); }
    };

    const fetchWarehouses = async (cityRef) => {
        if (!cityRef) return;
        setIsWarehousesLoading(true);
        try {
            const response = await api.post('/novaposhta/', {action: 'get_warehouses', city_ref: cityRef});
            const data = Array.isArray(response.data) ? response.data : [];
            setWarehouses(data);
            // Якщо відділень немає — примусово ставимо тип warehouse (щоб не вибирали адресу)
            if (data.length === 0) setDeliveryType('warehouse');
        } catch (err) {
            setWarehouses([]);
        } finally {
            setIsWarehousesLoading(false);
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
        if (!selectedCity) return toast.error("Оберіть місто зі списку");
        if (!isDeliveryAvailable) return toast.error("Доставка в цей населений пункт неможлива");

        const isAddressMode = deliveryType === 'address';
        const finalAddress = isAddressMode
            ? (streetSearch && houseNumber ? `вул. ${streetSearch}, буд. ${houseNumber}` : null)
            : selectedWarehouse?.Description;

        if (!finalAddress) return toast.error("Вкажіть конкретну точку отримання");

        setIsSubmitting(true);
        try {
            await Promise.all(formRows.map(row => api.post('/requests/', {
                resource: parseInt(row.resource),
                quantity_requested: parseInt(row.quantity),
                purpose: parseInt(row.purpose),
                user: selectedUserId || currentUser?.id,
                city: selectedCity.Present || selectedCity.Description,
                warehouse_address: finalAddress,
                warehouse_ref: isAddressMode ? 'ADDRESS_DELIVERY' : selectedWarehouse?.Ref,
                latitude: isAddressMode ? selectedCity?.Latitude : selectedWarehouse?.Latitude,
                longitude: isAddressMode ? selectedCity?.Longitude : selectedWarehouse?.Longitude
            })));
            toast.success("Заявку успішно створено!");
            fetchData();
            onClose();
        } catch (err) { toast.error("Помилка при збереженні"); }
        finally { setIsSubmitting(false); }
    };

    return (
        <div className="space-y-6 text-left relative">

            {/* 1. ЗАЯВНИК — Тільки для адміна */}
            {currentUser?.is_admin && (
                <div className="bg-blue-50/40 p-5 rounded-2xl border border-blue-100 shadow-sm">
                    <label className="text-[10px] font-black uppercase text-blue-500 italic mb-2 block tracking-widest">1. Оберіть заявника (Admin)</label>
                    <div className="flex items-center gap-3">
                        <div className="bg-blue-600 p-2.5 rounded-xl text-white shadow-lg shadow-blue-100"><User size={20}/></div>
                        <select
                            value={selectedUserId || ''}
                            onChange={(e) => setSelectedUserId(e.target.value)}
                            className="w-full px-4 py-2.5 bg-white border border-blue-100 rounded-xl font-bold text-sm outline-none focus:ring-2 focus:ring-blue-500/20"
                        >
                            <option value="">Виберіть користувача зі списку...</option>
                            {usersList.map(u => <option key={u.id} value={u.id}>{u.full_name || u.username}</option>)}
                        </select>
                    </div>
                </div>
            )}

            {/* 2. ЛОКАЦІЯ ТА ДОСТАВКА */}
            <div className="bg-slate-50 p-5 rounded-3xl border border-slate-200 space-y-4 shadow-inner">
                <label className="text-[10px] font-black uppercase text-slate-400 italic block tracking-widest">
                    {currentUser?.is_admin ? '2.' : '1.'} Локація та доставка
                </label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="relative">
                        <label className="text-[9px] font-bold uppercase text-slate-500 mb-1 ml-1 block">Місто</label>
                        <input type="text" value={citySearch || ''}
                            onChange={(e) => { handleCityInput(e.target.value); setSelectedCity(null); }}
                            placeholder="Пошук міста..." className="w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl font-bold text-sm outline-none focus:border-blue-400 transition-all"/>
                        {showCityDropdown && !selectedCity && cities.length > 0 && (
                            <div className="absolute left-0 right-0 z-[9999] mt-1 max-h-52 overflow-y-auto bg-white border-2 border-blue-100 rounded-xl shadow-xl">
                                {cities.map((city, idx) => (
                                    <div key={idx} className="px-4 py-3 hover:bg-blue-50 cursor-pointer text-sm font-bold border-b last:border-none"
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
                        <label className="text-[9px] font-bold uppercase text-slate-500 mb-1 ml-1 block">Спосіб отримання</label>
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
                        <div className="p-4 bg-red-50 border-2 border-dashed border-red-200 rounded-2xl flex flex-col items-center text-center gap-2 text-red-600 animate-in fade-in slide-in-from-top-2 duration-500">
                            <AlertCircle size={24} />
                            <div>
                                <p className="text-xs font-black uppercase tracking-wider">Логістичне обмеження</p>
                                <p className="text-[11px] font-bold opacity-80 uppercase mt-1">Доставка в цей населений пункт тимчасово недоступна. Будь ласка, оберіть інше місто.</p>
                            </div>
                        </div>
                    ) : (
                        deliveryType === 'warehouse' ? (
                            <div className="space-y-2">
                                <label className="text-[9px] font-bold text-slate-500 uppercase">Оберіть відділення</label>
                                <select
                                    disabled={!selectedCity || isWarehousesLoading}
                                    value={selectedWarehouse?.Ref || ''}
                                    onChange={(e) => setSelectedWarehouse(warehouses.find(w => w.Ref === e.target.value))}
                                    className="w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl font-bold text-sm outline-none disabled:bg-slate-50"
                                >
                                    <option value="">
                                        {isWarehousesLoading ? "Завантаження списку..." : (selectedCity ? "Оберіть зі списку..." : "Спочатку вкажіть місто")}
                                    </option>
                                    {warehouses.map((w, idx) => <option key={idx} value={w.Ref}>{w.Description}</option>)}
                                </select>
                            </div>
                        ) : (
                            <div className="grid grid-cols-3 gap-3 animate-in slide-in-from-top-2 duration-300">
                                <div className="col-span-2">
                                    <label className="text-[9px] font-bold text-slate-500 uppercase mb-1 block ml-1">Вулиця</label>
                                    <input type="text" value={streetSearch} onChange={(e) => setStreetSearch(e.target.value)}
                                        placeholder="Назва..." className="w-full px-4 py-2 bg-white border border-slate-200 rounded-xl font-bold text-sm outline-none focus:border-blue-400"/>
                                </div>
                                <div>
                                    <label className="text-[9px] font-bold text-slate-500 uppercase mb-1 block ml-1">Буд/Кв</label>
                                    <input type="text" value={houseNumber} onChange={(e) => setHouseNumber(e.target.value)}
                                        placeholder="№" className="w-full px-4 py-2 bg-white border border-slate-200 rounded-xl font-bold text-sm outline-none focus:border-blue-400"/>
                                </div>
                            </div>
                        )
                    )}
                </div>
            </div>

            {/* 3. ПЕРЕЛІК РЕСУРСІВ */}
            <div className="space-y-4 max-h-[30vh] overflow-y-auto pr-2 custom-scrollbar">
                <label className="text-[10px] font-black uppercase text-slate-400 italic block tracking-widest">
                    {currentUser?.is_admin ? '3.' : '2.'} Перелік ресурсів
                </label>
                {formRows.map((row, index) => {
                    const availableCount = availabilityMap[row.resource] || 0;
                    return (
                        <div key={row.id} className="bg-white p-5 rounded-2xl border hover:border-blue-100 transition-all shadow-sm">
                            <div className="flex flex-col md:flex-row gap-4 items-end">
                                <div className="flex-1 w-full text-left">
                                    <label className="text-[10px] font-bold text-slate-400 uppercase block mb-1 ml-1"><Package size={12} className="inline mr-1"/>Ресурс</label>
                                    <select value={row.resource || ''} onChange={(e) => handleFormChange(index, 'resource', e.target.value)}
                                        className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm font-bold outline-none">
                                        <option value="">Оберіть ресурс...</option>
                                        {resourcesList.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                                    </select>
                                </div>
                                <div className="w-24 text-left">
                                    <label className="text-[10px] font-bold text-slate-400 uppercase block mb-1 ml-1"><Hash size={12} className="inline mr-1"/>К-сть</label>
                                    <input type="text" inputMode="numeric" value={row.quantity || ''}
                                        onKeyDown={(e) => { if (['.', ',', 'e', 'E', '+', '-'].includes(e.key)) e.preventDefault(); }}
                                        onChange={(e) => handleFormChange(index, 'quantity', e.target.value)}
                                        placeholder="0" className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm font-black outline-none"/>
                                </div>
                                <div className="flex-1 w-full text-left">
                                    <label className="text-[10px] font-bold text-slate-400 uppercase block mb-1 ml-1"><Target size={12} className="inline mr-1"/>Ціль</label>
                                    <select value={row.purpose || ''} onChange={(e) => handleFormChange(index, 'purpose', e.target.value)}
                                        className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm font-medium outline-none">
                                        <option value="">Ціль...</option>
                                        {purposes.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                                    </select>
                                </div>
                                {formRows.length > 1 && (
                                    <button onClick={() => setFormRows(formRows.filter(r => r.id !== row.id))} className="text-slate-300 p-2 hover:text-red-500 transition-colors"><Trash2 size={18}/></button>
                                )}
                            </div>
                            {row.resource && (
                                <div className={`mt-3 px-3 py-1.5 rounded-lg text-[10px] font-black uppercase flex items-center gap-2 ${availableCount > 0 ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'}`}>
                                    {availableCount > 0 ? <CheckCircle2 size={12}/> : <AlertCircle size={12}/>}
                                    {availableCount > 0 ? `На складі: ${availableCount.toFixed(0)} од.` : 'На даний момент немає на складах'}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            <button type="button" onClick={() => setFormRows([...formRows, {id: Date.now(), resource: '', quantity: '', purpose: ''}])}
                className="flex items-center gap-2 text-blue-600 font-black text-[10px] uppercase tracking-widest hover:bg-blue-50 px-6 py-4 rounded-2xl border-2 border-dashed border-blue-100 w-full justify-center transition-all active:scale-95">
                <Plus size={16}/> Додати ще одну позицію
            </button>

            <div className="flex gap-4 justify-end pt-4 border-t border-slate-100">
                <button type="button" onClick={onClose} className="px-8 py-3 text-slate-400 font-bold hover:text-slate-600 transition-colors">Скасувати</button>
                <button type="button" onClick={handleSubmit} disabled={isSubmitting || !isDeliveryAvailable}
                    className="px-10 py-3 bg-blue-600 text-white font-black rounded-2xl hover:bg-slate-900 shadow-xl shadow-blue-200 active:scale-95 transition-all disabled:bg-slate-300 disabled:shadow-none">
                    {isSubmitting ? "ЗБЕРЕЖЕННЯ..." : <div className="flex items-center gap-2"><Save size={20}/>ЗБЕРЕГТИ ЗАЯВКУ</div>}
                </button>
            </div>
        </div>
    );
};

export default RequestForm;