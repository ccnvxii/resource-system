import { useState, useCallback } from 'react';

export const useModal = (initialState = {}) => {
  const [modals, setModals] = useState(initialState);

  const openModal = useCallback((name) => {
    setModals((prev) => ({ ...prev, [name]: true }));
  }, []);

  const closeModal = useCallback((name) => {
    setModals((prev) => ({ ...prev, [name]: false }));
  }, []);

  const toggleModal = useCallback((name) => {
    setModals((prev) => ({ ...prev, [name]: !prev[name] }));
  }, []);

  return { modals, openModal, closeModal, toggleModal };
};