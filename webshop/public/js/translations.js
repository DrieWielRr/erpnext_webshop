// translations.js

let translations = {};
let currentLang =
    frappe?.boot?.lang ||
    document.documentElement.lang ||
    "en";

async function loadTranslations(lang = currentLang) {
    const res = await fetch("./translations.json");
    const data = await res.json();

    translations = data;
    currentLang = lang;
}

function translate(key, capitalize = false, lang = currentLang) {
    if (!key) return key;

    const lookupKey = String(key).toLowerCase().trim();

    const dictLang = translations[lang] || translations.en || {};
    const dictEn = translations.en || {};

    const translated = dictLang[lookupKey] || dictEn[lookupKey] || key;

    if (capitalize) {
        const startsWithCapital =
            key.charAt(0) === key.charAt(0).toUpperCase() &&
            key.charAt(0) !== key.charAt(0).toLowerCase();

        if (startsWithCapital) {
            return translated.charAt(0).toUpperCase() + translated.slice(1);
        } else {
            return translated.toLowerCase();
        }
    }

    return translated;
}

// expose globally
window.translate = translate;
window.loadTranslations = loadTranslations;