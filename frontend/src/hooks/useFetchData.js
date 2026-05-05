import { useState, useCallback } from 'react';
import api from '../services/api';
import { PURPOSE_MAP } from '../constants/purposes';

export const useFetchData = (currentUser) => {
    const [data, setData] = useState({
        stocks: [],
        requests: [],
        logs: [], // Додано поле для логів
        warehouses: [],
        resourcesList: [],
        resourcesMap: {},
        usersList: [],
        units: [],
        purposes: [],
        purposeMap: {}
    });

    const fetchData = useCallback(async () => {
        if (!currentUser) return;

        try {
            // Базові запити для всіх
            const requestsToMake = {
                requests: api.get('/requests/'),
                resources: api.get('/resources/'),
                units: api.get('/units/'),
                purposes: api.get('/purposes/')
            };

            // Додаткові запити ТІЛЬКИ для адміна
            if (currentUser?.is_admin) {
                requestsToMake.stocks = api.get('/stocks/');
                requestsToMake.warehouses = api.get('/warehouses/');
                requestsToMake.users = api.get('/users/');
                requestsToMake.logs = api.get('/logs/'); // ДОДАНО ЗАПИТ ДО ЛОГІВ
            }

            const keys = Object.keys(requestsToMake);
            const responses = await Promise.all(Object.values(requestsToMake));

            const results = {};
            keys.forEach((key, index) => {
                results[key] = responses[index].data;
            });

            // Фільтрація заявок
            const rawRequests = results.requests || [];
            const filteredRequests = rawRequests.filter(r => {
                if (currentUser?.is_admin) return true;

                // Виправлено == на === для відповідності стандартам
                return (
                    Number(r.user) === Number(currentUser?.id) ||
                    r.username === currentUser?.email ||
                    r.user_email === currentUser?.email
                );
            });

            const resources = results.resources || [];
            const purposes = results.purposes || [];

            setData({
                stocks: results.stocks || [],
                requests: filteredRequests,
                logs: results.logs || [], // ТЕПЕР ЛОГИ ПЕРЕДАЮТЬСЯ В APP.JS
                resourcesList: resources,
                warehouses: results.warehouses || [],
                units: results.units || [],
                purposes: purposes,
                usersList: results.users || [],
                resourcesMap: resources.reduce((acc, r) => ({...acc, [r.id]: r}), {}),
                purposeMap: purposes.reduce((acc, p) => {
                    const config = PURPOSE_MAP[p.code] || PURPOSE_MAP['default'];
                    acc[p.id] = { label: p.name, icon: config.icon, color: config.color };
                    return acc;
                }, {})
            });
        } catch (error) {
            console.error("Помилка завантаження даних:", error);
        }
    }, [currentUser]);

    return { data, fetchData };
};