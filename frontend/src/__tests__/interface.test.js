/**
 * ТЕСТУВАННЯ ІНТЕРФЕЙСУ (Jest + React Testing Library).
 * Категорії: валідація та форми, компоненти, безпека та доступність коду.
 * Нумерація тестів наскрізна, назви починаються з номера (для таблиць у звіті).
 */
import React from 'react';
import fs from 'fs';
import path from 'path';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

jest.mock('axios', () => ({
    post: jest.fn(),
    get: jest.fn(),
    create: jest.fn(() => ({ interceptors: { request: { use: jest.fn() }, response: { use: jest.fn() } } })),
}));
jest.mock('react-hot-toast', () => ({ toast: { error: jest.fn(), success: jest.fn(), dismiss: jest.fn() } }));

import AuthModal from '../components/Auth/Auth';
import Modal from '../components/UI/Modal';
import ConfirmModal from '../components/UI/ConfirmModal';
import SearchableSelect from '../components/UI/SearchableSelect';
import RequestCard from '../components/Features/Requests/RequestCard';
import { PURPOSE_MAP } from '../constants/purposes';
import { extractErrorMessage } from '../services/api';
import {
    formatPhone, phoneDigits, isValidPhone, EMAIL_REGEX, NAME_REGEX, MIN_PASSWORD_LENGTH,
} from '../utils/validation';

// ---------------------------------------------------------------------------
describe('Валідація та форми', () => {
    test('1. Маска телефона: формат +380 (XX) XXX-XX-XX, лише цифри, посимвольне введення, стирання', () => {
        expect(formatPhone('0671234567')).toBe('+380 (67) 123-45-67');
        expect(formatPhone('+380671234567')).toBe('+380 (67) 123-45-67');
        expect(formatPhone('abc')).toBe('');
        expect(formatPhone('06a7b1c2d3')).toBe('+380 (67) 123');
        expect(formatPhone('06712345678901234')).toBe('+380 (67) 123-45-67');       // не більше 9 цифр
        const typeChars = (s) => [...s].reduce((v, ch) => formatPhone(v + ch), '');
        expect(typeChars('0671234567')).toBe('+380 (67) 123-45-67');
        expect(typeChars('+380671234567')).toBe('+380 (67) 123-45-67');              // ручне введення коду країни
        expect(formatPhone('+380 (67)')).toBe('+380 (67');                           // стирання не «залипає» на дужці
        expect(formatPhone('')).toBe('');
        expect(phoneDigits('+380 (67) 123-45-67')).toBe('380671234567');
        expect(isValidPhone('+380 (67) 123-45-67')).toBe(true);
        expect(isValidPhone('+380 (67) 123')).toBe(false);
    });

    test('2. Правила полів: email, ім’я, мінімальна довжина пароля', () => {
        ['name@example.com', 'a.b-c_d@sub.domain.ua', 'user+tag@mail.co'].forEach((e) => expect(EMAIL_REGEX.test(e)).toBe(true));
        ['abc', 'abc@', '@example.com', 'abc@x', 'a b@example.com', 'a@@example.com', ''].forEach((e) => expect(EMAIL_REGEX.test(e)).toBe(false));
        expect(NAME_REGEX.test("О'Коннор-Петренко")).toBe(true);
        expect(NAME_REGEX.test('Ivan 2')).toBe(false);
        expect(NAME_REGEX.test('<script>')).toBe(false);
        expect(MIN_PASSWORD_LENGTH).toBe(8);                                         // узгоджено з сервером
    });

    test('3. Повідомлення про помилки сервера та оформлення призначень заявок', () => {
        expect(extractErrorMessage({})).toMatch(/Немає зв.язку/);
        expect(extractErrorMessage({ response: { data: { detail: 'Деталі' } } })).toBe('Деталі');
        const fields = extractErrorMessage({ response: { data: { quantity_requested: ['Ліміт'], due_date: ['Минуле'] } } });
        expect(fields).toContain('Кількість: Ліміт');
        expect(fields).toContain('Термін виконання: Минуле');
        const codes = ['refugees', 'disaster', 'hospital', 'military', 'children', 'elderly', 'shelters', 'rescue'];
        codes.forEach((c) => {
            expect(PURPOSE_MAP[c].icon).toBeTruthy();
            expect(PURPOSE_MAP[c].color).toMatch(/bg-\w+-\d+ text-\w+-\d+/);
        });
        expect(new Set(codes.map((c) => PURPOSE_MAP[c].color)).size).toBe(codes.length);   // кольори відрізняються
        expect(PURPOSE_MAP.default.icon).toBeTruthy();                                      // запасний варіант
    });

    test('4. Форма входу: показ пароля, перехід до відновлення пароля (крок 1 з 3)', () => {
        render(<AuthModal isOpen onClose={() => {}} onSuccess={() => {}} />);
        expect(document.querySelector('input[type="password"]')).not.toBeNull();
        userEvent.click(screen.getByLabelText('Показати пароль'));
        expect(document.querySelector('input[type="password"]')).toBeNull();
        expect(screen.getByLabelText('Сховати пароль')).toBeInTheDocument();
        userEvent.click(screen.getByText('Забули пароль?'));
        expect(screen.getByText(/Крок 1 з 3/)).toBeInTheDocument();
    });

    test('5. Форма реєстрації: маска телефона, підказка про email, відхилення короткого пароля', async () => {
        render(<AuthModal isOpen onClose={() => {}} onSuccess={() => {}} />);
        userEvent.click(screen.getByText('Немає профілю? Створити'));
        const phone = screen.getByPlaceholderText('+380 (__) ___-__-__');
        userEvent.type(phone, 'abc0671234567');
        expect(phone).toHaveValue('+380 (67) 123-45-67');
        userEvent.type(screen.getByPlaceholderText('email@test.com'), 'без-собаки');
        expect(await screen.findByText(/Введіть коректний email/)).toBeInTheDocument();
        userEvent.type(document.querySelector('input[type="password"]'), 'abc123');
        expect(await screen.findByText(/щонайменше 8 символів/)).toBeInTheDocument();
    });
});

// ---------------------------------------------------------------------------
describe('Компоненти інтерфейсу', () => {
    test('6. Вікно: закривається хрестиком та Esc, але не кліком по фону', () => {
        const onClose = jest.fn();
        const { container } = render(<Modal isOpen onClose={onClose} title="Заголовок"><p>Вміст</p></Modal>);
        fireEvent.click(container.firstChild);
        expect(onClose).not.toHaveBeenCalled();
        fireEvent.click(screen.getByLabelText('Закрити вікно'));
        fireEvent.keyDown(window, { key: 'Escape' });
        expect(onClose).toHaveBeenCalledTimes(2);
    });

    test('7. Підтвердження дії: повідомлення, обробники кнопок, блокування під час виконання', () => {
        const onConfirm = jest.fn();
        const onCancel = jest.fn();
        const { unmount } = render(
            <ConfirmModal isOpen title="Видалити?" message="«Турнікети» (Київ)" details="Буде втрачено 10"
                          confirmText="Видалити" onConfirm={onConfirm} onCancel={onCancel} />
        );
        expect(screen.getByText('«Турнікети» (Київ)')).toBeInTheDocument();
        userEvent.click(screen.getByRole('button', { name: 'Видалити' }));
        userEvent.click(screen.getByRole('button', { name: 'Скасувати' }));
        expect([onConfirm.mock.calls.length, onCancel.mock.calls.length]).toEqual([1, 1]);
        unmount();
        render(<ConfirmModal isOpen message="m" loading onConfirm={() => {}} onCancel={() => {}} />);
        expect(screen.getByRole('button', { name: /ВИКОНАННЯ/ })).toBeDisabled();
    });

    test('8. Список з пошуком: пошук за словами в будь-якому порядку, вибір, клавіатура, відсутність результатів', () => {
        const options = [
            { value: 1, label: 'Відділення №5: вул. Соборна, 12' },
            { value: 2, label: 'Відділення №7: вул. Шевченка, 3' },
            { value: 3, label: 'Поштомат №1204' },
        ];
        const onChange = jest.fn();
        render(<SearchableSelect options={options} value="" onChange={onChange} placeholder="Оберіть..." />);
        const input = screen.getByRole('combobox');
        userEvent.click(input);
        userEvent.type(input, 'соборна 5');
        expect(screen.getByText(/Соборна/)).toBeInTheDocument();
        expect(screen.queryByText(/Шевченка/)).toBeNull();
        userEvent.clear(input);
        userEvent.type(input, 'неіснуючий запит');
        expect(screen.getByText('Нічого не знайдено')).toBeInTheDocument();
        userEvent.clear(input);
        userEvent.type(input, 'поштомат');
        fireEvent.keyDown(input, { key: 'Enter' });
        expect(onChange).toHaveBeenCalledWith('3');
        userEvent.click(input);
        expect(screen.getAllByRole('option').length).toBeGreaterThan(0);
        fireEvent.keyDown(input, { key: 'Escape' });
        expect(screen.queryAllByRole('option').length).toBe(0);
    });

    test('9. Картка заявки: ключові дані, пріоритет лише для адміністратора, запасне призначення, доступ до редагування', () => {
        const purposeMap = { 1: { label: 'Рятувальні служби (ДСНС)', icon: PURPOSE_MAP.rescue.icon, color: PURPOSE_MAP.rescue.color } };
        const req = {
            id: 1, resource_name: 'Турнікети CAT', purpose: 1, status: 'new', priority: 8.4, user_full_name: 'Іван Петренко',
            city: 'Харків', due_date: '2026-12-01', quantity_requested: 40, quantity_allocated: 10, auto_extend: true,
        };
        const onOpen = jest.fn();
        const { rerender } = render(<RequestCard req={req} purposeMap={purposeMap} isAdmin={false} onOpenModal={onOpen} />);
        ['Турнікети CAT', 'Іван Петренко', 'Харків', 'Нова', 'Рятувальні служби (ДСНС)', '10', '40'].forEach((t) => expect(screen.getByText(t)).toBeInTheDocument());
        expect(screen.queryByText('8.4')).toBeNull();
        userEvent.click(screen.getByText('10').closest('button'));
        expect(onOpen).toHaveBeenCalledWith(req);

        rerender(<RequestCard req={req} purposeMap={purposeMap} isAdmin onOpenModal={onOpen} />);
        expect(screen.getByText('8.4')).toBeInTheDocument();
        rerender(<RequestCard req={{ ...req, purpose: 999 }} purposeMap={purposeMap} isAdmin={false} onOpenModal={onOpen} />);
        expect(screen.getByText('Інше')).toBeInTheDocument();
        rerender(<RequestCard req={{ ...req, status: 'done' }} purposeMap={purposeMap} isAdmin={false} onOpenModal={onOpen} />);
        expect(screen.getByText('10').closest('button')).toBeDisabled();             // виконані недоступні користувачу
        rerender(<RequestCard req={{ ...req, status: 'done' }} purposeMap={purposeMap} isAdmin onOpenModal={onOpen} />);
        expect(screen.getByText('10').closest('button')).not.toBeDisabled();
    });
});

// ---------------------------------------------------------------------------
describe('Безпека та доступність коду', () => {
    const SRC = path.resolve(__dirname, '..');
    const listFiles = (dir) => fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
        const full = path.join(dir, e.name);
        if (e.isDirectory()) return e.name === '__tests__' ? [] : listFiles(full);
        return /\.(js|jsx)$/.test(e.name) ? [full] : [];
    });
    const files = listFiles(SRC);
    const read = (f) => fs.readFileSync(f, 'utf8');

    test('10. Безпека клієнтського коду: немає небезпечного HTML, eval, жорстко записаних секретів; JWT лише в сервісах', () => {
        expect(files.filter((f) => /dangerouslySetInnerHTML|\.innerHTML\s*=/.test(read(f)))).toEqual([]);
        expect(files.filter((f) => /\beval\(|new Function\(/.test(read(f)))).toEqual([]);
        expect(files.filter((f) => /(api[_-]?key|secret)\s*[:=]\s*['"][^'"]{8,}['"]/i.test(read(f)))).toEqual([]);
        const tokenUsers = files.filter((f) => /localStorage\.(set|get)Item\(\s*['"](access_token|refresh_token)/.test(read(f)));
        expect(tokenUsers.every((f) => /services[\\/](authService|api)\.js$/.test(f))).toBe(true);
    });

    test('11. Доступність: підписи кнопок-іконок, мова документа, viewport для мобільних пристроїв', () => {
        expect(read(path.join(SRC, 'components/UI/Modal.js'))).toMatch(/aria-label="Закрити вікно"/);
        expect(read(path.join(SRC, 'components/Auth/Auth.js'))).toMatch(/aria-label=\{visible \? 'Сховати пароль' : 'Показати пароль'\}/);
        const html = fs.readFileSync(path.resolve(SRC, '../public/index.html'), 'utf8');
        expect(html).toMatch(/<html[^>]*lang="uk"/);
        expect(html).toMatch(/name="viewport"/);
    });

    test('12. Сумісність браузерів: конфігурація browserslist (сучасні браузери, без застарілих)', () => {
        const pkg = JSON.parse(fs.readFileSync(path.resolve(SRC, '../package.json'), 'utf8'));
        const prod = pkg.browserslist.production.join(' ');
        expect(prod).toMatch(/>0\.2%/);
        expect(prod).toMatch(/not dead/);
        expect(prod).not.toMatch(/\bie\s*(6|7|8|9|10|11)\b/i);
        const dev = pkg.browserslist.development.join(' ');
        ['chrome', 'firefox', 'safari'].forEach((b) => expect(dev).toMatch(new RegExp(b)));
    });
});
