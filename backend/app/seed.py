"""演示数据生成：首次启动时写入，便于快速体验各模块。"""

import random
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import (
    INSPECTION_CHECK_ITEMS,
    DisposalMethod,
    EquipmentCategory,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    RestroomGrade,
    RestroomStatus,
    Shift,
)
from app.models import Restroom
from app.schemas.equipment import EquipmentCreate, MaintenanceRecordCreate, ScrapCreate
from app.schemas.inspection import InspectionCreate, InspectionItem
from app.schemas.issue import IssueCreate, IssueStatusUpdate
from app.schemas.restroom import RestroomCreate
from app.services import equipment_service, inspection_service, issue_service, restroom_service

RANDOM_SEED = 20240913

RESTROOM_SPECS = [
    ("人民广场公共厕所", "城东区", "人民广场东侧 50 米", RestroomGrade.FIRST, RestroomStatus.NORMAL, "王秀兰", 12, 6, True),
    ("滨江公园公共厕所", "城东区", "滨江公园 3 号入口", RestroomGrade.SECOND, RestroomStatus.NORMAL, "李国强", 8, 4, True),
    ("和平路公共厕所", "城东区", "和平路与解放街交叉口", RestroomGrade.THIRD, RestroomStatus.MAINTENANCE, "赵敏", 4, 2, False),
    ("火车站南广场公共厕所", "城西区", "火车站南广场西侧", RestroomGrade.FIRST, RestroomStatus.NORMAL, "陈志远", 16, 8, True),
    ("西城集贸市场公共厕所", "城西区", "西城集贸市场北门", RestroomGrade.SECOND, RestroomStatus.NORMAL, "刘桂芳", 10, 4, False),
    ("文化路步行街公共厕所", "城西区", "文化路步行街中段", RestroomGrade.SECOND, RestroomStatus.NORMAL, "孙鹏", 9, 5, True),
    ("滨江新区体育中心公共厕所", "滨江新区", "体育中心东看台下", RestroomGrade.FIRST, RestroomStatus.NORMAL, "周晓燕", 14, 7, True),
    ("滨江新区政务中心公共厕所", "滨江新区", "政务服务中心一楼", RestroomGrade.SECOND, RestroomStatus.NORMAL, "吴建华", 8, 4, True),
    ("老城隍庙公共厕所", "老城区", "城隍庙街 12 号", RestroomGrade.THIRD, RestroomStatus.NORMAL, "郑淑珍", 5, 2, False),
    ("老城区第三小学旁公共厕所", "老城区", "第三小学东侧巷道", RestroomGrade.THIRD, RestroomStatus.CLOSED, "何伟", 4, 2, False),
]

INSPECTORS = ["张伟", "刘洋", "胡明月", "邓晨曦", "马晓峰", "杨柳"]
MANAGERS = ["王秀兰", "李国强", "陈志远", "刘桂芳", "周晓燕", "吴建华", "郑淑珍", "孙鹏"]

ISSUE_TEMPLATES = {
    IssueCategory.CLEANING: [
        "地面存在明显污渍未及时清理",
        "蹲位清洁不彻底，存在残留",
        "垃圾篓内垃圾未及时清运",
    ],
    IssueCategory.FACILITY: [
        "水龙头漏水，需更换阀芯",
        "感应冲水器失灵，无法自动冲水",
        "隔间门锁损坏无法反锁",
    ],
    IssueCategory.ODOR: [
        "公厕内异味明显，通风效果差",
        "排风扇停转导致异味积聚",
    ],
    IssueCategory.CONSUMABLE: [
        "洗手液未及时补充",
        "纸巾盒空置，未补充厕纸",
    ],
    IssueCategory.SAFETY: [
        "地面湿滑未放置防滑警示牌",
        "照明灯具损坏，夜间存在安全隐患",
    ],
    IssueCategory.OTHER: [
        "无障碍扶手松动需加固",
        "标识牌褪色需更换",
    ],
}

CATEGORY_BY_ITEM = {
    "地面与台阶清洁": IssueCategory.CLEANING,
    "便池蹲位清洁": IssueCategory.CLEANING,
    "洗手台与镜面": IssueCategory.CLEANING,
    "通风除臭": IssueCategory.ODOR,
    "耗材补充": IssueCategory.CONSUMABLE,
    "垃圾清运": IssueCategory.CLEANING,
    "工具与标识摆放": IssueCategory.OTHER,
    "墙面门窗卫生": IssueCategory.CLEANING,
}

# 设备演示数据：(名称, 分类, 数量, 单位, 使用人, 公厕序号, 保养周期天, 购置于多少天前, 保养记录, 报废信息)
# 保养记录：(多少天前, 保养内容, 更换部件, 保养人)；报废信息：(原因, 处置方式, 处置说明) 或 None
EQUIPMENT_SPECS = [
    (
        "高压清洗机", EquipmentCategory.MACHINE, 1, "台", "王秀兰", 0, 30, 200,
        [
            (68, "更换密封圈、清洗泵头滤网", "高压密封圈", "设备员周师傅"),
            (8, "整机清洗、管路压力检查", None, "设备员周师傅"),
        ],
        None,
    ),
    (
        "驾驶式洗地机", EquipmentCategory.MACHINE, 1, "台", "李国强", 1, 30, 400,
        [(40, "刷盘更换、电瓶检测", "刷盘×2", "设备员周师傅")],
        None,
    ),
    (
        "吸尘吸水机", EquipmentCategory.MACHINE, 2, "台", "陈志远", 3, 60, 300,
        [(55, "电机碳刷检查、更换尘袋", "集尘袋", "维修班杜师傅")],
        None,
    ),
    (
        "保洁电动三轮车", EquipmentCategory.VEHICLE, 1, "辆", "刘桂芳", 4, 90, 260,
        [(80, "刹车调试、轮胎补气、链条上油", None, "维修班杜师傅")],
        None,
    ),
    (
        "拖把榨水桶套装", EquipmentCategory.TOOL, 20, "套", "周晓燕", 6, 15, 120,
        [(20, "拖把头全部更换、桶身消毒", "拖把头×20", "周晓燕")],
        None,
    ),
    (
        "防滑警示牌", EquipmentCategory.TOOL, 30, "个", "孙鹏", 5, 30, 10,
        [],
        None,
    ),
    (
        "自动喷香机", EquipmentCategory.ELECTRICAL, 6, "台", "吴建华", 7, 30, 150,
        [(26, "更换香薰罐与电池、喷头清洗", "香薰罐×6", "吴建华")],
        None,
    ),
    (
        "干手器", EquipmentCategory.ELECTRICAL, 4, "台", "郑淑珍", 8, 60, 320,
        [(70, "滤网清灰、感应器校准", None, "维修班杜师傅")],
        None,
    ),
    (
        "玻璃清洁套装", EquipmentCategory.TOOL, 15, "套", "王秀兰", 0, 15, 5,
        [],
        None,
    ),
    (
        "管道疏通机", EquipmentCategory.MACHINE, 1, "台", "何伟", 9, 45, 500,
        [(90, "更换疏通弹簧、机体除锈", "疏通弹簧", "设备员周师傅")],
        ("电机进水烧毁，维修成本过高", DisposalMethod.RECYCLE, "已交物资回收站，回收单 HS-20260911"),
    ),
]


def _build_items(rng: random.Random, quality: float) -> list[InspectionItem]:
    items: list[InspectionItem] = []
    for name in INSPECTION_CHECK_ITEMS:
        score = quality + rng.uniform(-1.6, 1.4)
        items.append(InspectionItem(name=name, score=max(0, min(10, round(score)))))
    return items


def _pick_problem(items: list[InspectionItem]) -> str | None:
    """找出最需要整改的检查项：优先取不合格项，否则取得分最低的一项。"""
    if not items:
        return None
    problems = [item for item in items if item.score < 6]
    pool = problems or items
    return min(pool, key=lambda item: item.score).name


def seed_database(db: Session, *, reset: bool = False) -> int:
    """写入演示数据，返回新增的问题条数；已有数据时默认跳过。"""
    existing = db.scalar(select(func.count()).select_from(Restroom)) or 0
    if existing and not reset:
        return 0

    rng = random.Random(RANDOM_SEED)
    now = datetime.now()

    restrooms = [
        restroom_service.create_restroom(
            db,
            RestroomCreate(
                name=name,
                district=district,
                address=address,
                grade=grade,
                status=status,
                manager=manager,
                manager_phone=f"13{rng.randint(100000000, 999999999)}",
                stall_count=stalls,
                basin_count=basins,
                has_accessible=accessible,
                open_hours="06:00-22:30" if grade == RestroomGrade.FIRST else "06:30-21:30",
            ),
        )
        for name, district, address, grade, status, manager, stalls, basins, accessible in RESTROOM_SPECS
    ]

    quality_by_restroom = {room.id: rng.uniform(7.4, 9.8) for room in restrooms}
    inspection_ids: list[tuple[int, int]] = []  # (restroom_id, inspection_id)

    for offset in range(13, -1, -1):
        day = now - timedelta(days=offset)
        for room in restrooms:
            if room.status == RestroomStatus.CLOSED:
                continue
            if rng.random() < 0.3:
                continue
            quality = quality_by_restroom[room.id] + rng.uniform(-1.0, 0.6)
            if rng.random() < 0.18:
                quality -= 2.6
            items = _build_items(rng, quality)
            inspection = inspection_service.create_inspection(
                db,
                InspectionCreate(
                    restroom_id=room.id,
                    inspector=rng.choice(INSPECTORS),
                    shift=rng.choice(list(Shift)),
                    inspect_time=day.replace(
                        hour=rng.choice([8, 10, 14, 16, 19]), minute=rng.choice([5, 20, 35, 50])
                    ),
                    items=items,
                    remark=None,
                ),
            )
            inspection_ids.append((room.id, inspection.id))

    created = 0
    for restroom_id, inspection_id in inspection_ids:
        summary = inspection_service.get_inspection(db, inspection_id)
        if summary.result != "发现问题" or rng.random() > 0.75:
            continue
        problem_item = _pick_problem([InspectionItem(**item) for item in summary.items])
        category = CATEGORY_BY_ITEM.get(problem_item or "", IssueCategory.OTHER)
        title = rng.choice(ISSUE_TEMPLATES[category])
        severity = (
            IssueSeverity.URGENT
            if category in (IssueCategory.SAFETY, IssueCategory.FACILITY) and rng.random() < 0.3
            else rng.choice([IssueSeverity.NORMAL, IssueSeverity.SERIOUS])
        )
        age_days = (now - summary.inspect_time).days
        deadline = summary.inspect_time + timedelta(
            days=1 if severity == IssueSeverity.URGENT else 3
        )
        issue = issue_service.create_issue(
            db,
            IssueCreate(
                restroom_id=restroom_id,
                inspection_id=inspection_id,
                title=title,
                description=f"巡查得分 {summary.score} 分（{summary.grade}），检查项「{problem_item}」不达标，请安排整改。",
                category=category,
                severity=severity,
                reporter=summary.inspector,
                assignee=rng.choice(MANAGERS),
                deadline=deadline,
                initial_remark="由保洁巡查自动生成的问题工单",
            ),
        )
        created += 1
        _advance_issue(db, issue.id, age_days, rng)

    _seed_equipment(db, restrooms, now)

    return created


def _seed_equipment(db: Session, restrooms: list, now: datetime) -> None:
    """写入工具与设备台账演示数据，覆盖正常/临近到期/已逾期/已报废四种保养状态。"""
    for name, category, quantity, unit, custodian, room_idx, cycle, bought_days_ago, records, scrap in EQUIPMENT_SPECS:
        equipment = equipment_service.create_equipment(
            db,
            EquipmentCreate(
                name=name,
                category=category,
                quantity=quantity,
                unit=unit,
                custodian=custodian,
                restroom_id=restrooms[room_idx].id,
                maintenance_cycle_days=cycle,
                purchase_date=(now - timedelta(days=bought_days_ago)).date(),
            ),
        )
        for days_ago, content, parts, operator in records:
            equipment_service.add_maintenance_record(
                db,
                equipment.id,
                MaintenanceRecordCreate(
                    maintained_at=now - timedelta(days=days_ago),
                    content=content,
                    replaced_parts=parts,
                    operator=operator,
                ),
            )
        if scrap:
            reason, disposal, note = scrap
            equipment_service.scrap_equipment(
                db,
                equipment.id,
                ScrapCreate(reason=reason, disposal_method=disposal, remark=note),
            )


def _advance_issue(db: Session, issue_id: int, age_days: int, rng: random.Random) -> None:
    """按问题存在时长模拟整改进度，让看板呈现多种状态。"""
    steps: list[tuple[str, str, str]] = []
    if age_days >= 1:
        steps.append(
            (
                IssueStatus.PROCESSING.value,
                "街办保洁队",
                "已派单至保洁班组，安排当日整改",
            )
        )
    if age_days >= 3:
        steps.append(
            (
                IssueStatus.REVIEWING.value,
                "整改责任人",
                "整改完成，提交巡查员验收",
            )
        )
    if age_days >= 5 and rng.random() < 0.75:
        steps.append((IssueStatus.DONE.value, "巡查员", "现场复核通过，问题已闭环"))
    if age_days >= 8 and rng.random() < 0.6:
        steps.append((IssueStatus.CLOSED.value, "值班长", "归档关闭"))

    for target, operator, remark in steps:
        try:
            issue_service.change_status(
                db,
                issue_id,
                IssueStatusUpdate(to_status=IssueStatus(target), operator=operator, remark=remark),
            )
        except Exception:  # noqa: BLE001  演示数据允许跳过不合法的流转
            break
