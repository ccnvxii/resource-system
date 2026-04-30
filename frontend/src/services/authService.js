const ACCESS_TOKEN = 'access_token';
const REFRESH_TOKEN = 'refresh_token';
const CURRENT_USER = 'currentUser';

const authService = {
  /**
   * Зберігає токени в локальному сховищі
   */
  setTokens(access, refresh) {
    if (access) localStorage.setItem(ACCESS_TOKEN, access);
    if (refresh) localStorage.setItem(REFRESH_TOKEN, refresh);
  },

  /**
   * Отримує access токен
   */
  getAccessToken() {
    return localStorage.getItem(ACCESS_TOKEN);
  },

  /**
   * Отримує refresh токен
   */
  getRefreshToken() {
    return localStorage.getItem(REFRESH_TOKEN);
  },

  /**
   * Зберігає дані користувача
   */
  setUser(userData) {
    localStorage.setItem(CURRENT_USER, JSON.stringify(userData));
  },

  /**
   * Отримує об'єкт користувача
   */
  getUser() {
    const user = localStorage.getItem(CURRENT_USER);
    try {
      return user ? JSON.parse(user) : null;
    } catch (e) {
      console.error("Помилка парсингу користувача з localStorage", e);
      return null;
    }
  },

  /**
   * Повністю очищує дані авторизації
   */
  clearAuth() {
    localStorage.removeItem(ACCESS_TOKEN);
    localStorage.removeItem(REFRESH_TOKEN);
    localStorage.removeItem(CURRENT_USER);
    // Якщо хочете очистити ВСЕ, використовуйте localStorage.clear();
  },

  /**
   * Перевіряє, чи залогінений користувач
   */
  isAuthenticated() {
    return !!this.getAccessToken();
  }
};

export default authService;