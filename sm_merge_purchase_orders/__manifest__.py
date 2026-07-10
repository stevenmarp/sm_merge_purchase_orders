# -*- coding: utf-8 -*-
{
    "name": "Merge Purchase Orders",
    "version": "15.0.1.0.0",
    "category": "Purchases",
    "summary": "Merge multiple draft RFQs from the same vendor into one clean purchase order",
    "description": """
Merge Purchase Orders
=====================

Merge selected draft purchase orders or RFQs from the same vendor into a new
purchase order or an existing selected order. Keep the source orders as
cancelled records or remove them after the merge.

Features
--------
* Add Merge Purchase Order under the Purchase Orders Action menu
* Merge only draft/RFQ orders from the same vendor
* Create a new merged purchase order and cancel selected orders
* Create a new merged purchase order and delete selected orders
* Merge selected purchase orders into an existing selected order
* Combine matching order lines to avoid duplicate product lines
* Show selected RFQs, untaxed amount, total amount, and status before merge
* Confirmation message after successful merge
    """,
    "author": "Steven Marp",
    "website": "https://apps.odoo.com/apps/modules/browse?author=Steven Marp",
    "license": "OPL-1",
    "depends": ["purchase"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/merge_purchase_order_views.xml",
    ],
    "images": [
        "static/description/banner.gif",
        "static/description/icon.png",
        "static/description/ss_01_action_menu.png",
        "static/description/ss_02_merge_wizard.png",
        "static/description/ss_03_success_message.png",
        "static/description/ss_04_merged_order.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "price": 28.99,
    "currency": "USD",
}
