// Copyright (c) 2026, corex and contributors
// For license information, please see license.txt

frappe.ui.form.on('Game Lesson', {
    refresh: function(frm) {
        // عند التحميل
        frm.trigger('toggle_topic_field');
    },
    unit: function(frm) {
        // عند تغيير الوحدة
        frm.trigger('toggle_topic_field');
    },
    toggle_topic_field: function(frm) {
        if (frm.doc.unit) {
            frappe.db.get_value('Game Unit', frm.doc.unit, 'structure_type')
            .then(r => {
                if (r && r.message && r.message.structure_type == 'Topic Based') {
                    // اظهر حقل التوبيك واجعله اجباري
                    frm.set_df_property('topic', 'hidden', 0);
                    frm.set_df_property('topic', 'reqd', 1);
                } else {
                    // اخفِ حقل التوبيك واجعله غير اجباري
                    frm.set_df_property('topic', 'hidden', 1);
                    frm.set_df_property('topic', 'reqd', 0);
                    frm.set_value('topic', null);
                }
            });
        }
    }
});