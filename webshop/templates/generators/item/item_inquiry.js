function waitForTranslations(timeout = 5000) {
	return new Promise((resolve, reject) => {
		const start = Date.now();

		const check = () => {
			if (
				frappe._messages &&
				Object.keys(frappe._messages).length > 0
			) {
				resolve();
				return;
			}

			if (Date.now() - start >= timeout) {
				reject(new Error("Translations did not load in time"));
				return;
			}

			setTimeout(check, 50);
		};

		check();
	});
}


frappe.ready(() => {
	console.log("Translations loading..");
	waitForTranslations()
		.then(() => {
			console.log("Translations ready:", frappe._messages);

	const d = new frappe.ui.Dialog({
		title: __('Contact Us'),
		fields: [
			{
				fieldtype: 'Data',
				label: __('Full Name'),
				fieldname: 'lead_name',
				reqd: 1
			},
			{
				fieldtype: 'Data',
				label: __('Organization Name'),
				fieldname: 'company_name',
			},
			{
				fieldtype: 'Data',
				label: __('Email'),
				fieldname: 'email_id',
				options: 'Email',
				reqd: 1
			},
			{
				fieldtype: 'Data',
				label: __('Phone Number'),
				fieldname: 'phone',
				options: 'Phone',
				reqd: 1
			},
			{
				fieldtype: 'Data',
				label: __('Subject'),
				fieldname: 'subject',
				reqd: 1
			},
			{
				fieldtype: 'Text',
				label: __('Message'),
				fieldname: 'message',
				reqd: 1
			}
		],
		primary_action: send_inquiry,
		primary_action_label: __('Send')
	});

	function send_inquiry() {
		const values = d.get_values();
		const doc = Object.assign({}, values);
		delete doc.subject;
		delete doc.message;

		d.hide();

		frappe.call('webshop.webshop.shopping_cart.cart.create_lead_for_item_inquiry', {
			lead: doc,
			subject: values.subject,
			message: values.message
		}).then(r => {
			if (r.message) {
				d.clear();
			}
		});
	}

	$('.btn-inquiry').click((e) => {
		const $btn = $(e.target);
		const item_code = $btn.data('item-code');
		d.set_value('subject', 'Inquiry about ' + item_code);
		if (!['Administrator', 'Guest'].includes(frappe.session.user)) {
			d.set_value('email_id', frappe.session.user);
			d.set_value('lead_name', frappe.get_cookie('full_name'));
		}

		d.show();
	});
});
