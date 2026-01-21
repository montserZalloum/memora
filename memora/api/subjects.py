"""
Subjects & Tracks Domain Module

This module handles subject listing and track retrieval based on academic plan.
"""

import frappe
from frappe import _


@frappe.whitelist()
def get_subjects():
    """
    Get subjects based on user's academic plan (Seasonal version).

    Logic:
    1. Determine student's grade, stream, and CURRENT SEASON.
    2. Fetch the Academic Plan matching (Grade + Stream + Season).
    3. Display only subjects listed in that seasonal plan.
    """
    try:
        user = frappe.session.user
        
        # 1. جلب بيانات بروفايل الطالب (تعديل: جلب season بدلاً من academic_year)
        profile = frappe.db.get_value("Player Profile", {"user": user},
            ["current_grade", "current_stream", "season"], as_dict=True)

        # إذا لم يكمل الطالب إعدادات البروفايل أو لم يحدد الموسم
        if not profile or not profile.current_grade or not profile.season:
            return []

        # 2. البحث عن الخطة الأكاديمية للموسم الحالي
        # الفلتر الآن يعتمد على الموسم (Season)
        filters = {
            "grade": profile.current_grade,
            "season": profile.season  # 👈 التغيير هنا
        }

        # التخصص (Stream) قد يكون فارغاً في الصفوف الأساسية
        if profile.current_stream:
            filters["stream"] = profile.current_stream

        plan_name = frappe.db.get_value("Game Academic Plan", filters, "name")

        if not plan_name:
            # لم يتم العثور على خطة لهذا الموسم (خطأ في إدخال البيانات من الإدارة)
            return []

        # 3. جلب المواد من داخل هذه الخطة الموسمية
        plan_subjects = frappe.get_all("Game Plan Subject",
            filters={"parent": plan_name},
            fields=["subject", "display_name"],
            order_by="idx asc"
        )

        final_list = []

        for item in plan_subjects:
            # جلب تفاصيل المادة الأصلية (أيقونة، لون، هل هي مدفوعة)
            original_subject = frappe.db.get_value("Game Subject", item.subject,
                ["name", "title", "icon", "is_paid"], as_dict=True)

            if not original_subject: 
                continue

            # استخدام الاسم المخصص في الخطة (Display Name) إذا وجد، وإلا الاسم الأصلي
            title_to_show = item.display_name if item.display_name else original_subject.title

            final_list.append({
                "name": original_subject.name,   # المعرف البرمجي (مثلاً: math-10)
                "title": title_to_show,          # الاسم للعرض (مثلاً: رياضيات)
                "icon": original_subject.icon,
                "is_paid": original_subject.is_paid
            })

        return final_list

    except Exception as e:
        frappe.log_error("Get Subjects Failed", frappe.get_traceback())
        return []


@frappe.whitelist()
def get_my_subjects():
    """
    Get subjects specific to the current user's Academic Plan.

    Returns subjects with their display names and additional metadata.
    """
    try:
        user = frappe.session.user

        # 1. Fetch Player Profile
        profile = frappe.db.get_value("Player Profile",
            {"user": user},
            ["current_grade", "current_stream", "academic_year"],
            as_dict=True)

        if not profile or not profile.current_grade:
            return []  # No profile set up yet

        current_grade = profile.current_grade
        current_stream = profile.current_stream
        academic_year = profile.academic_year or "2025"

        # 2. Fetch the Game Academic Plan
        plan_filters = {
            "grade": current_grade,
            "year": academic_year
        }

        if current_stream:
            plan_filters["stream"] = current_stream

        plan_name = frappe.db.get_value("Game Academic Plan", plan_filters, "name")

        if not plan_name:
            return []  # No plan configured

        plan = frappe.get_doc("Game Academic Plan", plan_name)

        # 3. Extract unique subjects from the plan
        subject_map = {}

        for row in plan.subjects:
            subject_name = row.subject

            if subject_name not in subject_map:
                # Fetch subject details
                subject_info = frappe.db.get_value("Game Subject",
                    {"name": subject_name, "is_published": 1},
                    ["name", "title", "icon"], as_dict=True)

                if subject_info:
                    subject_map[subject_name] = {
                        "id": subject_info.name,
                        "name": subject_info.title,
                        "icon": subject_info.icon,
                        "display_name": row.display_name or subject_info.title,
                        "is_mandatory": row.is_mandatory
                    }

        # Convert to list
        subjects = list(subject_map.values())

        return subjects

    except Exception as e:
        frappe.log_error(title="get_my_subjects failed", message=frappe.get_traceback())
        return []


@frappe.whitelist()
def get_game_tracks(subject):
    """
    Get tracks for a given subject.

    Args:
        subject: Subject name/ID

    Returns:
        List of tracks with metadata
    """
    try:
        if not subject: return []

        # Fetch tracks associated with subject
        # Order: Default first, then by order or creation
        tracks = frappe.get_all("Game Learning Track",
            filters={"subject": subject},
            fields=["name", "track_name", "is_default", "unlock_level", "icon", "description"],
            order_by="is_default desc, creation asc"
        )

        return tracks
    except Exception as e:
        return []
