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
    EquipmentReminders,
    EquipmentUpdate,
    MaintenanceRecordCreate,
    ScrapCreate,
)
from app.services import equipment_service

router = APIRouter(prefix="/equipment", tags=["工具设备"])


@router.get("", response_model=Page[EquipmentOut], summary="设备列表")
def list_equipment(
    db: Annotated[Session, Depends(get_db)],
    pagination: PaginationDep,
    keyword: Annotated[str | None, Query(description="名称/编号/使用人模糊搜索")] = None,
    category: Annotated[str | None, Query(description="设备分类")] = None,
    status: Annotated[str | None, Query(description="设备状态")] = None,
    due: Annotated[str | None, Query(description="保养到期状态：已逾期/临近到期/正常")] = None,
    restroom_id: Annotated[int | None, Query(description="按配置地点（公厕）过滤")] = None,
    sort_by: Annotated[str, Query(description="排序字段")] = "created_at",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> Page[EquipmentOut]:
    rows, total = equipment_service.list_equipment(
        db,
        keyword=keyword,
        category=category,
        status=status,
        due=due,
        restroom_id=restroom_id,
        page=pagination.page,
        page_size=pagination.page_size,
        sort_by=sort_by,
        order=order,
    )
    counts = equipment_service.maintenance_counts(db, [row.id for row in rows])
    return Page[EquipmentOut](
        items=[
            equipment_service.to_out(row, maintenance_count=counts.get(row.id, 0))
            for row in rows
        ],
        meta=build_meta(total, pagination),
    )


@router.post("", response_model=EquipmentOut, status_code=201, summary="新增设备")
def create_equipment(
    payload: EquipmentCreate, db: Annotated[Session, Depends(get_db)]
) -> EquipmentOut:
    return equipment_service.to_out(equipment_service.create_equipment(db, payload))


@router.get("/reminders", response_model=EquipmentReminders, summary="保养提醒")
def get_reminders(
    db: Annotated[Session, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=90, description="临近到期判断窗口（天）")] = MAINTENANCE_REMIND_DAYS,
) -> EquipmentReminders:
    overdue, upcoming = equipment_service.maintenance_reminders(db, days=days)
    return EquipmentReminders(
        overdue=[equipment_service.to_out(item) for item in overdue],
        upcoming=[equipment_service.to_out(item) for item in upcoming],
        remind_days=days,
    )


@router.get("/{equipment_id}", response_model=EquipmentDetail, summary="设备详情")
def get_equipment(equipment_id: int, db: Annotated[Session, Depends(get_db)]) -> EquipmentDetail:
    return equipment_service.get_equipment_detail(db, equipment_id)


@router.patch("/{equipment_id}", response_model=EquipmentOut, summary="更新设备信息")
def update_equipment(
    equipment_id: int, payload: EquipmentUpdate, db: Annotated[Session, Depends(get_db)]
) -> EquipmentOut:
    equipment = equipment_service.update_equipment(db, equipment_id, payload)
    return equipment_service.to_out(equipment)


@router.delete("/{equipment_id}", response_model=MessageOut, summary="删除设备")
def delete_equipment(
    equipment_id: int,
    db: Annotated[Session, Depends(get_db)],
    force: Annotated[bool, Query(description="为 true 时级联删除保养记录")] = False,
) -> MessageOut:
    equipment_service.delete_equipment(db, equipment_id, force=force)
    return MessageOut(message="删除成功")


@router.post(
    "/{equipment_id}/maintenance",
    response_model=EquipmentDetail,
    status_code=201,
    summary="登记保养记录",
)
def add_maintenance(
    equipment_id: int,
    payload: MaintenanceRecordCreate,
    db: Annotated[Session, Depends(get_db)],
) -> EquipmentDetail:
    equipment_service.add_maintenance_record(db, equipment_id, payload)
    return equipment_service.get_equipment_detail(db, equipment_id)


@router.post("/{equipment_id}/scrap", response_model=EquipmentDetail, summary="报废登记")
def scrap_equipment(
    equipment_id: int,
    payload: ScrapCreate,
    db: Annotated[Session, Depends(get_db)],
) -> EquipmentDetail:
    equipment_service.scrap_equipment(db, equipment_id, payload)
    return equipment_service.get_equipment_detail(db, equipment_id)
