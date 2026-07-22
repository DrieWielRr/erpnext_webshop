if (!window.ItemConfigurations) {
    
    window.ItemConfigurations = class ItemConfigurations {

        static initFromServer(data) {
            log("[ItemConfigurations] initFromServer started", data);
            
            const container = document.querySelector("#configurator");
            if (!container) {
                log("[ItemConfigurations] Error: #configurator not found");
                return;
            }

            this.initCombos(container, data);       
            log("[ItemConfigurations] initFromServer completed");        
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

				combo._selected = allowMulti ? [] : null;

				function updateClearVisibility() {
					const hasText = input.value.trim().length > 0;
					const hasSelection = allowMulti ? combo._selected.length > 0 : !!combo._selected;
					clearBtn.style.display = (hasText || hasSelection) ? "block" : "none";
				}

				function renderDropdown(filter = "") {
					dropdown.innerHTML = "";
					if (!attr) return;

					const filtered = attr.values.filter(v => {
						const matchesFilter = v.value.toLowerCase().includes(filter.toLowerCase());
						let isAlreadySelected = allowMulti 
							? combo._selected.some(x => x.value === v.value)
							: (combo._selected && combo._selected.value === v.value);

						return matchesFilter && !isAlreadySelected;
					});

					filtered.forEach(v => {                 
						const div = document.createElement("div");
						div.className = "combo-item";
						div.setAttribute("data-raw-value", v.value);                     
						div.setAttribute("data-customPrice-value", v.value);

						const priceText = v.custom_price != 0 ? ` (${v.custom_price > 0 ? "+" : "-"}€${Math.abs(v.custom_price)})` : "";            
						div.textContent = (window.translate ? translate(v.value, true) : v.value) + priceText;

						div.onclick = () => {
							if (allowMulti) {
								const max = Number(combo.dataset.max || 0);
								if (max > 0 && combo._selected.length >= max) {
									frappe.show_alert({
										message: `${window.translate ? translate('You can only select') : 'You can only select'} ${max} ${window.translate ? translate('items for') : 'items for'} "${window.translate ? translate(attrName, true) : attrName}"`,
										indicator: "orange"
									});
									return;
								}

								if (!combo._selected.find(x => x.value === v.value)) {
									combo._selected.push(v);
									renderTags(combo);
								}
								input.value = "";
								dropdown.style.display = "none";
								updateClearVisibility();
								if (typeof UpdatePricing === 'function') UpdatePricing(false);
								return;
							}

							combo._selected = v; 
							input.dataset.rawValue = v.value;
							input.value = (window.translate ? translate(v.value, true) : v.value) + priceText; 

							updateClearVisibility();
							dropdown.style.display = "none";
							if (typeof UpdatePricing === 'function') UpdatePricing(false);
						};

						dropdown.appendChild(div);
					});

					dropdown.style.display = filtered.length > 0 ? "block" : "none";
				}

				function renderTags(combo) {
					let tagBox = combo.querySelector(".tag-box");
					if (!tagBox) return;

					tagBox.innerHTML = "";
					if (!combo._selected || combo._selected.length === 0) {
						tagBox.style.display = "none";
						return;
					}

					tagBox.style.display = "flex";
					combo._selected.forEach(v => {
						const tag = document.createElement("span");
						tag.className = "tag";
						tag.setAttribute("data-raw-value", v.value);
						
						const priceText = v.custom_price > 0 ? ` (+€${v.custom_price})` : "";   
						tag.textContent = (window.translate ? translate(v.value, true) : v.value) + priceText;

						tag.onclick = () => {
							combo._selected = combo._selected.filter(x => x.value !== v.value);
							renderTags(combo);
							updateClearVisibility();
							if (typeof UpdatePricing === 'function') UpdatePricing(false);
						};
						tagBox.appendChild(tag);
					});
				}

				clearBtn.addEventListener("click", (e) => {
					e.preventDefault();
					e.stopPropagation();
					input.value = "";
					input.dataset.rawValue = "";
					combo._selected = allowMulti ? [] : null;
					renderTags(combo);
					dropdown.style.display = "none";
					updateClearVisibility();
					if (typeof UpdatePricing === 'function') UpdatePricing(false);
				});
				
				input.addEventListener("input", () => {
					updateClearVisibility();
					renderDropdown(input.value);
				});

				input.addEventListener("focus", () => {
					updateClearVisibility();
					renderDropdown(input.value);
				});

				input.addEventListener("blur", () => {
					setTimeout(() => {
						const typedValue = input.value.trim();
						const match = attr ? attr.values.find(v => v.value.toLowerCase() === typedValue.toLowerCase()) : null;

						if (allowMulti) {
							if (!match && allowCustom && typedValue !== "") {
								const customValue = { value: typedValue, custom_price: 0 };
								if (!combo._selected.find(x => x.value === typedValue)) {
									combo._selected.push(customValue);
									renderTags(combo);
								}
							}
							input.value = "";
							dropdown.style.display = "none";
							updateClearVisibility();
							if (typeof UpdatePricing === 'function') UpdatePricing(false);
							return;
						}

						if (!allowCustom) {
							if (combo._selected) {
								const priceText = combo._selected.custom_price > 0 ? ` (+€${combo._selected.custom_price})` : "";
								input.value = (window.translate ? translate(combo._selected.value, true) : combo._selected.value) + priceText;
							} else {
								input.value = "";
							}
						}

						dropdown.style.display = "none";
						updateClearVisibility();
						if (typeof UpdatePricing === 'function') UpdatePricing(false);
					}, 150);
				});
			}); 

			log("[ItemConfigurations] initCombos completed");       
		}
    }
}