import { useState, useCallback, useRef } from 'react';
import api from '../services/api';
import { PURPOSE_MAP } from '../constants/purposes';

export const useFetchData = (currentUser) => {
    const [data, setData] = useState({
        stocks: [],
        requests: [],
        logs: [],
        warehouses: [],
        resourcesList: [],
        resourcesMap: {},
        usersList: [],
        units: [],
        purposes: [],
        purposeMap: {}
    });

    // Використовуємо реф, щоб знати, чи це перше завантаження довідників
    const isStaticDataLoaded = useRef(false);

    const fetchData = useCallback(async () => {
        if (!currentUser) return;

        try {
            const requestsToMake = {};

            // 1. Динамічні дані — оновлюємо ЗАВЖДИ при кожному виклику
            requestsToMake.requests = api.get('/requests/');
            if (currentUser?.is_admin) {
                requestsToMake.stocks = api.get('/stocks/');
                requestsToMake.logs = api.get('/logs/');
            }

            // 2. Статичні дані — вантажимо ТІЛЬКИ ОДИН РАЗ при старті системи
            if (!isStaticDataLoaded.current) {
                requestsToMake.resources = api.get('/resources/');
                requestsToMake.units = api.get('/units/');
                requestsToMake.purposes = api.get('/purposes/');
                if (currentUser?.is_admin) {
                    requestsToMake.warehouses = api.get('/warehouses/');
                    requestsToMake.users = api.get('/users/');
                }
            }

            const keys = Object.keys(requestsToMake);
            const responses = await Promise.all(Object.values(requestsToMake));

            const results = {};
            keys.forEach((key, index) => {
                results[key] = responses[index].data;
            });

            // Фільтрація заявок (динамічне поле)
            const rawRequests = results.requests || [];
            const filteredRequests = rawRequests.filter(r => {
                if (currentUser?.is_admin) return true;
                return (
                    Number(r.user) === Number(currentUser?.id) ||
                    r.username === currentUser?.email ||
                    r.user_email === currentUser?.email
                );
            });

            // Оновлюємо стан React
            setData(prev => {
                // Якщо статичні дані прийшли вперше — трансформуємо мапи, інакше — беремо старі з prev
                const resources = results.resources || prev.resourcesList;
                const purposes = results.purposes || prev.purposes;

                const nextResourcesMap = results.resources
                    ? resources.reduce((acc, r) => ({...acc, [r.id]: r}), {})
                    : prev.resourcesMap;

                const nextPurposeMap = results.purposes
                    ? purposes.reduce((acc, p) => {
                        const config = PURPOSE_MAP[p.code] || PURPOSE_MAP['default'] || { color: 'bg-slate-100' };
                        acc[p.id] = { label: p.name, icon: config.icon, color: config.color };
                        return acc;
                    }, {})
                    : prev.purposeMap;

                return {
                    // Оновлювані (динамічні) поля
                    requests: filteredRequests,
                    stocks: results.stocks !== undefined ? (results.stocks || []) : prev.stocks,
                    logs: results.logs !== undefined ? (results.logs || []) : prev.logs,

                    // Статичні поля (або нові, або з попереднього стану)
                    resourcesList: resources,
                    purposes: purposes,
                    resourcesMap: nextResourcesMap,
                    purposeMap: nextPurposeMap,
                    warehouses: results.warehouses || prev.warehouses,
                    units: results.units || prev.units,
                    usersList: results.users || prev.usersList
                };
            });

             if (!isStaticDataLoaded.current) {
                isStaticDataLoaded.current = true;
            }

        } catch (error) {
            console.error("Помилка завантаження даних:", error);
        }
    }, [currentUser]);

    return { data, fetchData };
};