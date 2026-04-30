import axios from 'axios';
import { toast } from 'react-hot-toast';
import authService from './authService';

// Створюємо інстанс axios з базовими налаштуваннями
const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// --- REQUEST INTERCEPTOR ---
// Автоматично додає access токен до кожного запиту
api.interceptors.request.use((config) => {
  const token = authService.getAccessToken(); // Замість localStorage.getItem
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// --- RESPONSE INTERCEPTOR ---
// Обробка помилок та автоматичне оновлення токена
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Якщо отримали 401 (токен протух) і ми ще не пробували його оновити
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) throw new Error("No refresh token");

        // Запит на оновлення токена
        const res = await axios.post('http://localhost:8000/api/token/refresh/', {
          refresh: refreshToken
        });

        const newAccessToken = res.data.access;
        localStorage.setItem('access_token', newAccessToken);

        // Повторюємо початковий запит з новим токеном
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Якщо оновити не вдалося (наприклад, refresh токен теж недійсний)
        localStorage.clear();
        window.location.href = '/'; // Робимо редирект на логін
        return Promise.reject(refreshError);
      }
    }

    // Централізована обробка помилок для toast
    const errorMessage = error.response?.data?.detail || error.response?.data?.error || "Помилка сервера";

    // Не показуємо помилку 401 тут, бо ми її обробляємо вище
    if (error.response?.status !== 401) {
      toast.error(errorMessage);
    }

    return Promise.reject(error);
  }
);

export default api;