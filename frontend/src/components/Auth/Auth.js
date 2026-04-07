import React, { useState } from 'react';

const Auth = ({ isOpen, onClose, onLoginSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({ username: '', password: '' });

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    const usernameLower = formData.username.toLowerCase();
    const mockUser = {
      id: usernameLower === 'admin' ? 1 : 99,
      username: formData.username,
      isAdmin: usernameLower === 'admin'
    };
    onLoginSuccess(mockUser);
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      backgroundColor: 'rgba(15, 23, 42, 0.7)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      backdropFilter: 'blur(8px)'
    }}>
      <div style={{
        backgroundColor: 'white', padding: '40px', borderRadius: '24px',
        width: '100%', maxWidth: '400px', textAlign: 'center', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)'
      }}>
        <h2 style={{ fontSize: '24px', fontWeight: '900', marginBottom: '20px', color: '#1e293b' }}>
          {isLogin ? 'Вхід у систему' : 'Реєстрація'}
        </h2>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          <input
            type="text"
            placeholder="Логін (admin)"
            required
            style={{ padding: '12px', borderRadius: '12px', border: '1 -px solid #e2e8f0', outline: 'none' }}
            onChange={(e) => setFormData({...formData, username: e.target.value})}
          />
          <input
            type="password"
            placeholder="Пароль"
            required
            style={{ padding: '12px', borderRadius: '12px', border: '1px solid #e2e8f0', outline: 'none' }}
            onChange={(e) => setFormData({...formData, password: e.target.value})}
          />
          <button
            type="submit"
            style={{
              padding: '14px', backgroundColor: '#2563eb', color: 'white',
              fontWeight: 'bold', border: 'none', borderRadius: '12px', cursor: 'pointer'
            }}
          >
            {isLogin ? 'Увійти' : 'Створити акаунт'}
          </button>
        </form>

        <button
          onClick={() => setIsLogin(!isLogin)}
          style={{ marginTop: '20px', background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '12px' }}
        >
          {isLogin ? 'Немає акаунту? Реєстрація' : 'Вже є акаунт? Увійти'}
        </button>

        <button
          onClick={onClose}
          style={{ display: 'block', margin: '10px auto', background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer' }}
        >
          Закрити
        </button>
      </div>
    </div>
  );
};

export default Auth;