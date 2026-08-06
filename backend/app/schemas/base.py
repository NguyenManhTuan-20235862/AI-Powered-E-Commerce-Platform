"""Base class dùng chung cho toàn bộ Pydantic schema (task 1.4.1).

Các schema response domain-specific (UserResponse, ProductResponse...) nên kế
thừa `BaseSchema` thay vì `pydantic.BaseModel` trực tiếp, để tự động có sẵn
cấu hình chung thay vì mỗi file tự khai báo `model_config` riêng lẻ.
"""

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base cho schema response đọc từ SQLAlchemy ORM object.

    - `from_attributes=True`: cho phép `SomeSchema.model_validate(orm_object)`
      đọc trực tiếp field từ attribute của model (không cần convert sang dict).
    - `populate_by_name=True`: cho phép khởi tạo schema bằng tên field Python
      (snake_case) kể cả khi field có khai báo `alias` - hữu ích nếu sau này
      cần đổi field sang camelCase cho frontend qua `Field(alias=...)` mà vẫn
      giữ code Python phía backend snake_case.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
