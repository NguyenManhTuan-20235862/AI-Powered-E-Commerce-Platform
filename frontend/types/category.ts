// Khớp `CategoryRead` thật (backend/app/schemas/category.py, task 4.2.1).

export interface Category {
  id: number;
  name: string;
  description: string | null;
}
