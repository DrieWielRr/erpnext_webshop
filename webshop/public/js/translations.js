let currentLang = (document.documentElement.lang || "en").toLowerCase();
let translations = {};
let fallbackTranslations = {};

async function loadTranslations() {
    try {
        const [langRes, enRes] = await Promise.all([
            fetch(`/translations/${currentLang}.json`),
            fetch(`/translations/en.json`)
        ]);

        translations = await langRes.json();
        fallbackTranslations = await enRes.json();
        frappe._messages = translations;

        console.log(
            `[translations] loaded ${currentLang}: ${Object.keys(translations).length} entries`
        );

    } catch (err) {
        console.error("[translations] failed loading:", err);

        translations = {};
        fallbackTranslations = {};
    }
}

function translate(key, capitalize = false) {
    if (!key) return key;

    const original = String(key);
    const lookupKey = original.toLowerCase().trim();

    let translated =
        translations[lookupKey] ||
        fallbackTranslations[lookupKey] ||
        original;

    if (capitalize) {
        const startsWithCapital =
            original.charAt(0) === original.charAt(0).toUpperCase() &&
            original.charAt(0) !== original.charAt(0).toLowerCase();

        if (startsWithCapital) {
            translated =
                translated.charAt(0).toUpperCase() +
                translated.slice(1);
        } else {
            translated = translated.toLowerCase();
        }
    }

    return translated;
}

window.translate = translate;
window.loadTranslations = loadTranslations;