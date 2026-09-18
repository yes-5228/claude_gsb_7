"""保洁工具与设备维护台账业务逻辑。"""

from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.constants import (
    MAINTENANCE_CYCLE_DAYS,
    MAINTENANCE_REMIND_DAYS,
    EquipmentStatus,
    MaintenanceCycle,
)
from app.core.exceptions import ConflictError, DomainError, NotFoundError
from app.models import Equipment, MaintenanceRecord, ScrapRecord
from app.schemas.equipment import (
    EquipmentCreate,
    EquipmentDetail,
    EquipmentOut,
    EquipmentReminderItem,
    EquipmentUpdate,
    MaintenanceRecordCreate,
    MaintenanceReminders,
    ScrapRecordCreate,
)

SORTABLE_FIELDS = {
    "code": Equipment.code,
    "name": Equipment.name,
    "category": Equipment.category,
    "next_maintenance_at": Equipment.next_maintenance_at,
    "created_at": Equipment.created_at,
    "updated_at": Equipment.updated_at,
}


def _next_code(db: Session) -> str:
    """生成形如 GJ-0007 的工具设备编号。"""
    seq = (db.scalar(select(func.count()).select_from(Equipment)) or 0) + 1
    while True:
        code = f"GJ-{seq:04d}"
        if not db.scalar(select(Equipment.id).where(Equipment.code == code)):
            return code
        seq += 1


def _values(data: dict) -> dict:
    return {key: (value.value if hasattr(value, "value") else value) for key, value in data.items()}


def cycle_days(cycle: str) -> int:
    try:
        return MAINTENANCE_CYCLE_DAYS[MaintenanceCycle(cycle)]
    except ValueError:
        return MAINTENANCE_CYCLE_DAYS[MaintenanceCycle.MONTHLY]


def refresh_next_maintenance(equipment: Equipment) -> None:
    """按「最近保养时间（无则按建档时间）+ 保养周期」推算下次保养日期。"""
    base = equipment.last_maintained_at or equipment.created_at or datetime.now()
    equipment.next_maintenance_at = base + timedelta(days=cycle_days(equipment.maintenance_cycle))


def _sync_status(equipment: Equipment) -> None:
    """状态与可用数量保持一致：可用为 0 即已报废，补回数量后恢复在用。"""
    equipment.status = (
        EquipmentStatus.SCRAPPED.value
        if equipment.available_quantity <= 0
        else EquipmentStatus.IN_USE.value
    )


def get_equipment(db: Session, equipment_id: int) -> Equipment:
    equipment = db.get(Equipment, equipment_id)
    if equipment is None:
        raise NotFoundError(f"工具设备 {equipment_id} 不存在")
    return equipment


def to_out(equipment: Equipment) -> EquipmentOut:
    return EquipmentOut.model_validate(equipment)


def to_detail(equipment: Equipment) -> EquipmentDetail:
    return EquipmentDetail.model_validate(equipment)


def list_equipment(
    db: Session,
    *,
    keyword: str | None = None,
    category: str | None = None,
    status: str | None = None,
    maintenance_cycle: str | None = None,
    assignee: str | None = None,
    due: str | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "created_at",
    order: str = "desc",
) -> tuple[list[Equipment], int]:
    stmt = select(Equipment)
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                Equipment.name.like(like),
                Equipment.code.like(like),
                Equipment.assignee.like(like),
                Equipment.location.like(like),
            )
        )
    if category:
        stmt = stmt.where(Equipment.category == category)
    if status:
        stmt = stmt.where(Equipment.status == status)
    if maintenance_cycle:
        stmt = stmt.where(Equipment.maintenance_cycle == maintenance_cycle)
    if assignee:
        stmt = stmt.where(Equipment.assignee.like(f"%{assignee.strip()}%"))
    if due == "overdue":
        stmt = stmt.where(
            Equipment.status == EquipmentStatus.IN_USE.value,
            Equipment.next_maintenance_at.is_not(None),
            Equipment.next_maintenance_at < datetime.now(),
        )
    elif due == "upcoming":
        stmt = stmt.where(
            Equipment.status == EquipmentStatus.IN_USE.value,
            Equipment.next_maintenance_at.is_not(None),
            Equipment.next_maintenance_at >= datetime.now(),
            Equipment.next_maintenance_at
            <= datetime.now() + timedelta(days=MAINTENANCE_REMIND_DAYS),
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = SORTABLE_FIELDS.get(sort_by, Equipment.created_at)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), Equipment.id.desc())
    rows = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)))
    return rows, total


def create_equipment(db: Session, payload: EquipmentCreate) -> Equipment:
    data = _values(payload.model_dump())
    code = (data.pop("code") or "").strip() or _next_code(db)
    if db.scalar(select(Equipment.id).where(Equipment.code == code)):
        raise DomainError(f"工具设备编号 {code} 已存在")
    equipment = Equipment(code=code, **data)
    db.add(equipment)
    db.flush()
    refresh_next_maintenance(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment


def update_equipment(db: Session, equipment_id: int, payload: EquipmentUpdate) -> Equipment:
    equipment = get_equipment(db, equipment_id)
    data = _values(payload.model_dump(exclude_unset=True))
    if "quantity" in data and data["quantity"] < equipment.scrapped_quantity:
        raise DomainError(
            f"配置数量不能小于已报废数量（{equipment.scrapped_quantity} {equipment.unit}）"
        )
    for key, value in data.items():
        setattr(equipment, key, value)
    if "maintenance_cycle" in data:
        refresh_next_maintenance(equipment)
    _sync_status(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment


def delete_equipment(db: Session, equipment_id: int, *, force: bool = False) -> None:
    equipment = get_equipment(db, equipment_id)
    maintenance_count = db.scalar(
        select(func.count())
        .select_from(MaintenanceRecord)
        .where(MaintenanceRecord.equipment_id == equipment_id)
    ) or 0
    scrap_count = db.scalar(
        select(func.count())
        .select_from(ScrapRecord)
        .where(ScrapRecord.equipment_id == equipment_id)
    ) or 0
    if (maintenance_count or scrap_count) and not force:
        raise ConflictError(
            f"该设备已有 {maintenance_count} 条保养记录、{scrap_count} 条报废记录，"
            "确需删除请使用 force=true"
        )
    db.delete(equipment)
    db.commit()


def add_maintenance_record(
    db: Session, equipment_id: int, payload: MaintenanceRecordCreate
) -> Equipment:
    """登记保养：写入保养内容与更换部件，并按周期顺延下次保养日期。"""
    equipment = get_equipment(db, equipment_id)
    if equipment.status == EquipmentStatus.SCRAPPED.value:
        raise DomainError("设备已报废，无法登记保养")

    maintained_at = payload.maintained_at or datetime.now()
    record = MaintenanceRecord(
        equipment_id=equipment.id,
        maintained_at=maintained_at,
        operator=payload.operator,
        content=payload.content,
        replaced_parts=payload.replaced_parts,
        cost=payload.cost,
        remark=payload.remark,
    )
    db.add(record)
    equipment.last_maintained_at = maintained_at
    equipment.next_maintenance_at = maintained_at + timedelta(
        days=cycle_days(equipment.maintenance_cycle)
    )
    db.commit()
    db.refresh(equipment)
    return equipment


def add_scrap_record(db: Session, equipment_id: int, payload: ScrapRecordCreate) -> Equipment:
    """报废登记：累计报废数量，全部报废后设备状态转为「已报废」。"""
    equipment = get_equipment(db, equipment_id)
    if equipment.status == EquipmentStatus.SCRAPPED.value:
        raise DomainError("设备已全部报废，无法重复登记")
    available = equipment.available_quantity
    if payload.quantity > available:
        raise DomainError(f"报废数量超出可用数量（当前可用 {available} {equipment.unit}）")

    record = ScrapRecord(
        equipment_id=equipment.id,
        scrapped_at=payload.scrapped_at or datetime.now(),
        quantity=payload.quantity,
        reason=payload.reason,
        disposal_method=payload.disposal_method.value,
        operator=payload.operator,
        remark=payload.remark,
    )
    db.add(record)
    equipment.scrapped_quantity += payload.quantity
    _sync_status(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment


def _reminder_item(equipment: Equipment, days: int) -> EquipmentReminderItem:
    return EquipmentReminderItem(
        equipment_id=equipment.id,
        code=equipment.code,
        name=equipment.name,
        category=equipment.category,
        assignee=equipment.assignee,
        maintenance_cycle=equipment.maintenance_cycle,
        last_maintained_at=equipment.last_maintained_at,
        next_maintenance_at=equipment.next_maintenance_at,
        days=days,
    )


def maintenance_reminders(
    db: Session, *, within_days: int = MAINTENANCE_REMIND_DAYS
) -> MaintenanceReminders:
    """按保养周期生成提醒：已超期一组、N 天内即将到期一组，均按到期日升序。"""
    now = datetime.now()
    rows = list(
        db.scalars(
            select(Equipment)
            .where(
                Equipment.status == EquipmentStatus.IN_USE.value,
                Equipment.next_maintenance_at.is_not(None),
                Equipment.next_maintenance_at <= now + timedelta(days=within_days),
            )
            .order_by(Equipment.next_maintenance_at.asc(), Equipment.id.asc())
        )
    )
    overdue: list[EquipmentReminderItem] = []
    upcoming: list[EquipmentReminderItem] = []
    today = now.date()
    for equipment in rows:
        delta = (equipment.next_maintenance_at.date() - today).days
        if equipment.next_maintenance_at < now:
            overdue.append(_reminder_item(equipment, -delta))
        else:
            upcoming.append(_reminder_item(equipment, delta))
    return MaintenanceReminders(overdue=overdue, upcoming=upcoming)
