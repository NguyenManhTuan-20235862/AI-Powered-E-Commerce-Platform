export type UserRole = "customer" | "admin";

export interface User {
  id: string | number;
  email: string;
  fullName?: string;
  role: UserRole;
}
