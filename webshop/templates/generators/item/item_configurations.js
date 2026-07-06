class ItemConfigurations {

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
						// Filtering is always based on the original database value (v.value)
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
					
					// store original data
					div.setAttribute("data-raw-value", v.value);					

					const priceText = v.custom_price > 0
						? ` (+€${v.custom_price})`
						: "";				
						
					// store original custom price data string
					div.setAttribute("data-customPrice-value", v.value);

					// Display the TRANSLATED value to the user in the interface
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

							// Check against the original object (v), so v.value remains "Red"
							if (!combo._selected.find(x => x.value === v.value)) {
								combo._selected.push(v); // Stores the entire original object (including the raw value)
								renderTags(combo);
							}

							input.value = "";
							dropdown.style.display = "none";
							updateClearVisibility();
							UpdatePricing(false);
							return;
						}

						// SINGLE SELECT MODE

						// Store the original object in the state so the underlying logic remains correct
						combo._selected = v; 
						input.dataset.rawValue = v.value;

						// Display the translated version in the input field for the user
						const priceText = v.custom_price > 0
						? ` (+€${v.custom_price})`
						: "";							
						input.value = translate(v.value, true) + priceText; 

						updateClearVisibility();

						dropdown.style.display = "none";
						UpdatePricing(false);
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
					
					// store original data
					tag.setAttribute("data-raw-value", v.value);
					
					const priceText = v.custom_price > 0
						? ` (+€${v.custom_price})`
						: "";	

					// Display the TRANSLATED value to the user in the label
					tag.textContent = translate(v.value, true) + priceText;

					tag.onclick = () => {
						// Filtering still works safely using v.value ("Red" !== "Blue")
						combo._selected =
							combo._selected.filter(x => x.value !== v.value);

						renderTags(combo);
						updateClearVisibility();
						UpdatePricing(false);
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
				input.dataset.rawValue = "";

				// clear selected state
				combo._selected = allowMulti ? [] : null;

				// remove tags visually
				renderTags(combo);

				// hide dropdown
				dropdown.style.display = "none";

				// update clear button visibility
				updateClearVisibility();

				// recalculate total
				UpdatePricing(false);
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
						UpdatePricing(false);
						return;
					}

					// SINGLE MODE
					if (!allowCustom) {

						if (combo._selected) {

							const priceText = combo._selected.custom_price > 0
								? ` (+€${combo._selected.custom_price})`
								: "";

							input.value =
								translate(combo._selected.value, true) + priceText;
						}
						else {
							input.value = "";
						}
					}

					dropdown.style.display = "none";
					updateClearVisibility();
					UpdatePricing(false);

				}, 150);
			});
			
		});	

		log("[ItemConfigurations] initCombos completed");		
	}
}