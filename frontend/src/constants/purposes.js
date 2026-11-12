// src/constants/purposes.js
import React from 'react';
import {
  ShieldAlert,
  Stethoscope,
  Flame,
  Footprints,
  GraduationCap,
  User,
  Baby,
  Accessibility,
  Tent,
  Siren,
  Package
} from '../components/UI/icons';

// Іконка та колір для кожного коду призначення (code з довідника RequestPurpose).
// Для кодів, яких тут немає, використовується запис 'default'.
export const PURPOSE_MAP = {
  'military': {
    label: 'Військові',
    icon: <ShieldAlert size={14} />,
    color: 'bg-red-100 text-red-800'
  },
  'hospital': {
    label: 'Лікарня',
    icon: <Stethoscope size={14} />,
    color: 'bg-blue-100 text-blue-800'
  },
  'disaster': {
    label: 'Катастрофа',
    icon: <Flame size={14} />,
    color: 'bg-orange-100 text-orange-800'
  },
  'refugees': {
    label: 'ВПО',
    icon: <Footprints size={14} />,
    color: 'bg-yellow-100 text-yellow-800'
  },
  'school': {
    label: 'Школа',
    icon: <GraduationCap size={14} />,
    color: 'bg-purple-100 text-purple-800'
  },
  'personal': {
    label: 'Особисте',
    icon: <User size={14} />,
    color: 'bg-gray-100 text-gray-800'
  },
  'children': {
    label: 'Діти',
    icon: <Baby size={14} />,
    color: 'bg-pink-100 text-pink-800'
  },
  'elderly': {
    label: 'Літні люди',
    icon: <Accessibility size={14} />,
    color: 'bg-teal-100 text-teal-800'
  },
  'shelters': {
    label: 'Укриття',
    icon: <Tent size={14} />,
    color: 'bg-emerald-100 text-emerald-800'
  },
  'rescue': {
    label: 'Рятувальники',
    icon: <Siren size={14} />,
    color: 'bg-rose-100 text-rose-800'
  },
  'default': {
    label: 'Інше',
    icon: <Package size={14} />,
    color: 'bg-slate-100 text-slate-700'
  },
};
