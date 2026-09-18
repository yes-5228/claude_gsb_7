"""保洁工具与设备维护台账接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import PaginationDep, build_meta
from app.core.constants import MAINTENANCE_REMIND_DAYS
from app.core.database import get_db
from app.schemas.common import MessageOut, Page
from app.schemas.equipment import (
    EquipmentCreate,
    EquipmentDetail,
    EquipmentOut,
    EquipmentUpdate,
    MaintenanceRecordCreate,
    MaintenanceReminders,
    ScrapRecordCreate,
)
from app.services import equipment_service

router = APIRouter(prefix="/equipment", tags=["工具设备"])


@router.get("", response_model=Page[EquipmentOut], summary="工具设备列表")
def list_equipment(
    db: Annotated[Session, Depends(get_db)],
    pagination: PaginationDep,
    keyword: Annotated[str | None, Query(description="名称/编号/使用人/存放地点模糊搜索")] = None,
    category: Annotated[str | None, Query(description="分类")] = None,
    status: Annotated[str | None, Query(description="使用状态")] = None,
    maintenance_cycle: Annotated[str | None, Query(description="保养周期")] = None,
    assignee: Annotated[str | None, Query(description="使用人")] = None,
    due: Annotated[
        str | None, Query(description="保养到期过滤：overdue 已超期 / upcoming 即将到期")
    ] = None,
    sort_by: Annotated[str, Query(description="排序字段")] = "created_at",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> Page[EquipmentOut]:
    rows, total = equipment_service.list_equipment(
        db,
        keyword=keyword,
        category=category,
        status=status,
        maintenance_cycle=maintenance_cycle,
        assignee=assignee,
        due=due,
        page=pagination.page,
        page_size=pagination.page_size,
        sort_by=sort_by,
        order=order,
    )
    return Page[EquipmentOut](
        items=[equipment_service.to_out(row) for row in rows],
        meta=build_meta(total, pagination),
    )


@router.post("", response_model=EquipmentOut, status_code=201, summary="登记工具设备")
def create_equipment(
    payload: EquipmentCreate, db: Annotated[Session, Depends(get_db)]
) -> EquipmentOut:
    return equipment_service.to_out(equipment_service.create_equipment(db, payload))


@router.get("/reminders", response_model=MaintenanceReminders, summary="保养提醒")
def get_maintenance_reminders(
    db: Annotated[Session, Depends(get_db)],
    within_days: Annotated[int, Query(ge=1, le=90, description="即将到期的提前提醒天数")] = MAINTENANCE_REMIND_DAYS,
) -> MaintenanceReminders:
    return equipment_service.maintenance_reminders(db, within_days=within_days)


@router.get("/{equipment_id}", response_model=EquipmentDetail, summary="设备详情与保养报废记录")
def get_equipment(equipment_id: int, db: Annotated[Session, Depends(get_db)]) -> EquipmentDetail:
    return equipment_service.to_detail(equipment_service.get_equipment(db, equipment_id))


@router.patch("/{equipment_id}", response_model=EquipmentOut, summary="更新设备信息")
def update_equipment(
    equipment_id: int, payload: EquipmentUpdate, db: Annotated[Session, Depends(get_db)]
) -> EquipmentOut:
    return equipment_service.to_out(equipment_service.update_equipment(db, equipment_id, payload))


@router.delete("/{equipment_id}", response_model=MessageOut, summary="删除设备")
def delete_equipment(
    equipment_id: int,
    db: Annotated[Session, Depends(get_db)],
    force: Annotated[bool, Query(description="有保养/报废记录时需强制删除")] = False,
) -> MessageOut:
    equipment_service.delete_equipment(db, equipment_id, force=force)
    return MessageOut(message="删除成功")


@router.post(
    "/{equipment_id}/maintenances",
    response_model=EquipmentDetail,
    status_code=201,
    summary="登记保养记录",
)
def add_maintenance_record(
    equipment_id: int,
    payload: MaintenanceRecordCreate,
    db: Annotated[Session, Depends(get_db)],
) -> EquipmentDetail:
    equipment = equipment_service.add_maintenance_record(db, equipment_id, payload)
    return equipment_service.to_detail(equipment)


@router.post(
    "/{equipment_id}/scraps",
    response_model=EquipmentDetail,
    status_code=201,
    summary="报废登记",
)
def add_scrap_record(
    equipment_id: int,
    payload: ScrapRecordCreate,
    db: Annotated[Session, Depends(get_db)],
) -> EquipmentDetail:
    equipment = equipment_service.add_scrap_record(db, equipment_id, payload)
    return equipment_service.to_detail(equipment)
