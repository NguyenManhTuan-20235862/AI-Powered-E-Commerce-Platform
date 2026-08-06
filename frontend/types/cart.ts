export interface CartItem {
  productId: string | number;
  productName: string;
  price: number;
  quantity: number;
  imageUrl?: string;
}
