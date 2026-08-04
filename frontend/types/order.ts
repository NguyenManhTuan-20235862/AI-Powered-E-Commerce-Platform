export type OrderStatus =
  | "pending"
  | "confirmed"
  | "shipping"
  | "completed"
  | "cancelled";

export interface OrderItem {
  productId: string | number;
  productName: string;
  quantity: number;
  price: number;
}

export interface Order {
  id: string | number;
  userId: string | number;
  items: OrderItem[];
  total: number;
  status: OrderStatus;
  createdAt: string;
}
