import * as XLSX from 'xlsx';
import { PURPOSE_MAP } from '../../constants/purposes';

// Локальна функція форматування дати для Excel
const formatExcelDate = (dateString) => {
  if (!dateString) return null;
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('uk-UA', { day: '2-digit', month: '2-digit', year: 'numeric' });
  } catch (e) {
    return dateString;
  }
};

export const exportPlanToExcel = (plan, strategy = 'fairness') => {
  if (!plan || !plan.items || plan.items.length === 0) return;

  const dataToExport = plan.items.map(item => {
    const purposeKey = item.purpose_code || item.purpose;
    const purposeMeta = PURPOSE_MAP[purposeKey] || { label: item.purpose_name || 'Інше' };

    return {
      "ID Операції": item.id,
      "Пріоритет": item.priority ? Number(item.priority).toFixed(1) : '0.0',
      "Граничний термін": item.due_date ? formatExcelDate(item.due_date) : 'Не вказано',
      "Ресурс": item.resource_name,
      "Виділено": Math.round(item.amount),
      "Запитувано": item.quantity_requested ? Math.round(item.quantity_requested) : 0,
      "Одиниця": item.unit_name || 'од.',
      "Склад-джерело": item.warehouse_name,
      "Отримувач": item.recipient_name,
      "Пункт призначення": `${item.city || ''} ${item.warehouse_address || ''}`.trim() || 'Адресна доставка',
      "Призначення": purposeMeta.label,
      "Метод Розподілу": strategy === 'triage' ? 'Екстрений Тріаж' : 'Справедливість'
    };
  });

  const ws = XLSX.utils.json_to_sheet(dataToExport);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Результати розподілу");
  XLSX.writeFile(wb, `Distribution_Plan_${plan.id || 'new'}.xlsx`);
};