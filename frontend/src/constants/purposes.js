// src/constants/purposes.js
import React from 'react';
import {
  ShieldAlert,
  Stethoscope,
  Flame,
  Footprints,
  GraduationCap,
  User
} from 'lucide-react';

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
};