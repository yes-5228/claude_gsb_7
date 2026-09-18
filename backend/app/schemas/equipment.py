"""保洁工具与设备维护台账相关数据结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import (
    DisposalMethod,
    EquipmentCategory,
    EquipmentStatus,
    MaintenanceCycle,
)


class MaintenanceRecordOut(BaseModel):
    """保养记录节点。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    equipment_id: int
    maintained_at: datetime
    operator: str
    content: str
    replaced_parts: str
    cost: float | None = None
    remark: str | None = None
    created_at: datetime


class ScrapRecordOut(BaseModel):
    """报废登记节点。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    equipment_id: int
    scrapped_at: datetime
    quantity: int
    reason: str
    disposal_method: str
    operator: str
    remark: str | None = None
    created_at: datetime


class EquipmentBase(BaseModel):
    name: str = Field(min_length=1, max_length=120, description="工具/设备名称")
    category: EquipmentCategory = Field(
        default=EquipmentCategory.CLEANING_TOOL, description="分类"
    )
    quantity: int = Field(default=1, ge=1, description="配置数量")
    unit: str = Field(default="台", max_length=10, description="计量单位")
    assignee: str = Field(default="", max_length=60, description="使用人")
    location: str = Field(default="", max_length=120, description="存放地点")
    maintenance_cycle: MaintenanceCycle = Field(
        default=MaintenanceCycle.MONTHLY, description="保养周期"
    )
    remark: str | None = Field(default=None, max_length=500, description="备注")


class EquipmentCreate(EquipmentBase):
    code: str | None = Field(default=None, max_length=32, description="编号，留空自动生成")
    last_maintained_at: datetime | None = Field(
        default=None, description="最近保养时间，留空按建档时间起算"
    )


class EquipmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category: EquipmentCategory | None = None
    quantity: int | None = Field(default=None, ge=1)
    unit: str | None = Field(default=None, max_length=10)
    assignee: str | None = Field(default=None, max_length=60)
    location: str | None = Field(default=None, max_length=120)
    maintenance_cycle: MaintenanceCycle | None = None
    remark: str | None = Field(default=None, max_length=500)


class MaintenanceRecordCreate(BaseModel):
    maintained_at: datetime | None = Field(default=None, description="保养时间，留空取当前时间")
    operator: str = Field(min_length=1, max_length=60, description="保养人")
    content: str = Field(min_length=1, max_length=500, description="保养内容")
    replaced_parts: str = Field(default="", max_length=200, description="更换部件")
    cost: float | None = Field(default=None, ge=0, description="保养费用（元）")
    remark: str | None = Field(default=None, max_length=500, description="备注")


class ScrapRecordCreate(BaseModel):
    scrapped_at: datetime | None = Field(default=None, description="报废时间，留空取当前时间")
    quantity: int = Field(default=1, ge=1, description="报废数量")
    reason: str = Field(min_length=1, max_length=200, description="报废原因")
    disposal_method: DisposalMethod = Field(
        default=DisposalMethod.RECYCLE, description="处置方式"
    )
    operator: str = Field(min_length=1, max_length=60, description="经办人")
    remark: str | None = Field(default=None, max_length=500, description="备注")


class EquipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    category: str
    quantity: int
    unit: str
    assignee: str
    location: str
    maintenance_cycle: str
    last_maintained_at: datetime | None = None
    next_maintenance_at: datetime | None = None
    scrapped_quantity: int
    available_quantity: int
    status: str
    remark: str | None = None
    created_at: datetime
    updated_at: datetime


class EquipmentDetail(EquipmentOut):
    """设备详情：附带完整保养与报废记录。"""

    maintenance_records: list[MaintenanceRecordOut] = Field(default_factory=list)
    scrap_records: list[ScrapRecordOut] = Field(default_factory=list)


class EquipmentReminderItem(BaseModel):
    """一条保养提醒：设备摘要 + 到期信息。"""

    equipment_id: int
    code: str
    name: str
    category: str
    assignee: str
    maintenance_cycle: str
    last_maintained_at: datetime | None = None
    next_maintenance_at: datetime
    days: int = Field(description="已超期天数（overdue）或距到期天数（upcoming）")


class MaintenanceReminders(BaseModel):
    """按保养周期生成的提醒：已超期与即将到期两组。"""

    overdue: list[EquipmentReminderItem] = Field(default_factory=list)
    upcoming: list[EquipmentReminderItem] = Field(default_factory=list)
