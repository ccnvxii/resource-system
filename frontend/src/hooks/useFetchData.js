import { useState, useCallback } from 'react';
import api from '../services/api';
import { PURPOSE_MAP } from '../type/purposes';

export const useFetchData = (currentUser) => {
  const [data, setData] = useState({
    stocks: [],
    requests: [],
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
      const endpoints = [
        '/stocks/', '/requests/', '/resources/',
        '/warehouses/', '/units/', '/purposes/'
      ];

      // Додаємо запит користувачів лише для адміністратора
      if (currentUser?.is_admin) endpoints.push('/users/');

      const responses = await Promise.all(endpoints.map(url => api.get(url)));
      const [stock, req, res, wh, unit, purp, user] = responses.map(r => r.data);

      setData({
        stocks: stock,
        requests: req,
        resourcesList: res,
        warehouses: wh,
        units: unit,
        purposes: purp,
        usersList: user || [],
        // Створення мапи ресурсів для швидкого пошуку за ID
        resourcesMap: res.reduce((acc, r) => ({ ...acc, [r.id]: r }), {}),
        // Мапінг кодів призначень на іконки та кольори
        purposeMap: purp.reduce((acc, p) => {
          const config = PURPOSE_MAP[p.code] || PURPOSE_MAP['default'];
          acc[p.id] = {
            label: p.name,
            icon: config.icon,
            color: config.color
          };
          return acc;
        }, {})
      });
    } catch (error) {
      console.error("Помилка завантаження даних:", error);
      throw error;
    }
  }, [currentUser]);

  return { data, fetchData };
};