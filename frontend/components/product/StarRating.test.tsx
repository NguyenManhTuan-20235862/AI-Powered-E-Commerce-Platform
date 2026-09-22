import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { StarRating } from "@/components/product/StarRating";

describe("StarRating (task Hoàn thiện review sản phẩm)", () => {
  it("chế độ CHỈ XEM (không có onChange) - dùng role='img', KHÔNG có nút bấm nào", () => {
    render(<StarRating value={3} />);
    expect(screen.getByRole("img", { name: "3 trên 5 sao" })).toBeInTheDocument();
    expect(screen.queryAllByRole("radio")).toHaveLength(0);
    expect(screen.queryAllByRole("button")).toHaveLength(0);
  });

  it("chế độ NHẬP (có onChange) - dùng role='radiogroup', đủ 5 nút radio", () => {
    render(<StarRating value={0} onChange={vi.fn()} />);
    expect(screen.getByRole("radiogroup", { name: "Chọn số sao đánh giá" })).toBeInTheDocument();
    expect(screen.getAllByRole("radio")).toHaveLength(5);
  });

  it("bấm vào ngôi sao thứ N gọi onChange(N)", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<StarRating value={0} onChange={onChange} />);

    await user.click(screen.getByRole("radio", { name: "4 sao" }));

    expect(onChange).toHaveBeenCalledWith(4);
  });

  it("aria-checked ĐÚNG ngôi sao khớp value hiện tại", () => {
    render(<StarRating value={3} onChange={vi.fn()} />);
    expect(screen.getByRole("radio", { name: "3 sao" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("radio", { name: "4 sao" })).toHaveAttribute("aria-checked", "false");
  });
});
