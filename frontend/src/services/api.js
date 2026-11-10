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

// Допоміжна функція для вилучення зрозумілого тексту помилки з бекенду
export const extractErrorMessage = (error, fallback = "Сталася помилка") => {
  if (!error.response) {
    return "Немає зв'язку з сервером. Перевірте з'єднання.";
  }
  const data = error.response.data;
  if (!data) return fallback;
  if (typeof data === 'string') return data;
  if (data.detail) return data.detail;
  if (data.error) return data.error;
  if (Array.isArray(data.non_field_errors) && data.non_field_errors.length) {
    return data.non_field_errors.join(', ');
  }
  if (typeof data === 'object') {
    const messages = [];
    const fieldTranslations = {
      resource: 'Ресурс',
      quantity_requested: 'Кількість',
      purpose: 'Ціль',
      user: 'Заявник',
      city: 'Місто',
      warehouse_address: 'Адреса',
      warehouse_ref: 'Відділення',
      due_date: 'Термін виконання'
    };
    for (const [key, val] of Object.entries(data)) {
      const fieldTitle = fieldTranslations[key] || key;
      const fieldMsg = Array.isArray(val) ? val.join(', ') : String(val);
      messages.push(`${fieldTitle}: ${fieldMsg}`);
    }
    if (messages.length) return messages.join('\n');
  }
  return fallback;
};

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
    // Не показуємо помилку 401 тут, бо ми її обробляємо вище
    // Також не показуємо якщо запит передав _suppressToast: true або для запитів створення заявок
    const isSuppressed = error.config?._suppressToast || error.config?.url?.includes('/requests/');
    if (error.response?.status !== 401 && !isSuppressed) {
      const errorMessage = extractErrorMessage(error, "Помилка при виконанні запиту");
      toast.dismiss();
      toast.error(errorMessage, { id: 'global-api-error' });
    }

    return Promise.reject(error);
  }
);

export default api;