"""保洁工具与设备维护台账模型。"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import EquipmentCategory, EquipmentStatus
from app.core.database import Base


class Equipment(Base):
    """保洁工具/设备档案，按保养周期生成保养提醒。"""

    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, comment="设备编号")
    name: Mapped[str] = mapped_column(String(120), index=True, comment="设备名称")
    category: Mapped[str] = mapped_column(
        String(20), default=EquipmentCategory.TOOL.value, index=True, comment="设备分类"
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, comment="配置数量")
    unit: Mapped[str] = mapped_column(String(10), default="台", comment="计量单位")
    custodian: Mapped[str] = mapped_column(String(60), default="", index=True, comment="使用人")
    restroom_id: Mapped[int | None] = mapped_column(
        ForeignKey("restrooms.id", ondelete="SET NULL"), nullable=True, index=True,
        comment="配置地点（所属公厕）",
    )
    maintenance_cycle_days: Mapped[int] = mapped_column(Integer, default=30, comment="保养周期（天）")
    last_maintained_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="上次保养时间"
    )
    next_maintenance_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, index=True, comment="下次保养日期"
    )
    status: Mapped[str] = mapped_column(
        String(20), default=EquipmentStatus.IN_USE.value, index=True, comment="设备状态"
    )
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="购置日期")
    scrapped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="报废时间")
    scrap_reason: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="报废原因")
    disposal_method: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="处置方式"
    )
    scrap_note: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="处置说明")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )

    restroom: Mapped["Restroom | None"] = relationship()  # noqa: F821
    maintenance_records: Mapped[list["MaintenanceRecord"]] = relationship(
        back_populates="equipment",
        cascade="all, delete-orphan",
        order_by="MaintenanceRecord.maintained_at.desc()",
    )


class MaintenanceRecord(Base):
    """一次保养的流水记录：保养内容与更换部件。"""

    __tablename__ = "maintenance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipment.id", ondelete="CASCADE"), index=True, comment="所属设备"
    )
    maintained_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True, comment="保养时间"
    )
    content: Mapped[str] = mapped_column(String(300), comment="保养内容")
    replaced_parts: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="更换部件"
    )
    operator: Mapped[str] = mapped_column(String(60), default="", comment="保养人")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="登记时间")

    equipment: Mapped["Equipment"] = relationship(back_populates="maintenance_records")
