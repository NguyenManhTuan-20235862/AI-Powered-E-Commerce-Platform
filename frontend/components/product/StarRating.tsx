"use client";

import { useState } from "react";

const STAR_PATH = "M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z";

/**
 * Hiển thị/nhập số sao (task "Hoàn thiện review sản phẩm") - component ĐẦU
 * TIÊN trong dự án cho rating, chưa có tiền lệ nào để tái dùng. Màu
 * `amber-400` (class Tailwind mặc định có sẵn, KHÔNG tự định nghĩa giá trị
 * hex mới) - sao vàng là quy ước UI phổ biến, tách biệt có chủ đích khỏi màu
 * thương hiệu (`primary`) - không vi phạm nguyên tắc "không lặp hex" của
 * design token (task 4.1.1, chỉ cấm tự viết mã màu mới, không cấm dùng class
 * có sẵn của Tailwind).
 *
 * `onChange` có giá trị -> chế độ NHẬP (form viết review, bấm để chọn 1-5
 * sao, hover xem trước) - dùng `<button role="radio">`. KHÔNG có `onChange`
 * -> chế độ CHỈ XEM (hiển thị rating có sẵn, VD điểm trung bình/từng review
 * trong danh sách) - dùng `<span>`, không đưa vào accessibility tree như
 * phần tử tương tác được (không cho phím Tab dừng ở 5 ngôi sao vô nghĩa).
 */
export function StarRating({
  value,
  onChange,
  size = 20,
}: {
  value: number;
  onChange?: (rating: number) => void;
  size?: number;
}) {
  const [hoverValue, setHoverValue] = useState<number | null>(null);
  const interactive = Boolean(onChange);
  const displayValue = hoverValue ?? value;

  return (
    <div
      className="inline-flex items-center gap-0.5"
      role={interactive ? "radiogroup" : "img"}
      aria-label={interactive ? "Chọn số sao đánh giá" : `${value} trên 5 sao`}
      onMouseLeave={() => interactive && setHoverValue(null)}
    >
      {[1, 2, 3, 4, 5].map((star) => {
        const filled = star <= Math.round(displayValue);
        const icon = (
          <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill={filled ? "currentColor" : "none"}
            stroke="currentColor"
            strokeWidth="1.5"
            className={filled ? "text-amber-400" : "text-border"}
          >
            <path d={STAR_PATH} strokeLinejoin="round" />
          </svg>
        );

        if (!interactive) {
          return <span key={star}>{icon}</span>;
        }

        return (
          <button
            key={star}
            type="button"
            role="radio"
            aria-checked={star === value}
            aria-label={`${star} sao`}
            onClick={() => onChange?.(star)}
            onMouseEnter={() => setHoverValue(star)}
            className="cursor-pointer"
          >
            {icon}
          </button>
        );
      })}
    </div>
  );
}
