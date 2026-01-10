frappe.ui.form.on('Game Lesson', {
    refresh: function(frm) {
        // 
    },
    // This function runs before the document is saved
    validate: function(frm) {
        let missing_content = false;
        let incomplete_rows = [];

        // 1. Check if the child table itself is empty
        if (!frm.doc.stages || frm.doc.stages.length === 0) {
            frappe.throw({
                title: __("خطأ في التحقق"),
                message: __("يجب إضافة مرحلة واحدة على الأقل قبل حفظ الدرس."),
                indicator: 'red'
            });
        }

        // 2. Loop through each row in the child table (assumed fieldname is 'stages')
        frm.doc.stages.forEach(row => {
            // Check if 'config' is empty or just an empty JSON object
            if (!row.config || row.config.trim() === "" || row.config === "{}") {
                missing_content = true;
                incomplete_rows.push(row.idx); // Keep track of the row index
            }
        });

        if (missing_content) {
            // Stop the saving process
            frappe.validated = false;
            
            frappe.msgprint({
                title: __("محتوى ناقص"),
                indicator: 'red',
                message: __("لا يمكن الحفظ: المراحل رقم ({0}) تفتقر إلى المحتوى. يرجى الضغط على 'Edit Content' وإعدادها أولاً.", [incomplete_rows.join(', ')])
            });
            
            // Throwing an exception also stops the save and shows a red message
            frappe.throw(__("يرجى إكمال إعدادات جميع المراحل قبل الحفظ."));
        }
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
            } else if (row.type === 'Sentence Builder') {
                open_sentence_builder_dialog(frm, cdt, cdn, row, current_config);
            } else if (row.type === 'Fill Blank') {
                open_fill_blank_dialog(frm, cdt, cdn, row, current_config);
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

// =================================================
// 🏗️ 3. نافذة بناء الجملة (Sentence Builder)
// =================================================
function open_sentence_builder_dialog(frm, cdt, cdn, row, data) {
    // تجهيز البيانات القديمة إذا كانت موجودة
    let existing_data = (data.words || []).map(w => ({
        item_1: w
    }));

    let d = new frappe.ui.Dialog({
        title: 'إعدادات بناء الجملة (Sentence Builder)',
        fields: [
            {
                label: 'التعليمات',
                fieldname: 'instruction',
                fieldtype: 'Data',
                default: data.instruction || 'رتب الكلمات لتكوين جملة صحيحة',
                description: 'مثال: رتب الكلمات التالية'
            },
            {
                fieldtype: 'Section Break',
                label: 'محتوى الجملة'
            },
            {
                label: 'الجملة الكاملة (للمراجعة)',
                fieldname: 'sentence',
                fieldtype: 'Small Text',
                default: data.sentence,
                description: 'اكتب الجملة كاملة هنا كمرجع'
            },
            {
                label: 'الكلمات/المقاطع مرتبة (Words Tokens)',
                fieldname: 'words_table',
                fieldtype: 'Table',
                options: 'Game Content Builder Item',
                description: 'أضف الكلمات بالترتيب الصحيح. ملاحظة: يمكنك إضافة عبارة كاملة في سطر واحد لتظهر كزر واحد (مثل: حق إصدار العملة)',
                fields: [
                    {
                        label: 'الكلمة / العبارة',
                        fieldname: 'item_1',
                        fieldtype: 'Data',
                        in_list_view: 1,
                        reqd: 1
                    }
                ],
                data: existing_data
            }
        ],
        size: 'large',
        primary_action_label: 'حفظ (Save)',
        primary_action: function(values) {
            // تحويل الجدول إلى مصفوفة نصوص بسيطة للـ React
            let words_array = values.words_table.map(row => row.item_1);

            let config_payload = {
                instruction: values.instruction,
                sentence: values.sentence,
                words: words_array // سيتم إرسالها كـ Array من الكلمات
            };

            // حفظ الـ JSON في حقل الـ Config
            frappe.model.set_value(cdt, cdn, 'config', JSON.stringify(config_payload, null, 2));
            
            d.hide();
            frappe.show_alert({message: 'تم حفظ إعدادات الجملة ✅', indicator: 'green'});
        }
    });

    d.show();
}

// =================================================
// 📝 4. نافذة ملء الفراغ (Fill Blank)
// =================================================
function open_fill_blank_dialog(frm, cdt, cdn, row, data) {
    // تجهيز الكلمات المضللة القديمة
    let existing_distractors = (data.distractors || []).map(d => ({
        item_1: d
    }));

    let d = new frappe.ui.Dialog({
        title: 'إعدادات ملء الفراغ (Fill Blank)',
        fields: [
            {
                label: 'التعليمات',
                fieldname: 'instruction',
                fieldtype: 'Data',
                default: data.instruction || 'اسحب الكلمة المناسبة إلى الفراغ'
            },
            {
                label: 'الجملة مع الفراغات',
                fieldname: 'sentence',
                fieldtype: 'Small Text',
                reqd: 1,
                default: data.sentence,
                description: 'ضع الكلمة المراد إخفاؤها بين أقواس متعرجة. مثال: تقع مدينة {البتراء} في جنوب {الأردن}.'
            },
            {
                fieldtype: 'Section Break',
                label: 'الخيارات الإضافية'
            },
            {
                label: 'كلمات مضللة (Distractors)',
                fieldname: 'distractors_table',
                fieldtype: 'Table',
                options: 'Game Content Builder Item',
                description: 'أضف كلمات خاطئة لتظهر مع الخيارات (لتصعيب الحل)',
                fields: [
                    {
                        label: 'الكلمة المضللة',
                        fieldname: 'item_1',
                        fieldtype: 'Data',
                        in_list_view: 1,
                        reqd: 1
                    }
                ],
                data: existing_distractors
            }
        ],
        size: 'large',
        primary_action_label: 'حفظ (Save)',
        primary_action: function(values) {
            // 1. استخراج الكلمات الصحيحة من الجملة باستخدام Regex
            // يبحث عن أي شيء بين { }
            let blanks = [];
            let regex = /\{(.*?)\}/g;
            let match;
            while ((match = regex.exec(values.sentence)) !== null) {
                blanks.push(match[1]);
            }

            if (blanks.length === 0) {
                frappe.msgprint("يجب وضع كلمة واحدة على الأقل بين أقواس { }");
                return;
            }

            // 2. تجهيز البيانات للـ JSON
            let config_payload = {
                instruction: values.instruction,
                sentence: values.sentence, // الجملة الخام: "تقع {البتراء} في {الأردن}"
                blanks: blanks,           // الكلمات المستخرجة: ["البتراء", "الأردن"]
                distractors: values.distractors_table.map(row => row.item_1)
            };

            frappe.model.set_value(cdt, cdn, 'config', JSON.stringify(config_payload, null, 2));
            
            d.hide();
            frappe.show_alert({message: 'تم حفظ إعدادات الفراغات ✅', indicator: 'green'});
        }
    });

    d.show();
}