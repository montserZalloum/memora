frappe.ui.form.on('Game Lesson', {
    refresh: function(frm) {
        // 
    }
});

frappe.ui.form.on('Game Stage', {
    edit_content_btn: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        if (!row.type) {
            frappe.msgprint("الرجاء اختيار نوع المرحلة أولاً");
            return;
        }

        // نستخدم with_doctype للتأكد من وجود الموديل الأساسي فقط
        frappe.model.with_doctype('Game Content Builder Item', function() {
            
            let current_config = {};
            if (row.config) {
                try {
                    current_config = JSON.parse(row.config);
                } catch (e) {
                    console.error("Invalid JSON", e);
                }
            }

            if (row.type === 'Matching') {
                open_matching_dialog(frm, cdt, cdn, row, current_config);
            } else if (row.type === 'Reveal') {
                open_reveal_dialog(frm, cdt, cdn, row, current_config);
            } else {
                frappe.msgprint("لا يوجد محرر لهذا النوع بعد");
            }
        });
    }
});

// =================================================
// 🧩 1. نافذة إعدادات التوصيل (Matching)
// =================================================
function open_matching_dialog(frm, cdt, cdn, row, data) {
    let existing_data = (data.pairs || []).map(p => ({
        item_1: p.right,
        item_2: p.left
    }));

    let d = new frappe.ui.Dialog({
        title: 'إعدادات التوصيل (Matching)',
        fields: [
            {
                label: 'التعليمات',
                fieldname: 'instruction',
                fieldtype: 'Data',
                default: data.instruction || 'طابق العناصر'
            },
            {
                label: 'الأزواج',
                fieldname: 'pairs_table',
                fieldtype: 'Table',
                options: 'Game Content Builder Item',
                // 👇 الحل السحري: تعريف الحقول يدوياً هنا
                fields: [
                    {
                        label: 'اليمين (Right)', // نحدد الاسم هنا مباشرة
                        fieldname: 'item_1',
                        fieldtype: 'Data',
                        in_list_view: 1,
                        reqd: 1
                    },
                    {
                        label: 'اليسار (Left)',
                        fieldname: 'item_2',
                        fieldtype: 'Data',
                        in_list_view: 1,
                        reqd: 1
                    }
                ],
                data: existing_data,
                get_data: () => existing_data
            }
        ],
        size: 'large',
        primary_action_label: 'حفظ (Save)',
        primary_action: function(values) {
            let config_payload = {
                instruction: values.instruction,
                pairs: values.pairs_table.map((p, index) => ({
                    id: String(index + 1),
                    right: p.item_1,
                    left: p.item_2
                }))
            };
            frappe.model.set_value(cdt, cdn, 'config', JSON.stringify(config_payload, null, 2));
            d.hide();
            frappe.show_alert({message: 'تم الحفظ ✅', indicator: 'green'});
        }
    });

    d.show();
}

// =================================================
// 🔍 2. نافذة إعدادات الكشف (Reveal)
// =================================================
function open_reveal_dialog(frm, cdt, cdn, row, data) {
    let existing_data = (data.highlights || []).map(h => ({
        item_1: h.word,
        item_2: h.explanation
    }));

    let d = new frappe.ui.Dialog({
        title: 'إعدادات الكشف (Reveal)',
        fields: [
            {
                label: 'الأيقونة (Emoji)',
                fieldname: 'image',
                fieldtype: 'Data',
                default: data.image
            },
            {
                label: 'الجملة',
                fieldname: 'sentence',
                fieldtype: 'Small Text',
                reqd: 1,
                default: data.sentence
            },
            {
                label: 'الكلمات',
                fieldname: 'highlights_table',
                fieldtype: 'Table',
                options: 'Game Content Builder Item',
                // 👇 تعريف الحقول يدوياً هنا أيضاً
                fields: [
                    {
                        label: 'الكلمة (Word)',
                        fieldname: 'item_1',
                        fieldtype: 'Data',
                        in_list_view: 1,
                        reqd: 1
                    },
                    {
                        label: 'الشرح (Explanation)',
                        fieldname: 'item_2',
                        fieldtype: 'Data',
                        in_list_view: 1
                    }
                ],
                data: existing_data,
                get_data: () => existing_data
            }
        ],
        size: 'large',
        primary_action_label: 'حفظ (Save)',
        primary_action: function(values) {
            let config_payload = {
                image: values.image,
                sentence: values.sentence,
                highlights: values.highlights_table.map(h => ({
                    word: h.item_1,
                    explanation: h.item_2
                }))
            };
            frappe.model.set_value(cdt, cdn, 'config', JSON.stringify(config_payload, null, 2));
            d.hide();
            frappe.show_alert({message: 'تم الحفظ ✅', indicator: 'green'});
        }
    });

    d.show();
}