"""保洁工具与设备维护台账模型。"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import (
    DisposalMethod,
    EquipmentCategory,
    EquipmentStatus,
    MaintenanceCycle,
)
from app.core.database import Base


class Equipment(Base):
    """保洁工具与设备台账，一件（批）工具一条档案。"""

    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, comment="工具编号")
    name: Mapped[str] = mapped_column(String(120), index=True, comment="工具/设备名称")
    category: Mapped[str] = mapped_column(
        String(20), default=EquipmentCategory.CLEANING_TOOL.value, index=True, comment="分类"
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, comment="配置数量")
    unit: Mapped[str] = mapped_column(String(10), default="台", comment="计量单位")
    assignee: Mapped[str] = mapped_column(String(60), default="", index=True, comment="使用人")
    location: Mapped[str] = mapped_column(String(120), default="", comment="存放地点")
    maintenance_cycle: Mapped[str] = mapped_column(
        String(10), default=MaintenanceCycle.MONTHLY.value, comment="保养周期"
    )
    last_maintained_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="最近保养时间"
    )
    next_maintenance_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True, comment="下次保养日期"
    )
    scrapped_quantity: Mapped[int] = mapped_column(Integer, default=0, comment="累计报废数量")
    status: Mapped[str] = mapped_column(
        String(20), default=EquipmentStatus.IN_USE.value, index=True, comment="使用状态"
    )
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )

    maintenance_records: Mapped[list["MaintenanceRecord"]] = relationship(
        back_populates="equipment",
        cascade="all, delete-orphan",
        order_by="MaintenanceRecord.maintained_at.desc()",
    )
    scrap_records: Mapped[list["ScrapRecord"]] = relationship(
        back_populates="equipment",
        cascade="all, delete-orphan",
        order_by="ScrapRecord.scrapped_at.desc()",
    )

    @property
    def available_quantity(self) -> int:
        """可用数量 = 配置数量 - 累计报废数量。"""
        return max(self.quantity - self.scrapped_quantity, 0)


class MaintenanceRecord(Base):
    """保养记录：保养内容、更换部件与费用，用于还原维护历史。"""

    __tablename__ = "maintenance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipment.id", ondelete="CASCADE"), index=True, comment="所属工具设备"
    )
    maintained_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True, comment="保养时间"
    )
    operator: Mapped[str] = mapped_column(String(60), default="", comment="保养人")
    content: Mapped[str] = mapped_column(Text, default="", comment="保养内容")
    replaced_parts: Mapped[str] = mapped_column(String(200), default="", comment="更换部件")
    cost: Mapped[float | None] = mapped_column(Float, nullable=True, comment="保养费用（元）")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="登记时间")

    equipment: Mapped["Equipment"] = relationship(back_populates="maintenance_records")


class ScrapRecord(Base):
    """损坏报废登记：原因与处置方式。"""

    __tablename__ = "scrap_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipment.id", ondelete="CASCADE"), index=True, comment="所属工具设备"
    )
    scrapped_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True, comment="报废时间"
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, comment="报废数量")
    reason: Mapped[str] = mapped_column(String(200), comment="报废原因")
    disposal_method: Mapped[str] = mapped_column(
        String(20), default=DisposalMethod.RECYCLE.value, comment="处置方式"
    )
    operator: Mapped[str] = mapped_column(String(60), default="", comment="经办人")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="登记时间")

    equipment: Mapped["Equipment"] = relationship(back_populates="scrap_records")
