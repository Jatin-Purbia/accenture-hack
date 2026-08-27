import { Boxes, DollarSign, Headphones, Package, Percent, ShoppingCart, Tag } from "lucide-react";
import type { LucideIcon } from "lucide-react";

/** One icon per KPI domain — a single icon library (Lucide) used
 * consistently everywhere, never mixed with another style. */
export function kpiIcon(kpiId: string): LucideIcon {
  if (kpiId.includes("margin")) return Percent;
  if (kpiId.includes("ticket")) return Headphones;
  if (kpiId.includes("subcategory") || kpiId.includes("emerging")) return Package;
  return DollarSign;
}

export function driverIcon(driver: string): LucideIcon {
  if (driver.includes("quantity")) return ShoppingCart;
  if (driver.includes("discount")) return Tag;
  if (driver.includes("price")) return DollarSign;
  if (driver.includes("mix")) return Boxes;
  if (driver.includes("margin")) return Percent;
  return Package;
}

const PLAIN_DRIVER_LABEL: Record<string, string> = {
  quantity_effect: "Units sold",
  avg_price_effect: "Average price",
  discount_effect: "Discounting",
  cost_mix_effect: "Product mix",
  margin_rate_effect: "Margin rate",
};

/** Plain-English label for a raw driver key. `technical=true` (analyst
 * mode) shows the underlying name instead. */
export function driverLabel(driver: string, technical = false): string {
  if (technical) return driver.replace(/_/g, " ");
  return PLAIN_DRIVER_LABEL[driver] ?? driver.replace(/_/g, " ");
}
