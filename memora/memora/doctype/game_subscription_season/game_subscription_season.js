frappe.ui.form.on("Game Subscription Season", {
	refresh(frm) {
		if (frm.doc.enable_redis && frm.doc.partition_created) {
			if (frm.page.custom_buttons_added) return;

			frm.add_custom_button(__("Rebuild Cache"), () => {
				frappe.confirm(
					__(
						"This will rebuild the Redis cache for this season. " +
						"This may take several minutes for large datasets. " +
						"Are you sure you want to continue?"
					),
					() => {
						frappe.call({
							method: "memora.api.srs.rebuild_season_cache",
							args: {
								season_name: frm.doc.season_name
							},
							freeze: true,
							callback(r) {
								if (r.message?.status === "started") {
									frappe.msgprint({
										message: __(
											"Cache rebuild started. Estimated {0} records to process.",
											[r.message.estimated_records]
										),
										indicator: "blue",
										title: __("Cache Rebuild")
									});
								} else {
									frappe.msgprint({
										message: __(
											"Failed to start cache rebuild: {0}",
											[r.message?.error || "Unknown error"]
										),
										indicator: "red",
										title: __("Cache Rebuild")
									});
								}
							}
						});
					}
				);
			});

			frm.page.custom_buttons_added = true;
		}
	}
});
