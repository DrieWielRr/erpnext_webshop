// 1. Move these OUTSIDE and ABOVE the class definition
let CONFIGURATOR_BASE_PRICE = null;
let CONFIGURATOR_MIN_QTY = 1;

class ItemConfigurations {

    static injectConfiguratorStyles() {
		log("[ItemConfigurations] injectConfiguratorStyles started");        
        const style_id = "item_configurator.style";
        if (document.querySelector(`#${style_id}`)) return;

        const style = document.createElement("style");
        style.id = style_id;
        style.innerHTML = `
            .config-attribute { margin-bottom: 12px; }
            .input-row { position: relative; display: flex; align-items: center; }
            .config-label { display: block; margin-bottom: 0px; font-weight: 500; }
            .combo { position: relative; width: 75%; }
            .combo-input { width: 100%; padding-right: 30px; box-sizing: border-box; }
            .combo-clear { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); cursor: pointer; display: none; }
            .combo-dropdown { position: absolute; top: 100%; left: 0; right: 0; max-height: 200px; overflow-y: auto; background: white; border: 1px solid #ddd; z-index: 9999; display: none; }
            .combo-item { padding: 6px; cursor: pointer; }
            .combo-item:hover { background: #f2f2f2; }
            .tag-box { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 6px; }
            .tag { background: #eee; padding: 4px 8px; border-radius: 12px; font-size: 12px; cursor: pointer; }
            .combo-clear:hover { color: #333; }
        `;
        document.head.appendChild(style);
		log("[ItemConfigurations] injectConfiguratorStyles completed");        
    }

    static buildConfigurator(data, root) {
        log("[ItemConfigurations] buildConfigurator started", data);
        
        let container = root.querySelector("#configurator");
        if (!container) {
            container = document.createElement("div");
            container.id = "configurator";
            root.querySelector(".product-code")?.append(container);
        }

        let html = "<br>";
        data.attributes.forEach(attr => {
            html += `<div class="config-attribute">`;
            if (Number(attr.custom_checkbox_free_text) === 1) {
                html += `<label class="config-label">${window.translate ? translate(attr.attribute, true) : attr.attribute} (${window.translate ? translate('wishes') : 'wishes'})</label>`;
            } else if (Number(attr.custom_checkbox_multi_select) === 1) {
                let maxSelect = Number(attr.custom_max_select) || 99;
                html += `<label class="config-label">${window.translate ? translate(attr.attribute, true) : attr.attribute} (${window.translate ? translate('selectUpTo') : 'Select up to'} ${maxSelect} ${window.translate ? translate('items', true) : 'items'}):</label>`;
            } else {
                html += `<label class="config-label">${window.translate ? translate(attr.attribute, true) : attr.attribute}:</label>`;
            }

            html += `
                <div class="combo"
                    data-id="${attr.id}"
                    data-attribute="${attr.attribute}"
                    data-multi="${Number(attr.custom_checkbox_multi_select) === 1 ? 1 : 0}"
                    data-max="${Number(attr.custom_max_select) || 99}"
                    data-allow-custom="${Number(attr.custom_checkbox_free_text) === 1 ? 1 : 0}">
                    <div class="tag-box"></div>
                    <div class="input-row">
                        <input type="text" id="${attr.id}" class="combo-input" placeholder="Select ${attr.attribute}" autocomplete="off">
                        <span class="combo-clear">×</span>
                    </div>
                    <div class="combo-dropdown"></div>
                </div>
            `;
            html += `</div>`;
        });

        container.innerHTML = html;
        
        // 2. These functions can now read/write CONFIGURATOR_BASE_PRICE seamlessly
		
        if (typeof initBasePrice === "function") initBasePrice(data);
        this.initCombos(container, data);
		
		log("[ItemConfigurations] buildConfigurator completed");        
    }
	
	static initCombos(container, data) {
		log("[ItemConfigurations] initCombos started");		
		
		container.querySelectorAll(".combo").forEach(combo => {

			const input = combo.querySelector(".combo-input");
			const dropdown = combo.querySelector(".combo-dropdown");
			const clearBtn = combo.querySelector(".combo-clear");

			const attrName = combo.dataset.attribute;
			const allowMulti = combo.dataset.multi === "1";
			const allowCustom = combo.dataset.allowCustom === "1";

			const attr = data.attributes.find(a => a.attribute === attrName);

			// state per combo
			combo._selected = allowMulti ? [] : null;

			function updateClearVisibility() {
				const hasText = input.value.trim().length > 0;
				const hasSelection = allowMulti
					? combo._selected.length > 0
					: !!combo._selected;

				clearBtn.style.display = (hasText || hasSelection) ? "block" : "none";
			}

			function renderDropdown(filter = "") {

				dropdown.innerHTML = "";

				const filtered = attr.values
					.filter(v => {
						// Filteren gebeurt altijd op basis van de originele database-waarde (v.value)
						const matchesFilter = v.value.toLowerCase().includes(filter.toLowerCase());
						
						let isAlreadySelected = false;
						if (allowMulti && Array.isArray(combo._selected)) {
							isAlreadySelected = combo._selected.some(x => x.value === v.value);
						} else if (!allowMulti && combo._selected) {
							isAlreadySelected = combo._selected.value === v.value;
						}

						return matchesFilter && !isAlreadySelected;
					});

				filtered.forEach(v => {					
					const div = document.createElement("div");
					div.className = "combo-item";
					
					// --- NIEUW: Sla de originele, onvertaalde waarde op in de HTML ---
					div.setAttribute("data-raw-value", v.value);

					const priceText = v.custom_price > 0
						? ` (+€${v.custom_price})`
						: "";

					// Toon de VERTAALDE waarde aan de gebruiker in de interface
					div.textContent = translate(v.value, true) + priceText;

					div.onclick = () => {

						// MULTI SELECT MODE
						if (allowMulti) {
							
							const max = getMax(combo);
							if (max > 0 && combo._selected.length >= max) {
								frappe.show_alert({
									message: `${translate('You can only select')} ${max} ${translate('items for')} "${translate(attr.attribute, true)}"`,
									indicator: "orange"
								});
								return;
							}

							// Controleer op basis van het originele object (v), dus v.value blijft "Red"
							if (!combo._selected.find(x => x.value === v.value)) {
								combo._selected.push(v); // Slaat het hele originele object op (inclusif raw value)
								renderTags(combo);
							}

							input.value = "";
							dropdown.style.display = "none";
							updateClearVisibility();
							updatePrice();
							return;
						}

						// SINGLE SELECT MODE
						// Toon de vertaalde versie in de inputbalk voor de gebruiker
						input.value = translate(v.value, true); 
						
						// Sla het originele object op in de staat, zodat je logica op de achtergrond klopt
						combo._selected = v; 
						updateClearVisibility();

						dropdown.style.display = "none";
						updatePrice();
					};

					dropdown.appendChild(div);
				});

				if (filtered.length > 0) {
					dropdown.style.display = "block";
				} else {
					dropdown.style.display = "none";
				}
			}



			function renderTags(combo) {

				let tagBox = combo.querySelector(".tag-box");

				if (!tagBox) {
					tagBox = document.createElement("div");
					tagBox.className = "tag-box";
					combo.prepend(tagBox);
				}

				// clear existing
				tagBox.innerHTML = "";

				// hide if no tags
				if (!combo._selected || combo._selected.length === 0) {
					tagBox.style.display = "none";
					return;
				}

				tagBox.style.display = "flex";

				combo._selected.forEach(v => {

					const tag = document.createElement("span");
					tag.className = "tag";
					
					// --- NIEUW: Sla de originele, onvertaalde waarde op in de HTML ---
					tag.setAttribute("data-raw-value", v.value);

					// Toon de VERTAALDE waarde aan de gebruiker op het label
					tag.textContent = translate(v.value, true);

					tag.onclick = () => {
						// Het filteren gebeurt nog steeds veilig op v.value ("Red" !== "Blue")
						combo._selected =
							combo._selected.filter(x => x.value !== v.value);

						renderTags(combo);
						updateClearVisibility();
						updatePrice();
					};

					tagBox.appendChild(tag);
				});
			}

			
			function getMax(combo) {
				return Number(combo.dataset.max || 0);
			}


			// INPUT EVENTS	
			clearBtn.addEventListener("click", (e) => {

				e.preventDefault();
				e.stopPropagation();

				// clear textbox
				input.value = "";

				// clear selected state
				combo._selected = allowMulti ? [] : null;

				// remove tags visually
				renderTags(combo);

				// hide dropdown
				dropdown.style.display = "none";

				// update clear button visibility
				updateClearVisibility();

				// recalculate total
				updatePrice();
			});
			
			input.addEventListener("input", () => {
				updateClearVisibility();
				renderDropdown(input.value);
			});

			input.addEventListener("focus", updateClearVisibility);
			
			input.addEventListener("focus", () => {
				renderDropdown(input.value);
			});

			input.addEventListener("input", () => {
				renderDropdown(input.value);
			});

			input.addEventListener("blur", () => {
				setTimeout(() => {

					const typedValue = input.value.trim();

					const match = attr.values.find(v =>
						v.value.toLowerCase() === typedValue.toLowerCase()
					);

					// MULTI MODE
					if (allowMulti) {

						// free text allowed → treat as new tag
						if (!match && allowCustom && typedValue !== "") {

							const customValue = {
								value: typedValue,
								custom_price: 0
							};

							if (!combo._selected.find(x => x.value === typedValue)) {
								combo._selected.push(customValue);
								renderTags(combo);
							}

						}

						input.value = "";
						dropdown.style.display = "none";
						updateClearVisibility();
						updatePrice();
						return;
					}

					// SINGLE MODE

					if (match) {
						combo._selected = match;
						input.value = match.value;
					}

					else if (allowCustom && typedValue !== "") {
						combo._selected = {
							value: typedValue,
							custom_price: 0
						};
					}

					else {
						input.value = "";
						combo._selected = null;
					}

					dropdown.style.display = "none";
					updateClearVisibility();
					updatePrice();

				}, 150);
			});
			
		});	

		log("[ItemConfigurations] initCombos completed");		
	}
}