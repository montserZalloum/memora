*Make sure to check "Is Child Table" for all of these.*

1.  **`Game Grade Valid Stream`**
    *   `stream` (Link: `Game Academic Stream`) - [Mandatory]

2.  **`Game Plan Subject`**
    *   `subject` (Link: `Game Subject`) - [Mandatory]
    *   `display_name` (Data)
    *   `is_mandatory` (Check) - Default: 1
    *   `selection_type` (Select): `All Units`\n`Specific Unit` - Default: `All Units`
    *   `specific_unit` (Link: `Game Unit`) - Depends on: `eval:doc.selection_type=='Specific Unit'`

3.  **`Game Item Target Stream`**
    *   `stream` (Link: `Game Academic Stream`) - [Mandatory]

4.  **`Game Bundle Content`**
    *   `type` (Select): `Subject`\n`Track`
    *   `target_subject` (Link: `Game Subject`) - Depends on: `eval:doc.type=='Subject'`
    *   `target_track` (Link: `Game Learning Track`) - Depends on: `eval:doc.type=='Track'`

5.  **`Game Subscription Access`**
    *   `type` (Select): `Subject`\n`Track`\n`Global`
    *   `subject` (Link: `Game Subject`)
    *   `track` (Link: `Game Learning Track`)

6.  **`Game Player Device`**
    *   `device_id` (Data)
    *   `device_name` (Data)
    *   `last_active_date` (Datetime)

---


1.  **`Game Academic Stream`**
    *   `stream_name` (Data) - [Title Field]

2.  **`Game Academic Grade`**
    *   `grade_name` (Data) - [Title Field]
    *   `valid_streams` (Table MultiSelect: `Game Grade Valid Stream`)

3.  **`Game Subscription Season`**
    *   `season_name` (Data) - [Title Field]
    *   `start_date` (Date)
    *   `end_date` (Date)
    *   `is_active` (Check)

---


1.  **`Game Subject`** (Modify Existing)
    *   `is_paid` (Check)
    *   `full_price` (Currency)
    *   `discounted_price` (Currency)

2.  **`Game Learning Track`** (Modify Existing)
    *   `is_paid` (Check)
    *   `is_sold_separately` (Check)
    *   `standalone_price` (Currency)
    *   `discounted_price` (Currency)

3.  **`Game Unit`** (Modify Existing)
    *   `structure_type` (Select): `Topic Based`\n`Lesson Based` - Default: `Topic Based`
    *   `is_free_preview` (Check)
    *   `is_linear_topics` (Check)

4.  **`Game Topic`** (New)
    *   `title` (Data) - [Mandatory]
    *   `unit` (Link: `Game Unit`) - [Mandatory]
    *   `description` (Small Text)
    *   `order` (Int)
    *   `is_free_preview` (Check)
    *   `is_linear` (Check) - Default: 1

5.  **`Game Lesson`** (Modify Existing)
    *   `topic` (Link: `Game Topic`)

---


1.  **`Game Academic Plan`**
    *   `grade` (Link: `Game Academic Grade`) - [Mandatory]
    *   `stream` (Link: `Game Academic Stream`)
    *   `season` (Link: `Game Subscription Season`) - [Mandatory]
    *   `subjects` (Table: `Game Plan Subject`)

2.  **`Game Sales Item`**
    *   `item_name` (Data)
    *   `linked_season` (Link: `Game Subscription Season`) - [Mandatory]
    *   `target_grade` (Link: `Game Academic Grade`)
    *   `target_streams` (Table MultiSelect: `Game Item Target Stream`)
    *   `price` (Currency)
    *   `discounted_price` (Currency)
    *   `bundle_contents` (Table: `Game Bundle Content`)
    *   `sku` (Data)

1.  **`Game Player Subscription`**
    *   `player` (Link: `Player Profile`)
    *   `linked_season` (Link: `Game Subscription Season`) - [Mandatory]
    *   `type` (Select): `Global Access`\n`Specific Access`
    *   `status` (Select): `Active`\n`Suspended`\n`Expired`
    *   `access_items` (Table: `Game Subscription Access`)

2.  **`Game Purchase Request`**
    *   `user` (Link: `User`)
    *   `sales_item` (Link: `Game Sales Item`)
    *   `status` (Select): `Pending`\n`Approved`\n`Rejected`
    *   `transaction_id` (Data)
    *   `payment_screenshot` (Attach Image)
    *   *(Make sure to enable "Is Submittable")*

3.  **`Player Profile`** (Modify Existing)
    *   `current_grade` (Link: `Game Academic Grade`)
    *   `current_stream` (Link: `Game Academic Stream`)
    *   `academic_year` (Link: `Game Subscription Season`)
    *   `devices` (Table: `Game Player Device`)

4.  **`Player Memory Tracker`** (Modify Existing)
    *   `topic` (Link: `Game Topic`)
    *   `season` (Link: `Game Subscription Season`)
