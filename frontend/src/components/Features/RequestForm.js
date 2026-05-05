import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
    User, Package, Hash, Target, Plus, Trash2, Save,
    AlertCircle, CheckCircle2, MapPin, Truck, Map as MapIcon, X, Home
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import api from '../../services/api';

import 'leaflet/dist/leaflet.css';

// Фікс іконок Leaflet для React
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Допоміжні компоненти для мапи
function MapEffect() {
    const map = useMap();
    useEffect(() => {
        setTimeout(() => map.invalidateSize(), 250);
    }, [map]);
    return null;
}

function ChangeView({ center, zoom }) {
    const map = useMap();
    useEffect(() => {
        if (center && center[0] !== 48.3794) map.setView(center, zoom);
    }, [center, zoom, map]);
    return null;
}

const RequestForm = ({
    usersList = [], resourcesList = [], stocks = [], purposes = [],
    onClose, fetchData, currentUser
}) => {
    // --- СТАН ДАНИХ НОВОЇ ПОШТИ ---
    const [cities, setCities] = useState([]);
    const [warehouses, setWarehouses] = useState([]);
    const [streets, setStreets] = useState([]);
    const [selectedCity, setSelectedCity] = useState(null);
    const [selectedWarehouse, setSelectedWarehouse] = useState(null);
    const [selectedStreet, setSelectedStreet] = useState(null);

    const [citySearch, setCitySearch] = useState('');
    const [streetSearch, setStreetSearch] = useState('');
    const [houseNumber, setHouseNumber] = useState('');

    const [showCityDropdown, setShowCityDropdown] = useState(false);
    const [showStreetDropdown, setShowStreetDropdown] = useState(false);
    const [showMap, setShowMap] = useState(false);
    const [langError, setLangError] = useState(false);
    const [deliveryType, setDeliveryType] = useState('warehouse');

    // --- СТАН ФОРМИ ЗАПИТУ ---
    const [selectedUserId, setSelectedUserId] = useState('');
    const [formRows, setFormRows] = useState([{ id: Date.now(), resource: '', quantity: '', purpose: '' }]);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const dropdownRef = useRef(null);
    const streetDropdownRef = useRef(null);

    // --- ЛОГІКА ПОШУКУ МІСТ ---
    const handleCityInput = (val) => {
        setCitySearch(val);
        const isEnglish = /[a-zA-Z]/.test(val);
        setLangError(isEnglish);
        if (isEnglish) setShowCityDropdown(false);
        setSelectedCity(null);
    };

    const fetchCities = async (search) => {
        if (search.length < 2 || langError) return;
        try {
            const response = await api.post('/novaposhta/', { action: 'get_cities', search });
            setCities(Array.isArray(response.data) ? response.data : []);
            setShowCityDropdown(true);
        } catch (err) { console.error("City fetch error:", err); }
    };

    // --- ЛОГІКА ПОШУКУ ВІДДІЛЕНЬ ---
    const fetchWarehouses = async (cityRef) => {
        if (!cityRef) return;
        try {
            const response = await api.post('/novaposhta/', { action: 'get_warehouses', city_ref: cityRef });
            setWarehouses(Array.isArray(response.data) ? response.data : []);
        } catch (err) { console.error("Warehouse fetch error:", err); }
    };

    // --- ЛОГІКА ПОШУКУ ВУЛИЦЬ ---
    const fetchStreets = async (search) => {
        const cityRef = selectedCity?.SettlementRef || selectedCity?.Ref;
        if (!cityRef || search.length < 2) return;
        try {
            const response = await api.post('/novaposhta/', { action: 'get_streets', city_ref: cityRef, search });
            const data = Array.isArray(response.data) ? response.data : [];
            setStreets(data);
            setShowStreetDropdown(data.length > 0);
        } catch (err) { console.error("Street fetch error:", err); }
    };

    // --- ЕФЕКТИ ---
    useEffect(() => {
        const timer = setTimeout(() => {
            if (citySearch && !selectedCity && !langError) fetchCities(citySearch);
        }, 500);
        return () => clearTimeout(timer);
    }, [citySearch, selectedCity, langError]);

    useEffect(() => {
        if (selectedCity && deliveryType === 'warehouse') {
            // Використовуємо SettlementRef для отримання відділень
            fetchWarehouses(selectedCity.SettlementRef || selectedCity.Ref);
        }
    }, [selectedCity, deliveryType]);

    useEffect(() => {
        const timer = setTimeout(() => {
            if (streetSearch && !selectedStreet && deliveryType === 'address') fetchStreets(streetSearch);
        }, 500);
        return () => clearTimeout(timer);
    }, [streetSearch, selectedStreet, deliveryType]);

    // Розрахунок доступності ресурсів
    const availabilityMap = useMemo(() => {
        return stocks.reduce((acc, s) => {
            acc[s.resource] = (acc[s.resource] || 0) + parseFloat(s.amount);
            return acc;
        }, {});
    }, [stocks]);

    const mapCenter = useMemo(() => {
        if (selectedWarehouse?.Latitude && parseFloat(selectedWarehouse.Latitude) !== 0)
            return [parseFloat(selectedWarehouse.Latitude), parseFloat(selectedWarehouse.Longitude)];
        return [48.3794, 31.1656];
    }, [selectedWarehouse]);

    const handleFormChange = (index, field, value) => {
        const newRows = [...formRows];
        newRows[index][field] = value;
        setFormRows(newRows);
    };

    const handleSubmit = async () => {
        if (!selectedCity) return toast.error("Оберіть місто");
        const finalAddress = deliveryType === 'warehouse'
            ? selectedWarehouse?.Description
            : `вул. ${selectedStreet?.Description}, буд. ${houseNumber}`;

        if (!finalAddress) return toast.error("Вкажіть адресу доставки");

        setIsSubmitting(true);
        try {
            await Promise.all(formRows.map(row => api.post('/requests/', {
                resource: parseInt(row.resource),
                quantity_requested: Math.round(parseFloat(row.quantity)),
                purpose: parseInt(row.purpose),
                user: selectedUserId || currentUser?.id,
                city: selectedCity.Present || selectedCity.Description,
                warehouse_address: finalAddress,
                warehouse_ref: deliveryType === 'warehouse' ? selectedWarehouse?.Ref : 'ADDRESS_DELIVERY'
            })));
            toast.success("Заявку успішно створено");
            fetchData();
            onClose();
        } catch (err) {
            toast.error("Помилка при збереженні");
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="space-y-6 text-left relative">
            {/* МОДАЛЬНЕ ВІКНО КАРТИ */}
            {showMap && (
                <div className="fixed inset-0 z-[10000] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
                    <div className="bg-white w-full max-w-4xl h-[80vh] rounded-3xl overflow-hidden shadow-2xl flex flex-col">
                        <div className="p-4 border-b flex justify-between items-center bg-white">
                            <h3 className="font-black text-slate-700 uppercase text-xs italic flex items-center gap-2">
                                <MapIcon size={16} className="text-blue-600"/> Мапа: {selectedCity?.MainDescription}
                            </h3>
                            <button onClick={() => setShowMap(false)} className="p-2 hover:bg-slate-100 rounded-full transition-colors"><X size={20}/></button>
                        </div>
                        <div className="flex-1">
                            <MapContainer center={mapCenter} zoom={13} style={{height: '100%', width: '100%'}}>
                                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                                <MapEffect />
                                <ChangeView center={mapCenter} zoom={15} />
                                {warehouses.map((w, idx) => w.Latitude && (
                                    <Marker
                                        key={`marker-${w.Ref || idx}`}
                                        position={[parseFloat(w.Latitude), parseFloat(w.Longitude)]}
                                        eventHandlers={{ click: () => { setSelectedWarehouse(w); toast.success(`Обрано: ${w.Description}`); } }}
                                    >
                                        <Popup>
                                            <div className="text-center font-bold text-xs">
                                                {w.Description}<br/>
                                                <button onClick={() => setShowMap(false)} className="mt-2 bg-blue-600 text-white px-3 py-1 rounded uppercase">Вибрати</button>
                                            </div>
                                        </Popup>
                                    </Marker>
                                ))}
                            </MapContainer>
                        </div>
                    </div>
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* ЗАЯВНИК */}
                <div className="bg-blue-50/30 p-5 rounded-2xl border border-blue-100">
                    <label className="text-[10px] font-black uppercase text-slate-400 italic mb-1.5 block">Заявник</label>
                    {currentUser?.is_admin ? (
                        <select
                            value={selectedUserId || ''}
                            onChange={(e) => setSelectedUserId(e.target.value)}
                            className="w-full px-4 py-2 bg-white border border-slate-200 rounded-xl font-bold text-sm outline-none"
                        >
                            <option value="">Оберіть користувача...</option>
                            {usersList.map(u => <option key={`user-${u.id}`} value={u.id}>{u.full_name || u.username}</option>)}
                        </select>
                    ) : <p className="font-black text-slate-900 text-sm px-1">{currentUser?.first_name} {currentUser?.last_name}</p>}
                </div>

                {/* НАСЕЛЕНИЙ ПУНКТ */}
                <div className="bg-slate-50 p-5 rounded-2xl border border-slate-200 space-y-3 relative">
                    <div className="relative text-left">
                        <label className="text-[10px] font-black uppercase text-slate-400 italic mb-1.5 block">Місто</label>
                        <input
                            type="text"
                            value={citySearch || ''}
                            onChange={(e) => handleCityInput(e.target.value)}
                            placeholder="Введіть назву..."
                            className={`w-full px-4 py-2 bg-white border ${langError ? 'border-red-300' : 'border-slate-200'} rounded-xl font-bold text-sm outline-none transition-all`}
                        />
                        {showCityDropdown && cities.length > 0 && (
                            <div className="absolute left-0 right-0 z-[9999] mt-1 max-h-52 overflow-y-auto bg-white border-2 border-blue-100 rounded-xl shadow-2xl">
                                {cities.map((city, idx) => (
                                    <div
                                        key={`city-${city.Ref || idx}`}
                                        className="px-4 py-3 hover:bg-blue-50 cursor-pointer text-sm font-bold border-b last:border-none"
                                        onClick={() => {
                                            setSelectedCity(city);
                                            setCitySearch(city.MainDescription || city.Description);
                                            setShowCityDropdown(false);
                                            setStreetSearch('');
                                        }}
                                    >
                                        {city.Present || city.Description}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* ПЕРЕМИКАЧ ТИПУ ДОСТАВКИ */}
                    <div className="flex bg-white p-1 rounded-xl border">
                        <button type="button" onClick={() => setDeliveryType('warehouse')} className={`flex-1 py-2 rounded-lg text-[10px] font-black uppercase transition-all ${deliveryType === 'warehouse' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400'}`}>
                            <Truck size={14} className="inline mr-2"/>Відділення
                        </button>
                        <button type="button" onClick={() => setDeliveryType('address')} className={`flex-1 py-2 rounded-lg text-[10px] font-black uppercase transition-all ${deliveryType === 'address' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400'}`}>
                            <Home size={14} className="inline mr-2"/>Адреса
                        </button>
                    </div>

                    {/* ДИНАМІЧНІ ПОЛЯ ДОСТАВКИ */}
                    {deliveryType === 'warehouse' ? (
                        <div className="text-left animate-in fade-in">
                            <div className="flex justify-between items-center mb-1.5">
                                <label className="text-[10px] font-black text-slate-400 uppercase italic">Відділення</label>
                                {selectedCity && <button type="button" onClick={() => setShowMap(true)} className="text-[9px] font-black text-blue-600 uppercase flex items-center gap-1"><MapIcon size={10}/>Карта</button>}
                            </div>
                            <select
                                disabled={!selectedCity}
                                value={selectedWarehouse?.Ref || ''}
                                onChange={(e) => setSelectedWarehouse(warehouses.find(w => w.Ref === e.target.value))}
                                className="w-full px-4 py-2 bg-white border border-slate-200 rounded-xl font-bold text-sm outline-none disabled:bg-slate-100 transition-all"
                            >
                                <option value="">{selectedCity ? "Оберіть зі списку..." : "Спочатку вкажіть місто"}</option>
                                {warehouses.map((w, idx) => <option key={`wh-${w.Ref || idx}`} value={w.Ref}>{w.Description}</option>)}
                            </select>
                        </div>
                    ) : (
                        <div className="space-y-3 animate-in fade-in">
                            <div className="relative">
                                <label className="text-[10px] font-black text-slate-400 uppercase italic mb-1.5 block">Вулиця</label>
                                <input
                                    type="text"
                                    disabled={!selectedCity}
                                    value={streetSearch || ''}
                                    onChange={(e) => { setStreetSearch(e.target.value); setSelectedStreet(null); }}
                                    placeholder="Назва вулиці..."
                                    className="w-full px-4 py-2 bg-white border border-slate-200 rounded-xl font-bold text-sm outline-none disabled:bg-slate-100"
                                />
                                {showStreetDropdown && streets.length > 0 && (
                                    <div className="absolute left-0 right-0 z-[9999] mt-1 max-h-48 overflow-y-auto bg-white border-2 border-blue-100 rounded-xl shadow-2xl">
                                        {streets.map((s, idx) => (
                                            <div
                                                key={`street-${s.StreetRef || idx}`}
                                                className="px-4 py-2 hover:bg-blue-50 cursor-pointer border-b last:border-none font-bold text-sm"
                                                onClick={() => { setSelectedStreet(s); setStreetSearch(s.Description); setShowStreetDropdown(false); }}
                                            >
                                                {s.Description}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                            <input
                                type="text"
                                disabled={!selectedStreet}
                                value={houseNumber || ''}
                                onChange={(e) => setHouseNumber(e.target.value)}
                                placeholder="Будинок / Кв"
                                className="w-full px-4 py-2 bg-white border border-slate-200 rounded-xl font-bold text-sm outline-none disabled:bg-slate-100"
                            />
                        </div>
                    )}
                </div>
            </div>

            {/* СПИСОК РЕСУРСІВ */}
            <div className="space-y-4 max-h-[30vh] overflow-y-auto pr-2 custom-scrollbar">
                {formRows.map((row, index) => {
                    const availableCount = availabilityMap[row.resource] || 0;
                    return (
                        <div key={row.id} className="bg-white p-5 rounded-2xl border hover:border-blue-100 transition-all">
                            <div className="flex flex-col md:flex-row gap-4 items-end">
                                <div className="flex-1 w-full text-left">
                                    <label className="text-[10px] font-bold text-slate-400 uppercase block mb-1 ml-1"><Package size={12} className="inline mr-1"/>Ресурс</label>
                                    <select
                                        value={row.resource || ''}
                                        onChange={(e) => handleFormChange(index, 'resource', e.target.value)}
                                        className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm font-bold outline-none"
                                    >
                                        <option value="">Оберіть ресурс...</option>
                                        {resourcesList.map(r => <option key={`res-${r.id}`} value={r.id}>{r.name}</option>)}
                                    </select>
                                </div>
                                <div className="w-24 text-left">
                                    <label className="text-[10px] font-bold text-slate-400 uppercase block mb-1 ml-1"><Hash size={12} className="inline mr-1"/>К-сть</label>
                                    <input
                                        type="number"
                                        min="1"
                                        value={row.quantity || ''}
                                        onChange={(e) => handleFormChange(index, 'quantity', e.target.value)}
                                        className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm font-black outline-none"
                                    />
                                </div>
                                <div className="flex-1 w-full text-left">
                                    <label className="text-[10px] font-bold text-slate-400 uppercase block mb-1 ml-1"><Target size={12} className="inline mr-1"/>Ціль</label>
                                    <select
                                        value={row.purpose || ''}
                                        onChange={(e) => handleFormChange(index, 'purpose', e.target.value)}
                                        className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm font-medium outline-none"
                                    >
                                        <option value="">Оберіть ціль...</option>
                                        {purposes.map(p => <option key={`purp-${p.id}`} value={p.id}>{p.name}</option>)}
                                    </select>
                                </div>
                                {formRows.length > 1 && (
                                    <button
                                        type="button"
                                        onClick={() => setFormRows(formRows.filter(r => r.id !== row.id))}
                                        className="p-2.5 text-slate-300 hover:text-red-500 transition-colors mb-0.5"
                                    >
                                        <Trash2 size={18}/>
                                    </button>
                                )}
                            </div>
                            {row.resource && (
                                <div className={`mt-3 px-3 py-1.5 rounded-lg text-[10px] font-black uppercase flex items-center gap-2 ${availableCount > 0 ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'}`}>
                                    {availableCount > 0 ? <CheckCircle2 size={12}/> : <AlertCircle size={12}/>}
                                    {availableCount > 0 ? `На складі: ${availableCount.toFixed(0)} од.` : 'Ресурс відсутній'}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            <button
                type="button"
                onClick={() => setFormRows([...formRows, { id: Date.now(), resource: '', quantity: '', purpose: '' }])}
                className="flex items-center gap-2 text-blue-600 font-black text-[10px] uppercase tracking-widest hover:bg-blue-50 px-6 py-3 rounded-xl border-2 border-dashed border-blue-100 w-full justify-center transition-all"
            >
                <Plus size={16}/> Додати позицію
            </button>

            <div className="flex gap-4 justify-end pt-6 border-t border-slate-100">
                <button
                    type="button"
                    onClick={onClose}
                    className="px-8 py-3 text-slate-400 font-bold hover:text-slate-600 transition-colors"
                >
                    Скасувати
                </button>
                <button
                    type="button"
                    onClick={handleSubmit}
                    disabled={isSubmitting}
                    className="px-10 py-3 bg-blue-600 text-white font-black rounded-2xl shadow-xl shadow-blue-200 hover:bg-slate-900 transition-all transform active:scale-95 disabled:bg-slate-300"
                >
                    {isSubmitting ? "ЗБЕРЕЖЕННЯ..." : <div className="flex items-center gap-2"><Save size={20}/>ЗБЕРЕГТИ ЗАЯВКУ</div>}
                </button>
            </div>
        </div>
    );
};

export default RequestForm;