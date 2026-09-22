import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { InventoryAdjustmentModal } from "./InventoryAdjustmentModal";

const { post } = vi.hoisted(() => ({ post: vi.fn() }));
vi.mock("@/lib/axios", () => ({ api: { post } }));
vi.mock("sonner", () => ({ toast: { success: vi.fn() } }));
const product = { id: 1, name: "Tai nghe", stock_quantity: 10, image_url: null, is_active: true };
afterEach(() => { cleanup(); vi.clearAllMocks(); });

it("requires a positive integer and confirmation before sending", async () => {
  const user = userEvent.setup();
  render(<InventoryAdjustmentModal product={product} onClose={vi.fn()} onSaved={vi.fn()} />);
  expect(screen.getByRole("button", { name: "Xem lại điều chỉnh" })).toBeDisabled();
  await user.type(screen.getByLabelText("Số lượng"), "5");
  await user.click(screen.getByRole("button", { name: "Xem lại điều chỉnh" }));
  expect(post).not.toHaveBeenCalled();
  expect(screen.getByText(/Xác nhận tăng 5/)).toBeInTheDocument();
});

it("keeps the same key and form after a failed request and uses server stock on success", async () => {
  const user = userEvent.setup();
  const saved = vi.fn();
  post.mockRejectedValueOnce(new Error("network"));
  post.mockResolvedValueOnce({ data: { data: { id: 7, stock_before: 8, stock_after: 13 } } });
  render(<InventoryAdjustmentModal product={product} onClose={vi.fn()} onSaved={saved} />);
  await user.type(screen.getByLabelText("Số lượng"), "5");
  await user.click(screen.getByRole("button", { name: "Xem lại điều chỉnh" }));
  await user.click(screen.getByRole("button", { name: "Xác nhận điều chỉnh" }));
  await screen.findByRole("alert");
  expect(screen.getByLabelText("Số lượng")).toHaveValue(5);
  await user.click(screen.getByRole("button", { name: "Xác nhận điều chỉnh" }));
  await waitFor(() => expect(saved).toHaveBeenCalledWith({ id: 7, stock_before: 8, stock_after: 13 }));
  expect(post.mock.calls[0][2]).toEqual(post.mock.calls[1][2]);
});

it.each(["damage", "audit"])("sends a negative delta for %s reduction", async reason => {
  const user = userEvent.setup();
  post.mockResolvedValue({ data: { data: { stock_before: 10, stock_after: 7 } } });
  render(<InventoryAdjustmentModal product={product} onClose={vi.fn()} onSaved={vi.fn()} />);
  await user.selectOptions(screen.getByLabelText("Lý do"), reason);
  if (reason === "audit") await user.selectOptions(screen.getByLabelText("Hướng điều chỉnh"), "-1");
  await user.type(screen.getByLabelText("Số lượng"), "3");
  await user.click(screen.getByRole("button", { name: "Xem lại điều chỉnh" }));
  await user.click(screen.getByRole("button", { name: "Xác nhận điều chỉnh" }));
  expect(post.mock.calls[0][1]).toMatchObject({ reason, change_quantity: -3 });
});
