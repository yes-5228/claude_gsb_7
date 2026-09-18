"""保洁工具与设备维护台账相关数据结构。"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import DisposalMethod, EquipmentCategory, EquipmentStatus
from app.schemas.restroom import RestroomBrief


class EquipmentBase(BaseModel):
    name: str = Field(min_length=1, max_length=120, description="设备名称")
    category: EquipmentCategory = Field(default=EquipmentCategory.TOOL, description="设备分类")
    quantity: int = Field(default=1, ge=1, description="配置数量")
    unit: str = Field(default="台", max_length=10, description="计量单位")
    custodian: str = Field(default="", max_length=60, description="使用人")
    restroom_id: int | None = Field(default=None, description="配置地点（所属公厕 ID）")
    maintenance_cycle_days: int = Field(default=30, ge=1, le=3650, description="保养周期（天）")
    purchase_date: date | None = Field(default=None, description="购置日期")
    remark: str | None = Field(default=None, max_length=500, description="备注")


class EquipmentCreate(EquipmentBase):
    code: str | None = Field(default=None, max_length=32, description="设备编号，留空自动生成")


class EquipmentUpdate(BaseModel):
    """局部更新，仅提交需要变更的字段。"""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    category: EquipmentCategory | None = None
    quantity: int | None = Field(default=None, ge=1)
    unit: str | None = Field(default=None, max_length=10)
    custodian: str | None = Field(default=None, max_length=60)
    restroom_id: int | None = None
    maintenance_cycle_days: int | None = Field(default=None, ge=1, le=3650)
    status: EquipmentStatus | None = None
    purchase_date: date | None = None
    remark: str | None = Field(default=None, max_length=500)


class EquipmentOut(EquipmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    status: str
    last_maintained_at: datetime | None = None
    next_maintenance_date: date | None = None
    maintenance_due: str = Field(default="", description="保养到期状态：已逾期/临近到期/正常")
    days_to_maintenance: int | None = Field(default=None, description="距下次保养天数，负数表示已逾期")
    restroom: RestroomBrief | None = None
    maintenance_count: int = Field(default=0, description="累计保养次数")
    created_at: datetime
    updated_at: datetime


class EquipmentDetail(EquipmentOut):
    """设备详情，附带报废信息与完整保养记录。"""

    scrapped_at: datetime | None = None
    scrap_reason: str | None = None
    disposal_method: str | None = None
    scrap_note: str | None = None
    records: list["MaintenanceRecordOut"] = Field(default_factory=list)


class MaintenanceRecordCreate(BaseModel):
    maintained_at: datetime | None = Field(default=None, description="保养时间，默认当前时间")
    content: str = Field(min_length=1, max_length=300, description="保养内容")
    replaced_parts: str | None = Field(default=None, max_length=200, description="更换部件")
    operator: str = Field(default="", max_length=60, description="保养人")
    remark: str | None = Field(default=None, max_length=500, description="备注")


class MaintenanceRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipment_id: int
    maintained_at: datetime
    content: str
    replaced_parts: str | None = None
    operator: str = ""
    remark: str | None = None
    created_at: datetime


class ScrapCreate(BaseModel):
    reason: str = Field(min_length=1, max_length=200, description="报废原因")
    disposal_method: DisposalMethod = Field(description="处置方式")
    remark: str | None = Field(default=None, max_length=500, description="处置说明")


class EquipmentReminders(BaseModel):
    """保养提醒：已逾期与临近到期的设备。"""

    overdue: list[EquipmentOut] = Field(default_factory=list)
    upcoming: list[EquipmentOut] = Field(default_factory=list)
    remind_days: int = Field(description="临近到期判断窗口（天）")


EquipmentDetail.model_rebuild()
