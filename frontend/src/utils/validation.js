// Загальні правила валідації форм (використовуються у формі входу та реєстрації)

export const NAME_REGEX = /^[\p{L}\s'-]+$/u;

// Email: щось@домен.зона (без пробілів, з крапкою в домені)
export const EMAIL_REGEX = /^[^\s@]+@[^\s@.]+(\.[^\s@.]+)+$/;

export const MIN_PASSWORD_LENGTH = 8;

export const phoneDigits = (v) => (v || '').replace(/\D/g, '');

const MASK_PREFIX = '+380 (';

// Маска телефона: +380 (XX) XXX-XX-XX - приймає лише цифри.
// Працює і при посимвольному введенні (включно з ручним "+380"), і при вставленні готового номера.
export const formatPhone = (raw) => {
    const text = (raw || '').toString();
    let local;

    if (text.startsWith(MASK_PREFIX)) {
        // значення вже відформатоване нашою маскою (редагування або стирання)
        local = phoneDigits(text.slice(MASK_PREFIX.length));
    } else if (text.trim().startsWith('+')) {
        // користувач вводить код країни вручну
        const d = phoneDigits(text);
        if (d.length <= 3 && '380'.startsWith(d)) return '+' + d;
        local = d.startsWith('380') ? d.slice(3) : d;
    } else {
        const d = phoneDigits(text);
        if (d.startsWith('380')) local = d.slice(3);
        else if (d.startsWith('80')) local = d.slice(2);
        else if (d.startsWith('0')) local = d.slice(1);
        else local = d;
    }

    local = local.slice(0, 9);
    if (!local) return '';
    let out = MASK_PREFIX + local.slice(0, 2);
    if (local.length > 2) out += ') ' + local.slice(2, 5);
    if (local.length > 5) out += '-' + local.slice(5, 7);
    if (local.length > 7) out += '-' + local.slice(7, 9);
    return out;
};

export const isValidPhone = (v) => phoneDigits(v).length === 12;
