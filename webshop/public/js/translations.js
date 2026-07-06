// translations.js

let currentLang = document.documentElement.lang || "en";
let translations = {};

async function loadTranslations() {
    const res = await fetch("/assets/webshop/translations.json");
    translations = await res.json();
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