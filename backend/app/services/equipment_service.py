"""保洁工具与设备维护台账业务逻辑。"""

from datetime import date, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.constants import (
    MAINTENANCE_DUE_NORMAL,
    MAINTENANCE_DUE_OVERDUE,
    MAINTENANCE_DUE_UPCOMING,
    MAINTENANCE_REMIND_DAYS,
    EquipmentStatus,
)
from app.core.exceptions import ConflictError, DomainError, NotFoundError
from app.models import Equipment, MaintenanceRecord
from app.schemas.equipment import (
    EquipmentCreate,
    EquipmentDetail,
    EquipmentOut,
    EquipmentUpdate,
    MaintenanceRecordCreate,
    MaintenanceRecordOut,
    ScrapCreate,
)
from app.services import restroom_service

SORTABLE_FIELDS = {
    "code": Equipment.code,
    "name": Equipment.name,
    "next_maintenance_date": Equipment.next_maintenance_date,
    "created_at": Equipment.created_at,
    "updated_at": Equipment.updated_at,
}


def _next_code(db: Session) -> str:
    """生成形如 SB-0007 的设备编号。"""
    seq = (db.scalar(select(func.count()).select_from(Equipment)) or 0) + 1
    while True:
        code = f"SB-{seq:04d}"
        if not db.scalar(select(Equipment.id).where(Equipment.code == code)):
            return code
        seq += 1


def _values(data: dict) -> dict:
    return {key: (value.value if hasattr(value, "value") else value) for key, value in data.items()}


def due_state(
    next_date: date | None, status: str, *, today: date | None = None
) -> tuple[str, int | None]:
    """按下次保养日期推算到期状态：已报废或未排期的设备不参与提醒。"""
    if status == EquipmentStatus.SCRAPPED.value or next_date is None:
        return "", None
    today = today or date.today()
    days = (next_date - today).days
    if days < 0:
        return MAINTENANCE_DUE_OVERDUE, days
    if days <= MAINTENANCE_REMIND_DAYS:
        return MAINTENANCE_DUE_UPCOMING, days
    return MAINTENANCE_DUE_NORMAL, days


def _refresh_next_date(equipment: Equipment) -> None:
    """按「上次保养时间 → 购置日期 → 建档时间」的优先级重算下次保养日期。"""
    if equipment.last_maintained_at:
        base = equipment.last_maintained_at.date()
    elif equipment.purchase_date:
        base = equipment.purchase_date
    elif equipment.created_at is not None:
        base = equipment.created_at.date()
    else:  # 新建对象尚未落库，created_at 默认值未生效
        base = date.today()
    equipment.next_maintenance_date = base + timedelta(days=equipment.maintenance_cycle_days)


def get_equipment(db: Session, equipment_id: int) -> Equipment:
    equipment = db.get(Equipment, equipment_id)
    if equipment is None:
        raise NotFoundError(f"设备 {equipment_id} 不存在")
    return equipment


def maintenance_counts(db: Session, equipment_ids: list[int]) -> dict[int, int]:
    if not equipment_ids:
        return {}
    rows = db.execute(
        select(MaintenanceRecord.equipment_id, func.count())
        .where(MaintenanceRecord.equipment_id.in_(equipment_ids))
        .group_by(MaintenanceRecord.equipment_id)
    ).all()
    return {equipment_id: int(count) for equipment_id, count in rows}


def to_out(equipment: Equipment, *, maintenance_count: int = 0) -> EquipmentOut:
    due, days = due_state(equipment.next_maintenance_date, equipment.status)
    data = EquipmentOut.model_validate(equipment).model_dump()
    data.update(
        maintenance_due=due,
        days_to_maintenance=days,
        maintenance_count=maintenance_count,
    )
    return EquipmentOut(**data)


def list_equipment(
    db: Session,
    *,
    keyword: str | None = None,
    category: str | None = None,
    status: str | None = None,
    due: str | None = None,
    restroom_id: int | None = None,
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
                Equipment.custodian.like(like),
            )
        )
    if category:
        stmt = stmt.where(Equipment.category == category)
    if status:
        stmt = stmt.where(Equipment.status == status)
    if restroom_id:
        stmt = stmt.where(Equipment.restroom_id == restroom_id)
    if due:
        today = date.today()
        active = Equipment.status != EquipmentStatus.SCRAPPED.value
        if due == MAINTENANCE_DUE_OVERDUE:
            stmt = stmt.where(active, Equipment.next_maintenance_date < today)
        elif due == MAINTENANCE_DUE_UPCOMING:
            stmt = stmt.where(
                active,
                Equipment.next_maintenance_date >= today,
                Equipment.next_maintenance_date <= today + timedelta(days=MAINTENANCE_REMIND_DAYS),
            )
        elif due == MAINTENANCE_DUE_NORMAL:
            stmt = stmt.where(
                active,
                Equipment.next_maintenance_date > today + timedelta(days=MAINTENANCE_REMIND_DAYS),
            )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = SORTABLE_FIELDS.get(sort_by, Equipment.created_at)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), Equipment.id.desc())
    rows = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)))
    return rows, total


def create_equipment(db: Session, payload: EquipmentCreate) -> Equipment:
    data = _values(payload.model_dump(exclude={"code"}))
    code = (payload.code or "").strip() or _next_code(db)
    if db.scalar(select(Equipment.id).where(Equipment.code == code)):
        raise DomainError(f"设备编号 {code} 已存在")
    if data.get("restroom_id") is not None:
        restroom_service.get_restroom(db, data["restroom_id"])
    equipment = Equipment(code=code, **data)
    _refresh_next_date(equipment)
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment


def update_equipment(db: Session, equipment_id: int, payload: EquipmentUpdate) -> Equipment:
    equipment = get_equipment(db, equipment_id)
    if equipment.status == EquipmentStatus.SCRAPPED.value:
        raise DomainError("设备已报废，档案不可再编辑")
    data = payload.model_dump(exclude_unset=True)
    if data.get("status") == EquipmentStatus.SCRAPPED.value:
        raise DomainError("请通过报废登记接口办理报废，以便记录报废原因与处置方式")
    if data.get("restroom_id") is not None:
        restroom_service.get_restroom(db, data["restroom_id"])
    for key, value in _values(data).items():
        setattr(equipment, key, value)
    if "maintenance_cycle_days" in data:
        _refresh_next_date(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment


def delete_equipment(db: Session, equipment_id: int, *, force: bool = False) -> None:
    equipment = get_equipment(db, equipment_id)
    record_count = maintenance_counts(db, [equipment_id]).get(equipment_id, 0)
    if record_count and not force:
        raise ConflictError(
            f"该设备已有 {record_count} 条保养记录，确需删除请使用 force=true"
        )
    db.delete(equipment)
    db.commit()


def get_equipment_detail(db: Session, equipment_id: int) -> EquipmentDetail:
    equipment = get_equipment(db, equipment_id)
    count = maintenance_counts(db, [equipment_id]).get(equipment_id, 0)
    base = to_out(equipment, maintenance_count=count).model_dump()
    return EquipmentDetail(
        **base,
        scrapped_at=equipment.scrapped_at,
        scrap_reason=equipment.scrap_reason,
        disposal_method=equipment.disposal_method,
        scrap_note=equipment.scrap_note,
        records=[
            MaintenanceRecordOut.model_validate(record)
            for record in equipment.maintenance_records
        ],
    )


def add_maintenance_record(
    db: Session, equipment_id: int, payload: MaintenanceRecordCreate
) -> Equipment:
    """登记保养记录，并按保养周期顺延下次保养日期。"""
    equipment = get_equipment(db, equipment_id)
    if equipment.status == EquipmentStatus.SCRAPPED.value:
        raise DomainError("设备已报废，无需再登记保养")
    maintained_at = payload.maintained_at or datetime.now()
    record = MaintenanceRecord(
        equipment_id=equipment.id,
        maintained_at=maintained_at,
        content=payload.content.strip(),
        replaced_parts=(payload.replaced_parts or "").strip() or None,
        operator=payload.operator.strip(),
        remark=payload.remark,
    )
    db.add(record)
    equipment.last_maintained_at = maintained_at
    _refresh_next_date(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment


def scrap_equipment(db: Session, equipment_id: int, payload: ScrapCreate) -> Equipment:
    """损坏报废登记：记录报废原因与处置方式。"""
    equipment = get_equipment(db, equipment_id)
    if equipment.status == EquipmentStatus.SCRAPPED.value:
        raise DomainError("设备已报废，请勿重复登记")
    equipment.status = EquipmentStatus.SCRAPPED.value
    equipment.scrapped_at = datetime.now()
    equipment.scrap_reason = payload.reason.strip()
    equipment.disposal_method = payload.disposal_method.value
    equipment.scrap_note = (payload.remark or "").strip() or None
    db.commit()
    db.refresh(equipment)
    return equipment


def maintenance_reminders(
    db: Session, *, days: int = MAINTENANCE_REMIND_DAYS
) -> tuple[list[Equipment], list[Equipment]]:
    """保养提醒：返回（已逾期, 临近到期）两组在用设备，按下次保养日期升序。"""
    today = date.today()
    active = Equipment.status != EquipmentStatus.SCRAPPED.value
    overdue = list(
        db.scalars(
            select(Equipment)
            .where(active, Equipment.next_maintenance_date < today)
            .order_by(Equipment.next_maintenance_date.asc(), Equipment.id.asc())
        )
    )
    upcoming = list(
        db.scalars(
            select(Equipment)
            .where(
                active,
                Equipment.next_maintenance_date >= today,
                Equipment.next_maintenance_date <= today + timedelta(days=days),
            )
            .order_by(Equipment.next_maintenance_date.asc(), Equipment.id.asc())
        )
    )
    return overdue, upcoming
