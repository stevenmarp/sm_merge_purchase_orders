# -*- coding: utf-8 -*-
import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError
try:
    from odoo.tools import format_list
except ImportError:
    def format_list(env, items):
        return ", ".join(str(i) for i in items)



class SmMergePurchaseOrderWizard(models.TransientModel):
    _name = "sm.merge.purchase.order.wizard"
    _description = "Merge Purchase Order"

    action = fields.Selection(
        [
            ("new_cancel", "New Order and Cancel Selected"),
            ("new_delete", "New Order and Delete Selected"),
            ("existing_cancel", "Existing Order and Cancel Others"),
            ("existing_delete", "Existing Order and Delete Others"),
        ],
        default="new_cancel",
        required=True,
    )
    order_ids = fields.Many2many(
        "purchase.order",
        "sm_merge_purchase_order_wizard_rel",
        "wizard_id",
        "order_id",
        string="Purchase Orders",
        required=True,
    )
    destination_order_id = fields.Many2one(
        "purchase.order",
        string="Merge Into",
        domain="[('id', 'in', order_ids)]",
    )
    merge_similar_lines = fields.Boolean(default=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids") or []
        if active_model == "purchase.order" and active_ids and "order_ids" in fields_list:
            orders = self.env["purchase.order"].browse(active_ids).exists()
            res["order_ids"] = [(6, 0, orders.ids)]
            if orders and "destination_order_id" in fields_list:
                res["destination_order_id"] = orders.sorted("id")[0].id
        return res

    def action_merge(self):
        self.ensure_one()
        orders = self._get_valid_orders()
        target_order, source_orders = self._prepare_merge_target(orders)

        for order in source_orders.sorted("id"):
            for line in order.order_line.sorted(lambda item: (item.sequence, item.id)):
                self._copy_or_merge_line(target_order, line)

        source_names = format_list(self.env, source_orders.mapped("name"))
        target_order.message_post(body=_("Merged purchase orders: %s") % source_names)
        self._finish_source_orders(source_orders)

        message = self.env["sm.merge.purchase.order.message"].create({
            "message": _("Order merged successfully"),
            "purchase_order_id": target_order.id,
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("Information"),
            "res_model": "sm.merge.purchase.order.message",
            "res_id": message.id,
            "view_mode": "form",
            "target": "new",
        }

    def _get_valid_orders(self):
        orders = self.order_ids.exists()
        if len(orders) < 2:
            raise UserError(_("Select at least 2 purchase orders to merge."))
        invalid = orders.filtered(lambda order: order.state not in ("draft", "sent"))
        if invalid:
            raise UserError(_("Only draft RFQs can be merged: %s") % format_list(self.env, invalid.mapped("name")))
        if len(orders.partner_id) > 1:
            raise UserError(_("Only purchase orders from the same vendor can be merged."))
        if len(orders.company_id) > 1:
            raise UserError(_("Only purchase orders from the same company can be merged."))
        if len(orders.currency_id) > 1:
            raise UserError(_("Only purchase orders with the same currency can be merged."))
        return orders.sorted("id")

    def _prepare_merge_target(self, orders):
        if self.action.startswith("existing"):
            target_order = self.destination_order_id
            if not target_order:
                raise UserError(_("Select a purchase order to merge into."))
            if target_order not in orders:
                raise UserError(_("The target purchase order must be one of the selected orders."))
            return target_order, orders - target_order

        base_order = orders[0]
        values = self._prepare_new_order_values(base_order, orders)
        target_order = self.env["purchase.order"].create(values)
        return target_order, orders

    def _prepare_new_order_values(self, base_order, orders):
        values = base_order.copy_data({
            "order_line": False,
            "origin": self._merge_origin(orders),
            "partner_ref": False,
        })[0]
        values.pop("name", None)
        return values

    def _merge_origin(self, orders):
        origins = []
        for order in orders:
            if order.origin:
                origins.append(order.origin)
            else:
                origins.append(order.name)
        return ", ".join(dict.fromkeys(origins))

    def _copy_or_merge_line(self, target_order, line):
        if line.display_type or not self.merge_similar_lines:
            self._copy_line(target_order, line)
            return

        target_line = self._find_matching_line(target_order, line)
        if not target_line:
            self._copy_line(target_order, line)
            return

        values = {"product_qty": target_line.product_qty + line.product_qty}
        if "product_packaging_qty" in target_line._fields:
            values["product_packaging_qty"] = target_line.product_packaging_qty + line.product_packaging_qty
        if line.date_planned and (not target_line.date_planned or line.date_planned < target_line.date_planned):
            values["date_planned"] = line.date_planned
        target_line.write(values)

    def _find_matching_line(self, target_order, line):
        line_key = self._line_merge_key(line)
        for target_line in target_order.order_line.filtered(lambda item: not item.display_type):
            if self._line_merge_key(target_line) == line_key:
                return target_line
        return self.env["purchase.order.line"]

    def _line_merge_key(self, line):
        analytic_distribution = line.analytic_distribution or {}
        return (
            line.product_id.id,
            line.product_uom.id,
            line.price_unit,
            line.discount,
            tuple(line.taxes_id.ids),
            line.product_packaging_id.id,
            line.name or "",
            json.dumps(analytic_distribution, sort_keys=True),
        )

    def _copy_line(self, target_order, line):
        values = line.copy_data({"order_id": target_order.id})[0]
        values.pop("invoice_lines", None)
        self.env["purchase.order.line"].create(values)

    def _finish_source_orders(self, source_orders):
        if not source_orders:
            return
        source_orders.button_cancel()
        if self.action.endswith("delete"):
            source_orders.unlink()


class SmMergePurchaseOrderMessage(models.TransientModel):
    _name = "sm.merge.purchase.order.message"
    _description = "Merge Purchase Order Message"

    message = fields.Char(readonly=True)
    purchase_order_id = fields.Many2one("purchase.order", readonly=True)

    def action_open_purchase_order(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Merged Purchase Order"),
            "res_model": "purchase.order",
            "res_id": self.purchase_order_id.id,
            "view_mode": "form",
            "target": "current",
        }
