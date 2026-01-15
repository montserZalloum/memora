"""
Memora Schema Migration
Creates all DocTypes for the Memora module in the correct order.
"""
import frappe


def execute():
    """Execute the migration to create/update DocTypes"""

    def create_or_update_doctype(doctype_dict):
        """Helper function to create or update a DocType"""
        try:
            doctype_name = doctype_dict.get("name")

            # Check if DocType exists
            if frappe.db.exists("DocType", doctype_name):
                print(f"✓ Updating existing DocType: {doctype_name}")
                doc = frappe.get_doc("DocType", doctype_name)

                # Update fields (add new ones without deleting existing)
                for field in doctype_dict.get("fields", []):
                    field_name = field.get("fieldname")
                    # Check if field already exists
                    existing = [f for f in doc.fields if f.fieldname == field_name]
                    if not existing:
                        doc.append("fields", field)

                doc.save()
            else:
                print(f"✓ Creating new DocType: {doctype_name}")
                doc = frappe.get_doc(doctype_dict)
                doc.insert()

            frappe.db.commit()
            return True
        except Exception as e:
            print(f"✗ Error with {doctype_dict.get('name')}: {str(e)}")
            frappe.db.rollback()
            return False

    # PHASE 1: Create Child Tables
    print("\n" + "="*60)
    print("PHASE 1: Creating Child Tables")
    print("="*60)

    # 1. Game Player Device (Child Table)
    create_or_update_doctype({
        "doctype": "DocType",
        "name": "Game Player Device",
        "module": "Memora",
        "istable": 1,
        "fields": [
            {
                "fieldname": "device_id",
                "label": "Device ID",
                "fieldtype": "Data",
                "reqd": 0
            },
            {
                "fieldname": "device_name",
                "label": "Device Name",
                "fieldtype": "Data",
                "reqd": 0
            },
            {
                "fieldname": "last_active_date",
                "label": "Last Active Date",
                "fieldtype": "Datetime",
                "reqd": 0
            }
        ]
    })

    # 2. Game Bundle Content (Child Table) - Create before Game Plan Subject since it's referenced
    create_or_update_doctype({
        "doctype": "DocType",
        "name": "Game Bundle Content",
        "module": "Memora",
        "istable": 1,
        "fields": [
            {
                "fieldname": "type",
                "label": "Type",
                "fieldtype": "Select",
                "options": "Subject\nTrack",
                "reqd": 1
            },
            {
                "fieldname": "target_subject",
                "label": "Target Subject",
                "fieldtype": "Link",
                "options": "Game Subject",
                "reqd": 0
            },
            {
                "fieldname": "target_track",
                "label": "Target Track",
                "fieldtype": "Link",
                "options": "Game Learning Track",
                "reqd": 0
            }
        ]
    })

    # 3. Game Subscription Access (Child Table)
    create_or_update_doctype({
        "doctype": "DocType",
        "name": "Game Subscription Access",
        "module": "Memora",
        "istable": 1,
        "fields": [
            {
                "fieldname": "type",
                "label": "Type",
                "fieldtype": "Select",
                "options": "Subject\nTrack",
                "reqd": 1
            },
            {
                "fieldname": "subject",
                "label": "Subject",
                "fieldtype": "Link",
                "options": "Game Subject",
                "reqd": 0
            },
            {
                "fieldname": "track",
                "label": "Track",
                "fieldtype": "Link",
                "options": "Game Learning Track",
                "reqd": 0
            }
        ]
    })

    # 4. Game Plan Subject (Child Table) - Create after other child tables it might reference
    create_or_update_doctype({
        "doctype": "DocType",
        "name": "Game Plan Subject",
        "module": "Memora",
        "istable": 1,
        "fields": [
            {
                "fieldname": "subject",
                "label": "Subject",
                "fieldtype": "Link",
                "options": "Game Subject",
                "reqd": 1
            },
            {
                "fieldname": "display_name",
                "label": "Display Name",
                "fieldtype": "Data",
                "reqd": 0
            },
            {
                "fieldname": "is_mandatory",
                "label": "Is Mandatory",
                "fieldtype": "Check",
                "default": 1,
                "reqd": 0
            },
            {
                "fieldname": "inclusion_mode",
                "label": "Inclusion Mode",
                "fieldtype": "Select",
                "options": "All Units\nSelected Units Only",
                "default": "All Units",
                "reqd": 0
            },
            {
                "fieldname": "allowed_units",
                "label": "Allowed Units",
                "fieldtype": "Link",
                "options": "Game Unit",
                "reqd": 0
            }
        ]
    })

    # PHASE 2: Create Master Data DocTypes
    print("\n" + "="*60)
    print("PHASE 2: Creating Master Data DocTypes")
    print("="*60)

    # 1. Game Academic Grade
    create_or_update_doctype({
        "doctype": "DocType",
        "name": "Game Academic Grade",
        "module": "Memora",
        "document_type": "Master",
        "autoname": "field:grade_name",
        "naming_rule": "By fieldname",
        "track_changes": 1,
        "fields": [
            {
                "fieldname": "grade_name",
                "label": "Grade Name",
                "fieldtype": "Data",
                "unique": 1,
                "reqd": 1
            }
        ]
    })

    # 2. Game Academic Stream
    create_or_update_doctype({
        "doctype": "DocType",
        "name": "Game Academic Stream",
        "module": "Memora",
        "document_type": "Master",
        "autoname": "field:stream_name",
        "naming_rule": "By fieldname",
        "track_changes": 1,
        "fields": [
            {
                "fieldname": "stream_name",
                "label": "Stream Name",
                "fieldtype": "Data",
                "unique": 1,
                "reqd": 1
            }
        ]
    })

    # 3. Game Subscription Season
    create_or_update_doctype({
        "doctype": "DocType",
        "name": "Game Subscription Season",
        "module": "Memora",
        "document_type": "Master",
        "autoname": "field:season_name",
        "naming_rule": "By fieldname",
        "track_changes": 1,
        "fields": [
            {
                "fieldname": "season_name",
                "label": "Season Name",
                "fieldtype": "Data",
                "reqd": 1
            },
            {
                "fieldname": "start_date",
                "label": "Start Date",
                "fieldtype": "Date",
                "reqd": 0
            },
            {
                "fieldname": "end_date",
                "label": "End Date",
                "fieldtype": "Date",
                "reqd": 0
            },
            {
                "fieldname": "is_active",
                "label": "Is Active",
                "fieldtype": "Check",
                "default": 0,
                "reqd": 0
            }
        ]
    })

    # PHASE 3: Create Complex Logic DocTypes
    print("\n" + "="*60)
    print("PHASE 3: Creating Complex Logic DocTypes")
    print("="*60)

    # 1. Game Academic Plan
    create_or_update_doctype({
        "doctype": "DocType",
        "name": "Game Academic Plan",
        "module": "Memora",
        "document_type": "Master",
        "autoname": "naming_series:",
        "track_changes": 1,
        "fields": [
            {
                "fieldname": "naming_series",
                "label": "Naming Series",
                "fieldtype": "Select",
                "options": "PLAN-",
                "default": "PLAN-",
                "hidden": 1,
                "reqd": 0
            },
            {
                "fieldname": "grade",
                "label": "Grade",
                "fieldtype": "Link",
                "options": "Game Academic Grade",
                "reqd": 1
            },
            {
                "fieldname": "stream",
                "label": "Stream",
                "fieldtype": "Link",
                "options": "Game Academic Stream",
                "reqd": 1
            },
            {
                "fieldname": "year",
                "label": "Year",
                "fieldtype": "Data",
                "reqd": 0
            },
            {
                "fieldname": "subjects",
                "label": "Subjects",
                "fieldtype": "Table",
                "options": "Game Plan Subject",
                "reqd": 0
            }
        ]
    })

    # 2. Game Sales Item
    create_or_update_doctype({
        "doctype": "DocType",
        "name": "Game Sales Item",
        "module": "Memora",
        "document_type": "Master",
        "track_changes": 1,
        "fields": [
            {
                "fieldname": "item_name",
                "label": "Item Name",
                "fieldtype": "Data",
                "reqd": 0
            },
            {
                "fieldname": "description",
                "label": "Description",
                "fieldtype": "Text Editor",
                "reqd": 0
            },
            {
                "fieldname": "image",
                "label": "Image",
                "fieldtype": "Attach Image",
                "reqd": 0
            },
            {
                "fieldname": "price",
                "label": "Price",
                "fieldtype": "Currency",
                "reqd": 0
            },
            {
                "fieldname": "discounted_price",
                "label": "Discounted Price",
                "fieldtype": "Currency",
                "reqd": 0
            },
            {
                "fieldname": "bundle_contents",
                "label": "Bundle Contents",
                "fieldtype": "Table",
                "options": "Game Bundle Content",
                "reqd": 0
            },
            {
                "fieldname": "sku",
                "label": "SKU",
                "fieldtype": "Data",
                "reqd": 0
            }
        ]
    })

    # 3. Game Player Subscription
    create_or_update_doctype({
        "doctype": "DocType",
        "name": "Game Player Subscription",
        "module": "Memora",
        "document_type": "Master",
        "autoname": "naming_series:",
        "track_changes": 1,
        "fields": [
            {
                "fieldname": "naming_series",
                "label": "Naming Series",
                "fieldtype": "Select",
                "options": "SUB-",
                "default": "SUB-",
                "hidden": 1,
                "reqd": 0
            },
            {
                "fieldname": "player",
                "label": "Player",
                "fieldtype": "Link",
                "options": "Player Profile",
                "reqd": 1
            },
            {
                "fieldname": "linked_season",
                "label": "Linked Season",
                "fieldtype": "Link",
                "options": "Game Subscription Season",
                "reqd": 0
            },
            {
                "fieldname": "type",
                "label": "Type",
                "fieldtype": "Select",
                "options": "Global Access\nSpecific Access",
                "reqd": 1
            },
            {
                "fieldname": "status",
                "label": "Status",
                "fieldtype": "Select",
                "options": "Active\nSuspended\nExpired",
                "reqd": 0
            },
            {
                "fieldname": "start_date",
                "label": "Start Date",
                "fieldtype": "Date",
                "reqd": 0
            },
            {
                "fieldname": "expiry_date",
                "label": "Expiry Date",
                "fieldtype": "Date",
                "reqd": 0
            },
            {
                "fieldname": "access_items",
                "label": "Access Items",
                "fieldtype": "Table",
                "options": "Game Subscription Access",
                "depends_on": "eval:doc.type=='Specific Access'",
                "reqd": 0
            }
        ]
    })

    # PHASE 4: Modify Existing DocTypes
    print("\n" + "="*60)
    print("PHASE 4: Modifying Existing DocTypes")
    print("="*60)

    # A. Modify Player Profile
    print("Modifying: Player Profile")
    if frappe.db.exists("DocType", "Player Profile"):
        player_profile_fields = [
            {
                "fieldname": "current_grade",
                "label": "Current Grade",
                "fieldtype": "Link",
                "options": "Game Academic Grade",
                "reqd": 0
            },
            {
                "fieldname": "current_stream",
                "label": "Current Stream",
                "fieldtype": "Link",
                "options": "Game Academic Stream",
                "reqd": 0
            },
            {
                "fieldname": "academic_year",
                "label": "Academic Year",
                "fieldtype": "Data",
                "reqd": 0
            },
            {
                "fieldname": "devices",
                "label": "Devices",
                "fieldtype": "Table",
                "options": "Game Player Device",
                "reqd": 0
            }
        ]

        try:
            doc = frappe.get_doc("DocType", "Player Profile")
            for field in player_profile_fields:
                field_name = field.get("fieldname")
                existing = [f for f in doc.fields if f.fieldname == field_name]
                if not existing:
                    doc.append("fields", field)
            doc.save()
            frappe.db.commit()
            print("✓ Player Profile updated successfully")
        except Exception as e:
            print(f"✗ Error updating Player Profile: {str(e)}")
            frappe.db.rollback()
    else:
        print("✗ Player Profile DocType not found")

    # B. Modify Game Subject
    print("Modifying: Game Subject")
    if frappe.db.exists("DocType", "Game Subject"):
        game_subject_fields = [
            {
                "fieldname": "is_paid",
                "label": "Is Paid",
                "fieldtype": "Check",
                "default": 1,
                "reqd": 0
            },
            {
                "fieldname": "full_price",
                "label": "Full Price",
                "fieldtype": "Currency",
                "reqd": 0
            },
            {
                "fieldname": "discounted_price",
                "label": "Discounted Price",
                "fieldtype": "Currency",
                "reqd": 0
            }
        ]

        try:
            doc = frappe.get_doc("DocType", "Game Subject")
            for field in game_subject_fields:
                field_name = field.get("fieldname")
                existing = [f for f in doc.fields if f.fieldname == field_name]
                if not existing:
                    doc.append("fields", field)
            doc.save()
            frappe.db.commit()
            print("✓ Game Subject updated successfully")
        except Exception as e:
            print(f"✗ Error updating Game Subject: {str(e)}")
            frappe.db.rollback()
    else:
        print("✗ Game Subject DocType not found")

    # C. Modify Game Learning Track
    print("Modifying: Game Learning Track")
    if frappe.db.exists("DocType", "Game Learning Track"):
        game_track_fields = [
            {
                "fieldname": "is_paid",
                "label": "Is Paid",
                "fieldtype": "Check",
                "default": 0,
                "reqd": 0
            },
            {
                "fieldname": "is_sold_separately",
                "label": "Is Sold Separately",
                "fieldtype": "Check",
                "default": 0,
                "reqd": 0
            },
            {
                "fieldname": "standalone_price",
                "label": "Standalone Price",
                "fieldtype": "Currency",
                "reqd": 0
            },
            {
                "fieldname": "discounted_price",
                "label": "Discounted Price",
                "fieldtype": "Currency",
                "reqd": 0
            }
        ]

        try:
            doc = frappe.get_doc("DocType", "Game Learning Track")
            for field in game_track_fields:
                field_name = field.get("fieldname")
                existing = [f for f in doc.fields if f.fieldname == field_name]
                if not existing:
                    doc.append("fields", field)
            doc.save()
            frappe.db.commit()
            print("✓ Game Learning Track updated successfully")
        except Exception as e:
            print(f"✗ Error updating Game Learning Track: {str(e)}")
            frappe.db.rollback()
    else:
        print("✗ Game Learning Track DocType not found")

    # D. Modify Game Unit
    print("Modifying: Game Unit")
    if frappe.db.exists("DocType", "Game Unit"):
        game_unit_fields = [
            {
                "fieldname": "is_free_preview",
                "label": "Is Free Preview",
                "fieldtype": "Check",
                "default": 0,
                "reqd": 0
            }
        ]

        try:
            doc = frappe.get_doc("DocType", "Game Unit")
            for field in game_unit_fields:
                field_name = field.get("fieldname")
                existing = [f for f in doc.fields if f.fieldname == field_name]
                if not existing:
                    doc.append("fields", field)
            doc.save()
            frappe.db.commit()
            print("✓ Game Unit updated successfully")
        except Exception as e:
            print(f"✗ Error updating Game Unit: {str(e)}")
            frappe.db.rollback()
    else:
        print("✗ Game Unit DocType not found")

    # E. Modify Player Subject Score
    print("Modifying: Player Subject Score")
    if frappe.db.exists("DocType", "Player Subject Score"):
        player_score_fields = [
            {
                "fieldname": "season",
                "label": "Season",
                "fieldtype": "Link",
                "options": "Game Subscription Season",
                "reqd": 0
            }
        ]

        try:
            doc = frappe.get_doc("DocType", "Player Subject Score")
            for field in player_score_fields:
                field_name = field.get("fieldname")
                existing = [f for f in doc.fields if f.fieldname == field_name]
                if not existing:
                    doc.append("fields", field)
            doc.save()
            frappe.db.commit()
            print("✓ Player Subject Score updated successfully")
        except Exception as e:
            print(f"✗ Error updating Player Subject Score: {str(e)}")
            frappe.db.rollback()
    else:
        print("✗ Player Subject Score DocType not found")

    # F. Modify Player Memory Tracker
    print("Modifying: Player Memory Tracker")
    if frappe.db.exists("DocType", "Player Memory Tracker"):
        player_tracker_fields = [
            {
                "fieldname": "season",
                "label": "Season",
                "fieldtype": "Link",
                "options": "Game Subscription Season",
                "reqd": 0
            }
        ]

        try:
            doc = frappe.get_doc("DocType", "Player Memory Tracker")
            for field in player_tracker_fields:
                field_name = field.get("fieldname")
                existing = [f for f in doc.fields if f.fieldname == field_name]
                if not existing:
                    doc.append("fields", field)
            doc.save()
            frappe.db.commit()
            print("✓ Player Memory Tracker updated successfully")
        except Exception as e:
            print(f"✗ Error updating Player Memory Tracker: {str(e)}")
            frappe.db.rollback()
    else:
        print("✗ Player Memory Tracker DocType not found")

    print("\n" + "="*60)
    print("Schema setup completed!")
    print("="*60)
