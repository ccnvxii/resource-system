import { PURPOSE_MAP } from '../constants/purposes';

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

export const exportPlanToExcel = async (plan, strategy = 'hybrid') => {
  if (!plan || !plan.items || plan.items.length === 0) return;

  // Динамічний імпорт xlsx — виключає важку бібліотеку з головного бандлу
  const XLSX = await import('xlsx');

  const dataToExport = plan.items.map(item => {
    const purposeKey = item.purpose_code || item.purpose;
    const purposeMeta = PURPOSE_MAP[purposeKey] || { label: item.purpose_name || 'Інше' };

    // --- РОЗУМНЕ ВИЗНАЧЕННЯ МЕТОДУ ---
    let methodLabel = 'Справедливість';
    if (strategy === 'triage' || item.is_strategic) {
        methodLabel = 'Екстрений Тріаж';
    }

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
      "Метод Розподілу": methodLabel
    };
  });

  const ws = XLSX.utils.json_to_sheet(dataToExport);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Результати розподілу");
  XLSX.writeFile(wb, `Distribution_Plan_${plan.id || 'new'}.xlsx`);
};

export const exportRequestsToExcel = async (requests = []) => {
  if (!Array.isArray(requests) || !requests.length) return;
  const XLSX = await import('xlsx');
  const ws = XLSX.utils.json_to_sheet(requests);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Звіт");
  XLSX.writeFile(wb, "ResQ_Report.xlsx");
};

export const exportResourcesToExcel = async (stocks = [], resourcesMap = {}) => {
  if (!Array.isArray(stocks) || !stocks.length) return;
  const XLSX = await import('xlsx');
  const rows = stocks.map(s => {
    const res = resourcesMap?.[s.resource];
    return {
      "Склад": s.warehouse_name || '',
      "Ресурс": s.resource_name || res?.name || `Ресурс ID ${s.resource}`,
      "Категорія": res?.category_name || '',
      "Кількість": Number(s.amount) || 0,
      "Одиниця": s.unit_name || res?.unit_name || 'од.',
    };
  }).sort((a, b) => a["Склад"].localeCompare(b["Склад"]) || a["Ресурс"].localeCompare(b["Ресурс"]));
  const ws = XLSX.utils.json_to_sheet(rows);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Ресурси");
  XLSX.writeFile(wb, "ResQ_Resources_Report.xlsx");
};
